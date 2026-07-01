import re
import logging
from typing import Optional, Tuple, Any
from difflib import SequenceMatcher
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from .models import Product, ProductAlias, StoreProduct, RawScrapedProduct, ProductPrice, ProductImportReview
from supermarkets.models import Branch

logger = logging.getLogger(__name__)

UNIT_MAP = {
    'kg': 'kg', 'k.g.': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'g': 'g', 'gm': 'g', 'gms': 'g', 'gram': 'g', 'grams': 'g',
    'l': 'l', 'lt': 'l', 'lts': 'l', 'ltr': 'l', 'ltrs': 'l', 'litre': 'l', 'litres': 'l',
    'ml': 'ml', 'mls': 'ml', 'millilitre': 'ml', 'millilitres': 'ml'
}

SIZE_UNIT_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*(kg|k\.g\.|kilograms?|g|gm|gms|grams?|l|lts?|ltrs?|litres?|ml|mls|millilitres?)\b',
    re.IGNORECASE
)

KNOWN_BRANDS = {
    "pembe", "jogoo", "kabras", "brookside", "ajab", "exe", "soko", "ndovu",
    "santa maria", "blue band", "blueband", "tusker", "white cap", "safari", "ketepa",
    "cowboy", "kimbo", "super loaf", "broadways", "festive", "ilashe",
    "ranee", "daawat", "ciko", "elianto", "golden fry", "fresh fri",
    "salit", "pika", "sunrise", "ok", "nivea", "dettol", "colgate",
    "dano", "nido", "nestle", "cadbury", "aquafina", "dasani", "keringet",
    "ilmari", "unilever", "spinners", "del monte", "chapa mandashi", "morris",
    "tasty", "pepsi", "coca cola", "fanta", "sprite", "kapa", "menengai"
}

DESCRIPTIVE_WORDS = {
    "sifted", "premium", "packed", "pure", "fresh", "superfine", "refined",
    "uht", "carton", "pack", "best", "dairybest", "dairy", "white", "brown",
    "maize", "all", "purpose", "natural", "organic", "fino",
}

CATEGORY_ALIASES = {
    "corn oil": "oil",
    "cooking oil": "oil",
    "vegetable oil": "oil",
    "edible oil": "oil",
    "sunflower oil": "oil",
    "maize meal": "maize flour",
    "maize flour": "maize flour",
    "wheat flour": "wheat flour",
    "flour": "flour",
    "fresh milk": "milk",
    "uht milk": "milk",
    "whole milk": "milk",
    "milk": "milk",
    "spread": "spread",
    "margarine": "spread",
    "fat spread": "spread",
    "sugar": "sugar",
    "rice": "rice",
    "soap": "soap",
    "detergent": "detergent",
}

VARIANT_ALIASES = {
    "choco": "chocolate",
    "chocolate": "chocolate",
    "vanilla": "vanilla",
    "peanut": "peanut",
    "smooth": "smooth",
    "crunchy": "crunchy",
    "original": "original",
    "plain": "plain",
}

MULTI_VARIANT_BRANDS = {"blue band"}

BRAND_ALIASES = {
    "blueband": "blue band",
}


