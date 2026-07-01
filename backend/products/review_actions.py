from django.db import transaction
from django.utils import timezone

from .models import ProductAlias, ProductImportReview, ProductPrice, StoreProduct


def _request_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _merge_store_product(source_product, target_product, review):
    source = StoreProduct.objects.filter(
        product=source_product,
        store_name=review.store_name,
    ).first()
    if not source:
        return False

    target = StoreProduct.objects.filter(
        product=target_product,
        store_name=review.store_name,
    ).first()
    if target:
        target.store_product_name = source.store_product_name
        target.price = source.price
        target.product_url = source.product_url
        target.scraped_image_url = source.scraped_image_url
        target.save()
        source.delete()
    else:
        source.product = target_product
        source.save()
    return True


def _source_product_from_store_row(target_product, review):
    raw_url = getattr(review.raw_product, "product_url", None)
    candidates = StoreProduct.objects.filter(store_name=review.store_name).exclude(
        product=target_product
    )
    if raw_url:
        match = candidates.filter(product_url=raw_url).select_related("product").first()
        if match:
            return match.product
    match = candidates.filter(
        store_product_name__iexact=review.scraped_product_name
    ).select_related("product").first()
    return match.product if match else None


def _merge_product_prices(source_product, target_product, review):
    raw_url = getattr(review.raw_product, "product_url", None)
    prices = ProductPrice.objects.filter(product=source_product)
    if raw_url:
        prices = prices.filter(source_url=raw_url)

    moved = 0
    for price in list(prices):
        target = ProductPrice.objects.filter(
            product=target_product,
            branch=price.branch,
        ).first()
        if target:
            target.price = price.price
            target.source_url = price.source_url
            target.save()
            price.delete()
        else:
            price.product = target_product
            price.save()
        moved += 1
    return moved


def _delete_empty_duplicate(product):
    if (
        product
        and not product.store_products.exists()
        and not product.prices.exists()
        and not product.import_match_reviews.exclude(status=ProductImportReview.Status.REVIEWED).exists()
    ):
        product.delete()
        return True
    return False


@transaction.atomic
def accept_import_review(review, user=None):
    target_product = review.candidate_product or review.matched_product
    if not target_product:
        return {
            "accepted": False,
            "reason": "Review has no candidate or matched product to accept.",
        }

    source_product = review.matched_product
    if source_product and source_product.id == target_product.id:
        source_product = None
    if not source_product:
        source_product = _source_product_from_store_row(target_product, review)

    alias, _ = ProductAlias.objects.update_or_create(
        normalized_name=review.normalized_name,
        store_name=review.store_name,
        defaults={
            "product": target_product,
            "raw_name": review.scraped_product_name,
            "source": ProductAlias.Source.REVIEWED,
            "confidence": 1.0,
            "reviewed_by": _request_user(user),
        },
    )

    moved_store_product = False
    moved_prices = 0
    if source_product:
        moved_store_product = _merge_store_product(source_product, target_product, review)
        moved_prices = _merge_product_prices(source_product, target_product, review)

    review.status = ProductImportReview.Status.REVIEWED
    review.reviewed_at = timezone.now()
    review.admin_notes = (
        f"Accepted as alias for '{target_product.name}'. "
        f"StoreProduct moved: {moved_store_product}. ProductPrice rows moved: {moved_prices}."
    )
    review.matched_product = target_product
    review.save(update_fields=["status", "reviewed_at", "admin_notes", "matched_product"])

    deleted_source = _delete_empty_duplicate(source_product) if source_product else False

    return {
        "accepted": True,
        "alias": alias,
        "target_product": target_product,
        "moved_store_product": moved_store_product,
        "moved_prices": moved_prices,
        "deleted_source": deleted_source,
    }


@transaction.atomic
def ignore_import_review(review, user=None):
    review.status = ProductImportReview.Status.IGNORED
    review.reviewed_at = timezone.now()
    if not review.admin_notes:
        review.admin_notes = "Rejected by admin; keep products separate."
    review.save(update_fields=["status", "reviewed_at", "admin_notes"])
    return {"ignored": True}
