from dataclasses import dataclass

from django.db import transaction

from baskets.models import BasketItem

from .match_service import ProductMatchService
from .models import (
    Product,
    ProductAlias,
    ProductImportReview,
    ProductPrice,
    StoreProduct,
)


@dataclass(frozen=True)
class ConfirmedDuplicatePair:
    label: str
    canonical: str
    duplicate: str
    alias_store: str
    alias_raw_name: str


@dataclass(frozen=True)
class RepairPlan:
    pair: ConfirmedDuplicatePair
    status: str
    canonical_id: object = None
    duplicate_id: object = None


@dataclass(frozen=True)
class RepairResult:
    merged: int
    skipped: int
    ambiguous: int
    normalized: int


CONFIRMED_DUPLICATE_PAIRS = (
    ConfirmedDuplicatePair(
        label="Farmer's Choice Safari sausage 500 g",
        canonical="farmer s choice safari beef sausage 500g",
        duplicate="beef sausages safari 500g",
        alias_store="CleanShelf",
        alias_raw_name="Beef Sausages (Safari) 500Gm",
    ),
    ConfirmedDuplicatePair(
        label="Daawat long grain rice 5 kg",
        canonical="daawat long grain rice 5kg",
        duplicate="daawati long grain rice 5kg",
        alias_store="CleanShelf",
        alias_raw_name="Daawati Long Grain Rice 5Kg",
    ),
)


def plan_confirmed_duplicate_repairs():
    plans = []
    for pair in CONFIRMED_DUPLICATE_PAIRS:
        canonical_ids = list(
            Product.objects.filter(normalized_name=pair.canonical).values_list(
                "id", flat=True
            )
        )
        duplicate_ids = list(
            Product.objects.filter(normalized_name=pair.duplicate).values_list(
                "id", flat=True
            )
        )
        if len(canonical_ids) > 1 or len(duplicate_ids) > 1:
            plans.append(RepairPlan(pair=pair, status="ambiguous"))
        elif len(canonical_ids) == 1 and len(duplicate_ids) == 1:
            plans.append(
                RepairPlan(
                    pair=pair,
                    status="ready",
                    canonical_id=canonical_ids[0],
                    duplicate_id=duplicate_ids[0],
                )
            )
        elif len(canonical_ids) == 1:
            plans.append(
                RepairPlan(
                    pair=pair,
                    status="canonical_only",
                    canonical_id=canonical_ids[0],
                )
            )
        else:
            plans.append(RepairPlan(pair=pair, status="missing"))
    return plans


def _move_store_products(canonical, duplicate):
    for source in list(StoreProduct.objects.filter(product=duplicate)):
        target = StoreProduct.objects.filter(
            product=canonical,
            store_name=source.store_name,
        ).first()
        if target:
            if source.last_updated > target.last_updated:
                target.store_product_name = source.store_product_name
                target.price = source.price
                target.product_url = source.product_url
                target.scraped_image_url = source.scraped_image_url
                target.save()
            source.delete()
        else:
            source.product = canonical
            source.save()


def _move_prices(canonical, duplicate):
    for source in list(ProductPrice.objects.filter(product=duplicate)):
        target = ProductPrice.objects.filter(
            product=canonical,
            branch=source.branch,
        ).first()
        if target:
            if source.updated_at > target.updated_at:
                target.price = source.price
                target.source_url = source.source_url
                target.save()
            source.delete()
        else:
            source.product = canonical
            source.save()


def _move_basket_items(canonical, duplicate):
    for source in list(BasketItem.objects.filter(product=duplicate)):
        target = BasketItem.objects.filter(
            basket=source.basket,
            product=canonical,
        ).first()
        if target:
            target.quantity += source.quantity
            target.save(update_fields=["quantity"])
            source.delete()
        else:
            source.product = canonical
            source.save()


def _move_aliases(canonical, duplicate):
    for source in list(ProductAlias.objects.filter(product=duplicate)):
        target = ProductAlias.objects.filter(
            normalized_name=source.normalized_name,
            store_name=source.store_name,
        ).exclude(pk=source.pk).first()
        if target:
            target.product = canonical
            target.save(update_fields=["product"])
            source.delete()
        else:
            source.product = canonical
            source.save(update_fields=["product"])