class ProductMatchService:
    @staticmethod
    def normalize_store_name(store_name: Optional[str]) -> str:
        if not store_name:
            return "Unknown"
        normalized = re.sub(r'\s+', ' ', store_name).strip()
        canonical = {
            "carrefour": "Carrefour",
            "cleanshelf": "CleanShelf",
            "clean shelf": "CleanShelf",
            "naivas": "Naivas",
            "quickmart": "Quickmart",
        }
        return canonical.get(normalized.lower(), normalized.title())

    @staticmethod
    def canonical_brand(brand: Optional[str]) -> Optional[str]:
        if not brand:
            return None
        normalized = re.sub(r'\s+', ' ', brand).strip().lower()
        return BRAND_ALIASES.get(normalized, normalized)

    @staticmethod
    def normalize_name(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        
        name_lower = name.lower()
        name_lower = name_lower.replace("&", " and ")
        
        match = SIZE_UNIT_RE.search(name_lower)
        if match:
            raw_size = match.group(1)
            raw_unit = match.group(2)
            std_unit = UNIT_MAP.get(raw_unit.lower(), raw_unit.lower())
            
            try:
                float_size = float(raw_size)
                if float_size.is_integer():
                    normalized_size = str(int(float_size))
                else:
                    normalized_size = str(float_size)
            except ValueError:
                normalized_size = raw_size
                
            normalized_size_unit = f"{normalized_size}{std_unit}"
            name_lower = name_lower.replace(match.group(0), normalized_size_unit)
            
        cleaned = re.sub(r'[^a-z0-9\s\.]', ' ', name_lower)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned or None

    @staticmethod
    def clean_for_compare(name: Optional[str]) -> str:
        if not name:
            return ""
        n = name.lower()
        n = re.sub(r'\bmeal\b', ' flour ', n)
        for w in DESCRIPTIVE_WORDS:
            n = re.sub(r'\b' + re.escape(w) + r'\b', ' ', n)
        return re.sub(r'\s+', ' ', n).strip()

    @classmethod
    def identity_tokens(cls, normalized_name: Optional[str], brand: Optional[str] = None) -> set[str]:
        """Return stable product identity tokens, excluding brand, size, and store noise."""
        if not normalized_name:
            return set()

        cleaned = cls.clean_for_compare(normalized_name)
        cleaned = SIZE_UNIT_RE.sub(" ", cleaned)
        tokens = {
            t for t in re.split(r'[^a-z0-9]+', cleaned)
            if len(t) > 1 and not t.isdigit()
        }

        if brand:
            for part in re.split(r'[^a-z0-9]+', brand.lower()):
                tokens.discard(part)

        return tokens - DESCRIPTIVE_WORDS

    @classmethod
    def extract_canonical_category(cls, normalized_name: Optional[str]) -> Optional[str]:
        if not normalized_name:
            return None

        cleaned = cls.clean_for_compare(normalized_name)
        for alias, canonical in sorted(CATEGORY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(r'\b' + re.escape(alias) + r'\b', cleaned):
                return canonical
        return None

    @classmethod
    def extract_variant(cls, normalized_name: Optional[str]) -> Optional[str]:
        if not normalized_name:
            return None

        cleaned = cls.clean_for_compare(normalized_name)
        for alias, canonical in sorted(VARIANT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(r'\b' + re.escape(alias) + r'\b', cleaned):
                return canonical
        return None

    @classmethod
    def identity_key(
        cls,
        brand: Optional[str],
        canonical_category: Optional[str],
        variant: Optional[str],
        size: Optional[str],
        unit: Optional[str],
    ) -> Optional[str]:
        brand = cls.canonical_brand(brand)
        if not brand or not canonical_category or not size or not unit:
            return None
        if brand.lower() in MULTI_VARIANT_BRANDS and not variant:
            return None
        parts = [brand.lower(), canonical_category.lower()]
        if variant:
            parts.append(variant.lower())
        parts.extend([size, unit.lower()])
        return "|".join(parts)

    @classmethod
    def _alias_match(cls, normalized_name: str, store_name: str) -> Optional[Product]:
        alias = ProductAlias.objects.filter(
            Q(store_name__iexact=store_name) | Q(store_name__isnull=True) | Q(store_name=""),
            normalized_name=normalized_name,
        ).select_related("product").order_by("-confidence", "store_name").first()
        if alias:
            logger.info(
                f"[Product Matched] Alias match: '{normalized_name}' from '{store_name}' "
                f"matched Product '{alias.product.name}' (ID: {alias.product_id})"
            )
            return alias.product
        return None

    @staticmethod
    def _brand_compatible(incoming_brand: Optional[str], candidate: Product) -> bool:
        if not incoming_brand or not candidate.brand:
            return True
        return (
            ProductMatchService.canonical_brand(incoming_brand)
            == ProductMatchService.canonical_brand(candidate.brand)
        )

    @staticmethod
    def _size_compatible(size: Optional[str], unit: Optional[str], candidate: Product) -> bool:
        if not size or not unit or not candidate.size or not candidate.unit:
            return True
        return size == candidate.size and unit == candidate.unit

    @classmethod
    def _candidate_variant(cls, candidate: Product) -> Optional[str]:
        return candidate.variant or cls.extract_variant(candidate.normalized_name)

    @classmethod
    def _variant_compatible(
        cls,
        variant: Optional[str],
        brand: Optional[str],
        candidate: Product,
    ) -> bool:
        candidate_variant = cls._candidate_variant(candidate)
        if variant and candidate_variant:
            return variant == candidate_variant
        if (
            brand and cls.canonical_brand(brand) in MULTI_VARIANT_BRANDS
        ) or (
            candidate.brand and cls.canonical_brand(candidate.brand) in MULTI_VARIANT_BRANDS
        ):
            return not (variant or candidate_variant)
        return True

    @staticmethod
    def _requires_variant_review(brand: Optional[str], variant: Optional[str]) -> bool:
        return bool(
            brand
            and ProductMatchService.canonical_brand(brand) in MULTI_VARIANT_BRANDS
            and not variant
        )

    @classmethod
    def _identity_score(
        cls,
        normalized_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str],
        candidate: Product,
    ) -> float:
        if not cls._brand_compatible(brand, candidate):
            return 0.0
        if not cls._size_compatible(size, unit, candidate):
            return 0.0
        if not cls._variant_compatible(variant, brand, candidate):
            return 0.0

        incoming_tokens = cls.identity_tokens(normalized_name, brand)
        candidate_tokens = cls.identity_tokens(candidate.normalized_name, candidate.brand)

        if (
            not incoming_tokens
            and not candidate_tokens
            and brand
            and candidate.brand
            and size
            and unit
            and candidate.size
            and candidate.unit
            and cls.canonical_brand(brand) == cls.canonical_brand(candidate.brand)
            and size == candidate.size
            and unit == candidate.unit
        ):
            return 0.88

        if not incoming_tokens or not candidate_tokens:
            return 0.0

        overlap = incoming_tokens & candidate_tokens
        subset_score = len(overlap) / min(len(incoming_tokens), len(candidate_tokens))
        jaccard_score = len(overlap) / len(incoming_tokens | candidate_tokens)

        if subset_score == 1.0:
            return max(0.92, jaccard_score)
        return jaccard_score

    @classmethod
    def _identity_match(
        cls,
        normalized_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str],
    ) -> Optional[Product]:
        canonical_category = cls.extract_canonical_category(normalized_name)
        identity_key = cls.identity_key(brand, canonical_category, variant, size, unit)
        if cls._requires_variant_review(brand, variant):
            return None
        if identity_key:
            match = Product.objects.filter(identity_key=identity_key).order_by("created_at").first()
            if match:
                logger.info(
                    f"[Product Matched] Canonical identity key: '{identity_key}' matched "
                    f"Product '{match.name}' (ID: {match.id})"
                )
                return match

        query = Q(normalized_name__isnull=False) & ~Q(normalized_name="")

        if brand:
            query &= (Q(brand__iexact=brand) | Q(brand__isnull=True) | Q(brand=""))

        if size and unit:
            query &= (
                Q(size=size, unit=unit) |
                Q(size__isnull=True) |
                Q(size="")
            )

        candidates = Product.objects.filter(query).order_by("created_at")
        best_match = None
        best_score = 0.0
        exact_cluster_matches = []

        for candidate in candidates:
            if not cls._variant_compatible(variant, brand, candidate):
                continue
            score = cls._identity_score(normalized_name, brand, size, unit, variant, candidate)
            if (
                brand
                and size
                and unit
                and candidate.brand
                and candidate.size
                and candidate.unit
                and cls.canonical_brand(brand) == cls.canonical_brand(candidate.brand)
                and size == candidate.size
                and unit == candidate.unit
                and cls._variant_compatible(variant, brand, candidate)
            ):
                exact_cluster_matches.append(candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score >= 0.85:
            logger.info(
                f"[Product Matched] Identity match: '{normalized_name}' matched with "
                f"'{best_match.normalized_name}' (score: {best_score:.2f}, ID: {best_match.id})"
            )
            return best_match

        incoming_tokens = cls.identity_tokens(normalized_name, brand)
        if not incoming_tokens and len(exact_cluster_matches) == 1:
            match = exact_cluster_matches[0]
            logger.info(
                f"[Product Matched] Brand+size singleton match: '{normalized_name}' matched with "
                f"'{match.normalized_name}' (ID: {match.id})"
            )
            return match

        return None

    @classmethod
    def _review_score(
        cls,
        normalized_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str],
        candidate: Product,
    ) -> float:
        identity_score = cls._identity_score(normalized_name, brand, size, unit, variant, candidate)

        if not cls._brand_compatible(brand, candidate):
            return identity_score
        if not cls._size_compatible(size, unit, candidate):
            return identity_score
        if not cls._variant_compatible(variant, brand, candidate):
            return identity_score
        if not candidate.normalized_name:
            return identity_score

        similarity_score = SequenceMatcher(
            None,
            cls.clean_for_compare(normalized_name),
            cls.clean_for_compare(candidate.normalized_name),
        ).ratio()
        return max(identity_score, similarity_score)

    @classmethod
    def _best_review_candidate(
        cls,
        normalized_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str],
        exclude_product_id: Optional[Any] = None,
    ) -> Tuple[Optional[Product], float]:
        if not normalized_name:
            return None, 0.0

        best_match = None
        best_score = 0.0

        candidates = Product.objects.exclude(normalized_name__isnull=True).exclude(normalized_name="")
        if exclude_product_id:
            candidates = candidates.exclude(id=exclude_product_id)

        for candidate in candidates:
            score = cls._review_score(normalized_name, brand, size, unit, variant, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        return best_match, best_score

    @classmethod
    def _create_import_review(
        cls,
        *,
        raw: RawScrapedProduct,
        issue_type: str,
        normalized_name: Optional[str],
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        score: float,
        reason: str,
        matched_product: Optional[Product] = None,
        candidate_product: Optional[Product] = None,
    ) -> None:
        review, created = ProductImportReview.objects.update_or_create(
            raw_product=raw,
            issue_type=issue_type,
            candidate_product=candidate_product,
            defaults={
                "matched_product": matched_product,
                "store_name": cls.normalize_store_name(raw.store_name),
                "scraped_product_name": raw.product_name,
                "normalized_name": normalized_name,
                "brand": brand,
                "size": size,
                "unit": unit,
                "score": round(score, 4),
                "reason": reason,
            },
        )
        action = "Created" if created else "Updated"
        logger.info(
            "[Import Review %s] %s for raw '%s' from %s (score: %.2f)",
            action,
            review.get_issue_type_display(),
            raw.product_name,
            raw.store_name,
            score,
        )

    @classmethod
    def _record_alias(
        cls,
        *,
        product: Product,
        normalized_name: str,
        raw_name: str,
        store_name: str,
        confidence: float,
    ) -> None:
        alias, created = ProductAlias.objects.get_or_create(
            normalized_name=normalized_name,
            store_name=store_name,
            defaults={
                "product": product,
                "raw_name": raw_name,
                "source": ProductAlias.Source.IMPORTED,
                "confidence": confidence,
            },
        )
        if created or alias.source == ProductAlias.Source.REVIEWED:
            return
        alias.product = product
        alias.raw_name = raw_name
        alias.confidence = confidence
        alias.save()

    @staticmethod
    def extract_brand(name: str, raw_brand: Optional[str] = None) -> Optional[str]:
        if raw_brand and raw_brand.strip():
            return ProductMatchService.canonical_brand(raw_brand)
            
        if not name:
            return None
            
        name_lower = name.lower()
        
        for brand in KNOWN_BRANDS:
            if re.search(r'\b' + re.escape(brand) + r'\b', name_lower):
                return ProductMatchService.canonical_brand(brand)
                
        words = [w for w in re.split(r'[^a-z0-9]', name_lower) if w]
        if words:
            return ProductMatchService.canonical_brand(words[0])
            
        return None

    @staticmethod
    def extract_size_unit(name: str) -> Tuple[Optional[str], Optional[str]]:
        if not name:
            return None, None
            
        name_lower = name.lower()
        match = SIZE_UNIT_RE.search(name_lower)
        if match:
            raw_size = match.group(1)
            raw_unit = match.group(2)
            std_unit = UNIT_MAP.get(raw_unit.lower(), raw_unit.lower())
            
            try:
                float_size = float(raw_size)
                if float_size.is_integer():
                    normalized_size = str(int(float_size))
                else:
                    normalized_size = str(float_size)
            except ValueError:
                normalized_size = raw_size
                
            return normalized_size, std_unit
            
        return None, None

    @classmethod
    def find_match(
        cls,
        normalized_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str] = None,
    ) -> Optional[Product]:
        """Search existing products for a match using exact name or fuzzy matching.

        Matching strategy (in order):
          1. Exact match on normalized_name (fast, indexed).
          2. Fuzzy match within the same brand+size+unit cluster.
          3. Broad fuzzy match across all products by normalized_name (catches
             cases where an existing product has null size/unit).
        """
        if not normalized_name:
            return None
            
        if variant is None:
            variant = cls.extract_variant(normalized_name)

        identity_match = cls._identity_match(normalized_name, brand, size, unit, variant)
        if identity_match:
            logger.info(
                f"[Duplicate Product Detected] Incoming '{normalized_name}' would duplicate "
                f"existing Product '{identity_match.normalized_name}' (ID: {identity_match.id}); reusing canonical record."
            )
            return identity_match

        exact_match = Product.objects.filter(normalized_name=normalized_name).first()
        if exact_match and cls._variant_compatible(variant, brand, exact_match):
            logger.info(f"[Product Matched] Exact match found for: '{normalized_name}' (ID: {exact_match.id})")
            return exact_match

        if cls._requires_variant_review(brand, variant):
            return None
            
        threshold = getattr(settings, 'PRODUCT_SIMILARITY_THRESHOLD', 0.8)
        clean_query = cls.clean_for_compare(normalized_name)
            
        if brand and size:
            candidates = Product.objects.filter(brand=brand, size=size, unit=unit)
        elif brand:
            candidates = Product.objects.filter(brand=brand)
        else:
            candidates = Product.objects.all()
        
        best_match = None
        best_ratio = 0.0
        
        for candidate in candidates:
            if not candidate.normalized_name:
                continue
            if not cls._variant_compatible(variant, brand, candidate):
                continue
            
            clean_candidate = cls.clean_for_compare(candidate.normalized_name)
            ratio = SequenceMatcher(None, clean_query, clean_candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
                
        if best_ratio >= threshold:
            logger.info(f"[Product Matched] Fuzzy match found: '{normalized_name}' matched with '{best_match.normalized_name}' (similarity: {best_ratio:.2f}, ID: {best_match.id})")
            return best_match
            
        # 3. Broad fuzzy fallback: search ALL products by normalized_name.
        #    This catches the case where an existing canonical product has null
        #    size/unit (e.g. "Pembe Flour" was created without size/unit) and
        #    the incoming product has a size/unit that excludes it from the
        #    filtered search above.
        all_best_match = None
        all_best_ratio = 0.0
        
        for candidate in Product.objects.exclude(normalized_name__isnull=True).exclude(normalized_name=""):
            if candidate.id == (best_match.id if best_match else None):
                continue
            if not cls._brand_compatible(brand, candidate):
                continue
            if not cls._size_compatible(size, unit, candidate):
                continue
            if not cls._variant_compatible(variant, brand, candidate):
                continue
            clean_candidate = cls.clean_for_compare(candidate.normalized_name)
            ratio = SequenceMatcher(None, clean_query, clean_candidate).ratio()
            if ratio > all_best_ratio:
                all_best_ratio = ratio
                all_best_match = candidate
                
        if all_best_ratio >= threshold and all_best_ratio > best_ratio:
            logger.info(
                f"[Product Matched] Broad fuzzy fallback match: '{normalized_name}' matched with "
                f"'{all_best_match.normalized_name}' (similarity: {all_best_ratio:.2f}, ID: {all_best_match.id})"
            )
            return all_best_match
            
        return None

    @classmethod
    def _missing_variant_candidate(
        cls,
        brand: Optional[str],
        canonical_category: Optional[str],
        size: Optional[str],
        unit: Optional[str],
        variant: Optional[str],
    ) -> Optional[Product]:
        if variant or not brand or cls.canonical_brand(brand) not in MULTI_VARIANT_BRANDS or not size or not unit:
            return None
        candidates = Product.objects.filter(size=size, unit=unit).exclude(brand__isnull=True).exclude(brand="")
        if canonical_category:
            candidates = candidates.filter(canonical_category=canonical_category)
        for candidate in candidates.order_by("created_at"):
            if cls.canonical_brand(candidate.brand) != cls.canonical_brand(brand):
                continue
            if cls._candidate_variant(candidate):
                return candidate
        return None

    @classmethod
    def process_raw_product(cls, raw: RawScrapedProduct, branch: Optional[Branch] = None) -> Tuple[Product, bool, bool]:
        name = raw.product_name.strip()
        store_name = cls.normalize_store_name(raw.store_name)
        normalized_name = cls.normalize_name(name)
        brand = cls.extract_brand(name)
        size, unit = cls.extract_size_unit(name)
        canonical_category = cls.extract_canonical_category(normalized_name)
        variant = cls.extract_variant(normalized_name)
        identity_key = cls.identity_key(brand, canonical_category, variant, size, unit)
        
        with transaction.atomic():
            if brand and size:
                list(Product.objects.select_for_update().filter(brand=brand, size=size, unit=unit))
            elif brand:
                list(Product.objects.select_for_update().filter(brand=brand))
            else:
                list(Product.objects.select_for_update().filter(normalized_name=normalized_name))
                
            product = cls._alias_match(normalized_name, store_name)
            if not product:
                product = cls.find_match(normalized_name, brand, size, unit, variant)
            created = False
            possible_duplicate = None
            possible_duplicate_score = 0.0
            
            if not product:
                double_check = Product.objects.filter(normalized_name=normalized_name).first()
                if double_check:
                    product = double_check
                    logger.info(
                        f"[Product Matched] Race condition / double-check match: raw '{name}' matched to "
                        f"existing '{product.name}' (ID: {product.id})"
                    )
                else:
                    fuzzy_fallback = cls._broad_fuzzy_match(normalized_name, brand, size, unit, variant)
                    if fuzzy_fallback:
                        product = fuzzy_fallback
                        logger.info(
                            f"[Product Matched] Broad fuzzy fallback in double-check: '{normalized_name}' matched to "
                            f"'{product.normalized_name}' (ID: {product.id})"
                        )
                    else:
                        possible_duplicate, possible_duplicate_score = cls._best_review_candidate(
                            normalized_name,
                            brand,
                            size,
                            unit,
                            variant,
                        )
                        product = Product.objects.create(
                            name=name,
                            normalized_name=normalized_name,
                            brand=brand,
                            size=size,
                            unit=unit,
                            canonical_category=canonical_category,
                            variant=variant,
                            identity_key=identity_key,
                            image_url=raw.image_url,
                            category=None,
                        )
                        created = True
                        logger.info(f"[Product Created] Created new canonical product: '{name}' (ID: {product.id})")
            else:
                score = cls._review_score(normalized_name, brand, size, unit, variant, product)
                auto_threshold = getattr(settings, 'PRODUCT_SIMILARITY_THRESHOLD', 0.8)
                low_confidence_threshold = getattr(settings, 'PRODUCT_LOW_CONFIDENCE_MATCH_THRESHOLD', 0.92)
                if auto_threshold <= score < low_confidence_threshold:
                    cls._create_import_review(
                        raw=raw,
                        issue_type=ProductImportReview.IssueType.LOW_CONFIDENCE_MATCH,
                        matched_product=product,
                        candidate_product=product,
                        normalized_name=normalized_name,
                        brand=brand,
                        size=size,
                        unit=unit,
                        score=score,
                        reason=(
                            "Importer accepted this match automatically, but the score is below "
                            "the high-confidence threshold. Confirm it should stay linked."
                        ),
                    )
                updated = False
                if not product.brand and brand:
                    product.brand = brand
                    updated = True
                if not product.size and size:
                    product.size = size
                    updated = True
                if not product.unit and unit:
                    product.unit = unit
                    updated = True
                if not product.canonical_category and canonical_category:
                    product.canonical_category = canonical_category
                    updated = True
                if not product.variant and variant:
                    product.variant = variant
                    updated = True
                if not product.identity_key and identity_key:
                    product.identity_key = identity_key
                    updated = True
                if not product.image_url and raw.image_url:
                    product.image_url = raw.image_url
                    updated = True
                if updated:
                    product.save()
            
            store_product, sp_created = StoreProduct.objects.update_or_create(
                product=product,
                store_name=store_name,
                defaults={
                    'store_product_name': name,
                    'price': raw.price,
                    'product_url': raw.product_url,
                    'scraped_image_url': raw.image_url,
                }
            )
            
            if sp_created:
                logger.info(f"[StoreProduct Created] Created StoreProduct for '{store_name}': '{name}' (Price: {raw.price}) linked to Product '{product.name}' (ID: {product.id})")
            else:
                logger.info(f"[StoreProduct Updated] Updated StoreProduct for '{store_name}': '{name}' (Price: {raw.price}) linked to Product '{product.name}' (ID: {product.id})")

            cls._record_alias(
                product=product,
                normalized_name=normalized_name,
                raw_name=name,
                store_name=store_name,
                confidence=1.0 if created else cls._review_score(normalized_name, brand, size, unit, variant, product),
            )

            missing_variant_candidate = cls._missing_variant_candidate(
                brand,
                canonical_category,
                size,
                unit,
                variant,
            )
            if missing_variant_candidate and missing_variant_candidate.id != product.id:
                cls._create_import_review(
                    raw=raw,
                    issue_type=ProductImportReview.IssueType.MISSING_VARIANT,
                    matched_product=product,
                    candidate_product=missing_variant_candidate,
                    normalized_name=normalized_name,
                    brand=brand,
                    size=size,
                    unit=unit,
                    score=0.0,
                    reason=(
                        "This brand has known variants, but the scraped name did not include a variant. "
                        "Review before adding aliases or merging products."
                    ),
                )

            if created and possible_duplicate:
                review_min_score = getattr(settings, 'PRODUCT_REVIEW_MIN_SIMILARITY', 0.55)
                auto_threshold = getattr(settings, 'PRODUCT_SIMILARITY_THRESHOLD', 0.8)
                if review_min_score <= possible_duplicate_score < auto_threshold:
                    cls._create_import_review(
                        raw=raw,
                        issue_type=ProductImportReview.IssueType.POSSIBLE_DUPLICATE,
                        matched_product=product,
                        candidate_product=possible_duplicate,
                        normalized_name=normalized_name,
                        brand=brand,
                        size=size,
                        unit=unit,
                        score=possible_duplicate_score,
                        reason=(
                            "Importer created a new canonical Product, but an existing product "
                            "looked similar enough to require admin review."
                        ),
                    )
            
            price_created = False
            if branch and raw.price is not None:
                pp, price_created = ProductPrice.objects.update_or_create(
                    product=product,
                    branch=branch,
                    defaults={
                        'price': raw.price,
                        'source_url': raw.product_url
                    }
                )
                
            raw.processed = True
            raw.save()
            
        return product, created, price_created

    @classmethod
    def _broad_fuzzy_match(
        cls,
        normalized_name: str,
        brand: Optional[str] = None,
        size: Optional[str] = None,
        unit: Optional[str] = None,
        variant: Optional[str] = None,
    ) -> Optional[Product]:
        """Search ALL products by normalized_name similarity as a last resort.
        
        This is a safety net used just before creating a new Product to catch
        cases where the initial find_match() missed an existing product due to
        restrictive brand/size/unit filters.
        """
        if not normalized_name:
            return None
        threshold = getattr(settings, 'PRODUCT_SIMILARITY_THRESHOLD', 0.8)
        clean_query = cls.clean_for_compare(normalized_name)
        if variant is None:
            variant = cls.extract_variant(normalized_name)
        if cls._requires_variant_review(brand, variant):
            return None
        
        best_match = None
        best_ratio = 0.0
        
        for candidate in Product.objects.exclude(normalized_name__isnull=True).exclude(normalized_name=""):
            if not cls._brand_compatible(brand, candidate):
                continue
            if not cls._size_compatible(size, unit, candidate):
                continue
            if not cls._variant_compatible(variant, brand, candidate):
                continue
            clean_candidate = cls.clean_for_compare(candidate.normalized_name)
            ratio = SequenceMatcher(None, clean_query, clean_candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
                
        if best_ratio >= threshold:
            return best_match
        return None
