import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from products.models import Product, ProductAlias, StoreProduct, ProductPrice
from products.match_service import ProductMatchService
from baskets.models import BasketItem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize existing products, detect duplicates, and merge them into canonical products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print duplicates detected without modifying the database",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.8,
            help="Similarity threshold for fuzzy matching (default: 0.8)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        threshold = options["threshold"]

        self.stdout.write(self.style.NOTICE(f"Starting product deduplication (dry-run={dry_run}, threshold={threshold})..."))

        # Step 1: Normalize all existing products
        all_products = Product.objects.all().order_by("id")
        self.stdout.write(f"Phase 1: Normalizing {all_products.count()} existing products...")

        normalized_count = 0
        for p in all_products:
            norm_name = ProductMatchService.normalize_name(p.name)
            brand = ProductMatchService.extract_brand(p.name, p.brand)
            size, unit = ProductMatchService.extract_size_unit(p.name)
            canonical_category = ProductMatchService.extract_canonical_category(norm_name)
            variant = ProductMatchService.extract_variant(norm_name)
            identity_key = ProductMatchService.identity_key(brand, canonical_category, variant, size, unit)

            changed = False
            if p.normalized_name != norm_name:
                p.normalized_name = norm_name
                changed = True
            if p.brand != brand:
                p.brand = brand
                changed = True
            if p.size != size:
                p.size = size
                changed = True
            if p.unit != unit:
                p.unit = unit
                changed = True
            if p.canonical_category != canonical_category:
                p.canonical_category = canonical_category
                changed = True
            if p.variant != variant:
                p.variant = variant
                changed = True
            if p.identity_key != identity_key:
                p.identity_key = identity_key
                changed = True

            if changed:
                normalized_count += 1
                if not dry_run:
                    p.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully normalized {normalized_count} products."))

        # Step 2: Detect and merge duplicates
        self.stdout.write("Phase 2: Detecting duplicates and merging...")

        processed_canonical_ids = set()
        duplicates_merged = 0

        # Refetch all products to ensure normalized names are in memory/db
        products = list(Product.objects.all().order_by("created_at"))

        for i, p in enumerate(products):
            if p.id in processed_canonical_ids:
                continue

            # First, check if this product has StoreProduct records populated
            # If not, populate them from its existing branch pricing
            if not dry_run:
                self.populate_store_products(p)
                self.populate_aliases(p)

            # Find duplicates in the remaining products
            for other in products[i + 1:]:
                if other.id in processed_canonical_ids or other.id == p.id:
                    continue

                # We require brand and size/unit match, and check normalized_name similarity
                if other.brand == p.brand and other.size == p.size and other.unit == p.unit:
                    match_found = False
                    if other.normalized_name == p.normalized_name:
                        match_found = True
                        reason = "Exact normalized name match"
                    else:
                        identity_score = ProductMatchService._identity_score(
                            other.normalized_name,
                            other.brand,
                            other.size,
                            other.unit,
                            ProductMatchService.extract_variant(other.normalized_name),
                            p,
                        )
                        if identity_score >= 0.85:
                            match_found = True
                            reason = f"Canonical identity match (score: {identity_score:.2f})"
                        
                        # Use fuzzy sequence matching
                        if not match_found:
                            from difflib import SequenceMatcher
                            left = ProductMatchService.clean_for_compare(p.normalized_name)
                            right = ProductMatchService.clean_for_compare(other.normalized_name)
                            ratio = SequenceMatcher(None, left, right).ratio()
                            if ratio >= threshold:
                                match_found = True
                                reason = f"Fuzzy match (similarity: {ratio:.2f})"

                        if not match_found and self.brand_size_singleton_match(p, other):
                            match_found = True
                            reason = "Brand+size singleton match"

                    if match_found:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[Duplicate Product Detected] Duplicate found: '{other.name}' ({other.id}) matches canonical '{p.name}' ({p.id}) [{reason}]"
                            )
                        )
                        logger.info(f"[Duplicate Product Detected] Duplicate found: '{other.name}' ({other.id}) matches canonical '{p.name}' ({p.id}) [{reason}]")
                        duplicates_merged += 1

                        if not dry_run:
                            self.merge_products(p, other)
                            processed_canonical_ids.add(other.id)

            processed_canonical_ids.add(p.id)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry-run completed. Detected {duplicates_merged} duplicates."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Deduplication completed. Merged {duplicates_merged} duplicate products."))

    def brand_size_singleton_match(self, first: Product, second: Product) -> bool:
        if not first.brand or not first.size or not first.unit:
            return False
        if first.brand != second.brand or first.size != second.size or first.unit != second.unit:
            return False
        if not ProductMatchService._variant_compatible(
            ProductMatchService._candidate_variant(first),
            first.brand,
            second,
        ):
            return False

        first_tokens = ProductMatchService.identity_tokens(first.normalized_name, first.brand)
        second_tokens = ProductMatchService.identity_tokens(second.normalized_name, second.brand)
        if first_tokens and second_tokens:
            return False

        cluster_count = Product.objects.filter(
            brand=first.brand,
            size=first.size,
            unit=first.unit,
        ).count()
        return cluster_count == 2

    def populate_store_products(self, product: Product):
        """Populate StoreProduct records from existing ProductPrice records for a product."""
        prices = product.prices.all()
        for price_obj in prices:
            store_name = price_obj.branch.supermarket.name
            StoreProduct.objects.get_or_create(
                product=product,
                store_name=store_name,
                defaults={
                    "store_product_name": product.name,
                    "price": price_obj.price,
                    "product_url": price_obj.source_url,
                    "scraped_image_url": product.image_url,
                },
            )

    def populate_aliases(self, product: Product):
        for sp in product.store_products.all():
            normalized_name = ProductMatchService.normalize_name(sp.store_product_name)
            if not normalized_name:
                continue
            ProductAlias.objects.get_or_create(
                normalized_name=normalized_name,
                store_name=sp.store_name,
                defaults={
                    "product": product,
                    "raw_name": sp.store_product_name,
                    "source": ProductAlias.Source.IMPORTED,
                    "confidence": 1.0,
                },
            )

    def merge_products(self, canonical: Product, duplicate: Product):
        """Merge a duplicate product into the canonical product, reassigning related records."""
        with transaction.atomic():
            # 1. Move related StoreProduct records
            for sp in duplicate.store_products.all():
                existing_sp = canonical.store_products.filter(store_name=sp.store_name).first()
                if existing_sp:
                    # Keep the most recently updated one
                    if sp.last_updated > existing_sp.last_updated:
                        existing_sp.price = sp.price
                        existing_sp.store_product_name = sp.store_product_name
                        existing_sp.product_url = sp.product_url
                        existing_sp.scraped_image_url = sp.scraped_image_url
                        existing_sp.save()
                    sp.delete()
                else:
                    sp.product = canonical
                    sp.save()

            # 2. Move related ProductPrice records
            for pp in duplicate.prices.all():
                existing_pp = canonical.prices.filter(branch=pp.branch).first()
                if existing_pp:
                    # Keep the most recently updated price
                    if pp.updated_at > existing_pp.updated_at:
                        existing_pp.price = pp.price
                        existing_pp.source_url = pp.source_url
                        existing_pp.save()
                    pp.delete()
                else:
                    pp.product = canonical
                    pp.save()

            # 3. Reassign related BasketItem records
            for item in BasketItem.objects.filter(product=duplicate):
                existing_item = BasketItem.objects.filter(basket=item.basket, product=canonical).first()
                if existing_item:
                    existing_item.quantity += item.quantity
                    existing_item.save()
                    item.delete()
                else:
                    item.product = canonical
                    item.save()

            # 4. Delete the duplicate product
            duplicate_name = duplicate.name
            duplicate.delete()
            logger.info(f"Merged and deleted duplicate product: '{duplicate_name}' into '{canonical.name}'")