def _move_reviews(canonical, duplicate):
    for review in list(ProductImportReview.objects.filter(candidate_product=duplicate)):
        conflict = ProductImportReview.objects.filter(
            raw_product=review.raw_product,
            issue_type=review.issue_type,
            candidate_product=canonical,
        ).exclude(pk=review.pk).first()
        if conflict:
            if conflict.matched_product_id == duplicate.id:
                conflict.matched_product = canonical
                conflict.save(update_fields=["matched_product"])
            review.delete()
        else:
            review.candidate_product = canonical
            review.save(update_fields=["candidate_product"])

    ProductImportReview.objects.filter(matched_product=duplicate).update(
        matched_product=canonical
    )


def _assert_duplicate_is_empty(duplicate):
    remaining = {
        "store products": duplicate.store_products.exists(),
        "prices": duplicate.prices.exists(),
        "basket items": duplicate.basket_items.exists(),
        "aliases": duplicate.aliases.exists(),
        "matched reviews": duplicate.import_match_reviews.exists(),
        "candidate reviews": duplicate.import_candidate_reviews.exists(),
    }
    unresolved = [name for name, exists in remaining.items() if exists]
    if unresolved:
        raise RuntimeError(
            f"Cannot delete confirmed duplicate; unresolved: {', '.join(unresolved)}"
        )


def _normalize_canonical_metadata(canonical):
    normalized = ProductMatchService.normalize_name(canonical.name)
    brand = ProductMatchService.extract_brand(canonical.name)
    size, unit = ProductMatchService.extract_size_unit(canonical.name)
    category = ProductMatchService.extract_canonical_category(normalized)
    variant = ProductMatchService.extract_variant(normalized)
    identity_key = ProductMatchService.identity_key(
        brand,
        category,
        variant,
        size,
        unit,
    )
    desired = {
        "brand": brand,
        "size": size,
        "unit": unit,
        "canonical_category": category,
        "variant": variant,
        "identity_key": identity_key,
    }
    changed = [field for field, value in desired.items() if getattr(canonical, field) != value]
    if not changed:
        return False
    for field, value in desired.items():
        setattr(canonical, field, value)
    canonical.save(update_fields=changed + ["updated_at"])
    return True


def _apply_plan(plan):
    products = {
        product.id: product
        for product in Product.objects.select_for_update().filter(
            id__in=[plan.canonical_id, plan.duplicate_id]
        )
    }
    canonical = products[plan.canonical_id]
    duplicate = products[plan.duplicate_id]

    metadata_changed = _normalize_canonical_metadata(canonical)

    _move_store_products(canonical, duplicate)
    _move_prices(canonical, duplicate)
    _move_basket_items(canonical, duplicate)
    _move_aliases(canonical, duplicate)
    _move_reviews(canonical, duplicate)

    alias_name = ProductMatchService.normalize_name(plan.pair.alias_raw_name)
    ProductAlias.objects.update_or_create(
        normalized_name=alias_name,
        store_name=plan.pair.alias_store,
        defaults={
            "product": canonical,
            "raw_name": plan.pair.alias_raw_name,
            "source": ProductAlias.Source.REVIEWED,
            "confidence": 1.0,
        },
    )

    _assert_duplicate_is_empty(duplicate)
    duplicate.delete()
    return metadata_changed


@transaction.atomic
def apply_confirmed_duplicate_repairs():
    plans = plan_confirmed_duplicate_repairs()
    merged = 0
    skipped = 0
    ambiguous = 0
    normalized = 0
    for plan in plans:
        if plan.status == "ambiguous":
            ambiguous += 1
            continue
        if plan.status == "canonical_only":
            canonical = Product.objects.select_for_update().get(pk=plan.canonical_id)
            normalized += int(_normalize_canonical_metadata(canonical))
            skipped += 1
            continue
        if plan.status != "ready":
            skipped += 1
            continue
        normalized += int(_apply_plan(plan))
        merged += 1
    return RepairResult(
        merged=merged,
        skipped=skipped,
        ambiguous=ambiguous,
        normalized=normalized,
    )
