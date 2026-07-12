from django.contrib.auth.models import User
from django.test import TestCase

from baskets.models import Basket, BasketItem
from supermarkets.models import Branch, Supermarket

from .confirmed_duplicate_repair import (
    apply_confirmed_duplicate_repairs,
    plan_confirmed_duplicate_repairs,
)
from .models import (
    Product,
    ProductAlias,
    ProductImportReview,
    ProductPrice,
    RawScrapedProduct,
    StoreProduct,
)


class ConfirmedDuplicateRepairTests(TestCase):
    def create_pair(self, canonical_name, canonical_normalized, duplicate_name, duplicate_normalized):
        canonical = Product.objects.create(
            name=canonical_name,
            normalized_name=canonical_normalized,
            size="500" if "sausage" in duplicate_normalized else "5",
            unit="g" if "sausage" in duplicate_normalized else "kg",
        )
        duplicate = Product.objects.create(
            name=duplicate_name,
            normalized_name=duplicate_normalized,
            size=canonical.size,
            unit=canonical.unit,
        )
        return canonical, duplicate

    def create_both_pairs(self):
        sausage = self.create_pair(
            "Farmer's Choice Safari Beef Sausage 500 Gm",
            "farmer s choice safari beef sausage 500g",
            "Beef Sausages (Safari) 500Gm",
            "beef sausages safari 500g",
        )
        rice = self.create_pair(
            "Daawat Long Grain Rice 5Kg",
            "daawat long grain rice 5kg",
            "Daawati Long Grain Rice 5Kg",
            "daawati long grain rice 5kg",
        )
        return sausage, rice

    def test_plan_finds_only_confirmed_pairs_without_writes(self):
        self.create_both_pairs()

        plans = plan_confirmed_duplicate_repairs()

        self.assertEqual([plan.status for plan in plans], ["ready", "ready"])
        self.assertEqual(Product.objects.count(), 4)
        self.assertEqual(ProductAlias.objects.count(), 0)

    def test_plan_reports_missing_pair_without_guessing(self):
        self.create_pair(
            "Daawat Long Grain Rice 5Kg",
            "daawat long grain rice 5kg",
            "Daawati Long Grain Rice 5Kg",
            "daawati long grain rice 5kg",
        )

        plans = plan_confirmed_duplicate_repairs()

        self.assertEqual([plan.status for plan in plans], ["missing", "ready"])

    def test_apply_moves_dependencies_creates_reviewed_alias_and_is_idempotent(self):
        (canonical, duplicate), _ = self.create_both_pairs()
        supermarket = Supermarket.objects.create(name="CleanShelf")
        branch = Branch.objects.create(
            supermarket=supermarket,
            name="Website",
            city="Nairobi",
        )
        StoreProduct.objects.create(
            product=duplicate,
            store_name="CleanShelf",
            store_product_name="Beef Sausages (Safari) 500Gm",
            price="490.00",
        )
        ProductPrice.objects.create(
            product=duplicate,
            branch=branch,
            price="490.00",
        )
        user = User.objects.create_user(username="shopper")
        basket = Basket.objects.create(user=user)
        BasketItem.objects.create(basket=basket, product=canonical, quantity=1)
        BasketItem.objects.create(basket=basket, product=duplicate, quantity=2)
        ProductAlias.objects.create(
            product=duplicate,
            normalized_name="beef sausages safari 500g",
            raw_name="Beef Sausages (Safari) 500Gm",
            store_name="CleanShelf",
        )
        raw = RawScrapedProduct.objects.create(
            store_name="CleanShelf",
            product_name="Beef Sausages (Safari) 500Gm",
            price="490.00",
        )
        review = ProductImportReview.objects.create(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.POSSIBLE_DUPLICATE,
            matched_product=duplicate,
            candidate_product=duplicate,
            store_name="CleanShelf",
            scraped_product_name=raw.product_name,
        )

        result = apply_confirmed_duplicate_repairs()

        self.assertEqual(result.merged, 2)
        self.assertFalse(Product.objects.filter(pk=duplicate.pk).exists())
        self.assertTrue(
            StoreProduct.objects.filter(product=canonical, store_name="CleanShelf").exists()
        )
        self.assertTrue(ProductPrice.objects.filter(product=canonical, branch=branch).exists())
        self.assertEqual(BasketItem.objects.get(basket=basket, product=canonical).quantity, 3)
        alias = ProductAlias.objects.get(
            normalized_name="beef sausage safari 500g",
            store_name="CleanShelf",
        )
        self.assertEqual(alias.product, canonical)
        self.assertEqual(alias.source, ProductAlias.Source.REVIEWED)
        review.refresh_from_db()
        self.assertEqual(review.matched_product, canonical)
        self.assertEqual(review.candidate_product, canonical)

        second = apply_confirmed_duplicate_repairs()
        self.assertEqual(second.merged, 0)
        self.assertEqual(Product.objects.count(), 2)
