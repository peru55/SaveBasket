from django.test import TestCase
from django.conf import settings
from .models import Product, ProductAlias, StoreProduct, RawScrapedProduct, ProductPrice, ProductImportReview
from .match_service import ProductMatchService
from .review_actions import accept_import_review, ignore_import_review
from supermarkets.models import Supermarket, Branch


class ProductMatchServiceTests(TestCase):
    def test_normalize_name(self):
        self.assertEqual(ProductMatchService.normalize_name("Pembe Flour 2 KG"), "pembe flour 2kg")
        self.assertEqual(ProductMatchService.normalize_name("Pembe Maize Flour 2kg"), "pembe maize flour 2kg")
        self.assertEqual(ProductMatchService.normalize_name("Pembe Sifted Maize Flour 2 Kg"), "pembe sifted maize flour 2kg")
        self.assertEqual(ProductMatchService.normalize_name("Brookside Fresh Milk 1.5 Litres"), "brookside fresh milk 1.5l")
        self.assertEqual(ProductMatchService.normalize_name("Kabras Sugar 500 Grams"), "kabras sugar 500g")
        self.assertEqual(ProductMatchService.normalize_name("Kabras Sugar & Honey"), "kabras sugar and honey")

    def test_normalize_store_name(self):
        self.assertEqual(ProductMatchService.normalize_store_name("quickmart"), "Quickmart")
        self.assertEqual(ProductMatchService.normalize_store_name("CleanShelf"), "CleanShelf")
        self.assertEqual(ProductMatchService.normalize_store_name("clean shelf"), "CleanShelf")

    def test_extract_brand(self):
        self.assertEqual(ProductMatchService.extract_brand("Pembe Maize Flour 2kg"), "pembe")
        self.assertEqual(ProductMatchService.extract_brand("Brookside Dairy Best 500ml"), "brookside")
        self.assertEqual(ProductMatchService.extract_brand("Soko Maize Meal 2kg"), "soko")
        self.assertEqual(ProductMatchService.extract_brand("Blueband Margarine 500g"), "blue band")
        
        self.assertEqual(ProductMatchService.extract_brand("Ajab wheat flour"), "ajab")
        self.assertEqual(ProductMatchService.extract_brand("UnknownProduct 2kg"), "unknownproduct")
        
        self.assertEqual(ProductMatchService.extract_brand("Product name", "RawBrandName"), "rawbrandname")

    def test_extract_size_unit(self):
        self.assertEqual(ProductMatchService.extract_size_unit("Pembe Maize Flour 2kg"), ("2", "kg"))
        self.assertEqual(ProductMatchService.extract_size_unit("Pembe Flour 2 KG"), ("2", "kg"))
        self.assertEqual(ProductMatchService.extract_size_unit("Milk 500ml"), ("500", "ml"))
        self.assertEqual(ProductMatchService.extract_size_unit("Brookside Fresh Milk 1.5 L"), ("1.5", "l"))
        self.assertEqual(ProductMatchService.extract_size_unit("Elianto Corn Oil 2Lt"), ("2", "l"))
        self.assertEqual(ProductMatchService.extract_size_unit("Brookside Fresh Milk 1.5 Litre"), ("1.5", "l"))
        self.assertEqual(ProductMatchService.extract_size_unit("No Size Product"), (None, None))

    def test_find_match_exact(self):
        p = Product.objects.create(
            name="Pembe Maize Flour 2kg",
            normalized_name="pembe maize flour 2kg",
            brand="pembe",
            size="2",
            unit="kg"
        )
        match = ProductMatchService.find_match("pembe maize flour 2kg", "pembe", "2", "kg")
        self.assertEqual(match, p)

    def test_find_match_fuzzy(self):
        p = Product.objects.create(
            name="Pembe Maize Flour 2kg",
            normalized_name="pembe maize flour 2kg",
            brand="pembe",
            size="2",
            unit="kg"
        )
        
        match = ProductMatchService.find_match("pembe flour 2kg", "pembe", "2", "kg")
        self.assertEqual(match, p)
        
        no_match = ProductMatchService.find_match("pembe flour 1kg", "pembe", "1", "kg")
        self.assertIsNone(no_match)

    def test_find_match_broad_fallback_when_existing_product_has_null_size(self):
        """The exact bug scenario: an existing Product has null size/unit because
        it was created from a product name that lacked size info (e.g. "Pembe Flour").
        A new import with size/unit (e.g. "Pembe Flour 2kg") should still match via
        the broad fuzzy fallback instead of creating a duplicate."""
        p = Product.objects.create(
            name="Pembe Flour",
            normalized_name="pembe flour",
            brand="pembe",
            size=None,
            unit=None
        )
        
        StoreProduct.objects.create(
            product=p,
            store_name="Naivas",
            store_product_name="Pembe Flour",
            price=150.00
        )
        
        match = ProductMatchService.find_match("pembe flour 2kg", "pembe", "2", "kg")
        self.assertIsNotNone(match, "Broad fuzzy fallback should have matched!")
        self.assertEqual(match.id, p.id)

    def test_process_raw_product(self):
        s = Supermarket.objects.create(name="Naivas")
        b = Branch.objects.create(supermarket=s, name="Online", city="Nairobi")
        
        raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Pembe Maize Flour 2kg",
            price=180.00,
            product_url="https://naivas.online/pembe-2kg",
            image_url="https://naivas.online/pembe.png"
        )
        
        product, created, price_created = ProductMatchService.process_raw_product(raw, branch=b)
        self.assertTrue(created)
        self.assertTrue(price_created)
        self.assertEqual(product.name, "Pembe Maize Flour 2kg")
        self.assertEqual(product.brand, "pembe")
        self.assertEqual(product.size, "2")
        self.assertEqual(product.unit, "kg")
        
        sp = StoreProduct.objects.get(product=product, store_name="Naivas")
        self.assertEqual(sp.price, 180.00)
        self.assertEqual(sp.store_product_name, "Pembe Maize Flour 2kg")
        
        pp = ProductPrice.objects.get(product=product, branch=b)
        self.assertEqual(pp.price, 180.00)
        
        raw2 = RawScrapedProduct.objects.create(
            store_name="Carrefour",
            product_name="Pembe Flour 2 KG",
            price=185.00,
            product_url="https://carrefour.ke/pembe-2kg",
            image_url="https://carrefour.ke/pembe.png"
        )
        
        product2, created2, price_created2 = ProductMatchService.process_raw_product(raw2)
        self.assertFalse(created2)
        self.assertEqual(product2, product)
        
        sp2 = StoreProduct.objects.get(product=product, store_name="Carrefour")
        self.assertEqual(sp2.price, 185.00)

    def test_repeated_imports_and_price_updates(self):
        raw1 = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Pembe Maize Flour 2kg",
            price=180.00,
            product_url="https://naivas.online/pembe-2kg"
        )
        p1, created1, _ = ProductMatchService.process_raw_product(raw1)
        self.assertTrue(created1)
        
        raw2 = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Pembe Maize Flour 2kg",
            price=175.00,
            product_url="https://naivas.online/pembe-2kg-new"
        )
        p2, created2, _ = ProductMatchService.process_raw_product(raw2)
        
        self.assertFalse(created2)
        self.assertEqual(p1, p2)
        
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(StoreProduct.objects.filter(product=p1, store_name="Naivas").count(), 1)
        
        sp = StoreProduct.objects.get(product=p1, store_name="Naivas")
        self.assertEqual(sp.price, 175.00)
        self.assertEqual(sp.product_url, "https://naivas.online/pembe-2kg-new")

    def test_fuzzy_matching_with_descriptive_noise(self):
        p = Product.objects.create(
            name="Pembe Maize Flour 2kg",
            normalized_name="pembe maize flour 2kg",
            brand="pembe",
            size="2",
            unit="kg"
        )
        
        match1 = ProductMatchService.find_match("pembe sifted maize flour 2kg", "pembe", "2", "kg")
        self.assertEqual(match1, p)
        
        match2 = ProductMatchService.find_match("pembe premium maize meal 2kg", "pembe", "2", "kg")
        self.assertEqual(match2, p)

    def test_new_supermarket_links_correctly(self):
        p = Product.objects.create(
            name="Kabras Sugar 2kg",
            normalized_name="kabras sugar 2kg",
            brand="kabras",
            size="2",
            unit="kg"
        )
        StoreProduct.objects.create(product=p, store_name="Naivas", store_product_name="Kabras Sugar 2kg", price=300.00)
        
        raw = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Kabras Sugar White 2kg",
            price=290.00
        )
        
        matched_product, created, _ = ProductMatchService.process_raw_product(raw)
        
        self.assertFalse(created)
        self.assertEqual(matched_product, p)
        
        self.assertEqual(p.store_products.count(), 2)
        self.assertTrue(p.store_products.filter(store_name="Naivas").exists())
        self.assertTrue(p.store_products.filter(store_name="Quickmart").exists())

    def test_bug_null_size_unit_existing_product_preserves_relationships(self):
        """REGRESSION TEST: the exact bug described in the task.
        
        Scenario:
          - Existing Product "Pembe Flour" (no size/unit) with StoreProducts
            for both Naivas and Quickmart.
          - New import of "Pembe Maize Flour 2kg" which HAS size/unit.
        
        Expected outcome:
          - The existing Product should be matched (not duplicated).
          - All StoreProduct relationships (Naivas + Quickmart) remain intact.
          - Only ONE canonical Product exists.
        """
        existing_product = Product.objects.create(
            name="Pembe Flour",
            normalized_name="pembe flour",
            brand="pembe",
            size=None,
            unit=None
        )
        
        StoreProduct.objects.create(
            product=existing_product,
            store_name="Naivas",
            store_product_name="Pembe Flour",
            price=150.00
        )
        StoreProduct.objects.create(
            product=existing_product,
            store_name="Quickmart",
            store_product_name="Pembe Flour",
            price=155.00
        )
        
        self.assertEqual(existing_product.store_products.count(), 2)
        
        raw = RawScrapedProduct.objects.create(
            store_name="Carrefour",
            product_name="Pembe Maize Flour 2kg",
            price=170.00
        )
        
        product, created, _ = ProductMatchService.process_raw_product(raw)
        
        self.assertFalse(created, "Should NOT create a new Product - must match existing!")
        self.assertEqual(product.id, existing_product.id, "Should match the existing Product!")
        
        self.assertEqual(
            product.store_products.count(),
            3,
            "Should have 3 StoreProducts (Naivas + Quickmart + Carrefour) all under ONE Product!"
        )
        self.assertTrue(product.store_products.filter(store_name="Naivas").exists())
        self.assertTrue(product.store_products.filter(store_name="Quickmart").exists())
        self.assertTrue(product.store_products.filter(store_name="Carrefour").exists())
        
        self.assertEqual(Product.objects.count(), 1)

    def test_exact_bug_scenario_two_supermarkets_then_import_third(self):
        """EXACT bug reproduction from the task description.
        
        Before import:
          - Pembe Flour
            - Carrefour
            - Naivas
            - Quickmart
        
        Expected after importing a new product that matches the same canonical:
          - Pembe Flour
            - Carrefour
            - Naivas
            - Quickmart
            + NewSupermarket
        
        NOT split into:
          - Pembe Flour (Carrefour only)
          - Pembe Flour (Naivas + Quickmart)
        """
        canonical = Product.objects.create(
            name="Pembe Flour",
            normalized_name="pembe flour",
            brand="pembe",
            size=None,
            unit=None
        )
        
        for store_name, price in [("Carrefour", 160), ("Naivas", 150), ("Quickmart", 155)]:
            StoreProduct.objects.create(
                product=canonical,
                store_name=store_name,
                store_product_name="Pembe Flour",
                price=price
            )
        
        self.assertEqual(canonical.store_products.count(), 3, "3 StoreProducts should exist before import")
        
        raw = RawScrapedProduct.objects.create(
            store_name="Tuskys",
            product_name="Pembe Sifted Maize Flour 2 Kg",
            price=165.00
        )
        
        product, created, _ = ProductMatchService.process_raw_product(raw)
        
        self.assertFalse(created, "Must NOT create a duplicate Product!")
        self.assertEqual(product.id, canonical.id, "Must reuse the existing canonical Product!")
        
        self.assertEqual(
            product.store_products.count(),
            4,
            "Should have 4 StoreProducts (Carrefour + Naivas + Quickmart + Tuskys) under ONE Product"
        )
        
        for store_name in ["Carrefour", "Naivas", "Quickmart", "Tuskys"]:
            self.assertTrue(
                product.store_products.filter(store_name=store_name).exists(),
                f"StoreProduct for {store_name} must exist!"
            )
        
        self.assertEqual(Product.objects.count(), 1)

    def test_duplicate_prevention_with_broad_fallback(self):
        """Even if the incoming product has a different brand prediction, the
        broad fallback should still match based on normalized_name similarity
        when the original product had no size/unit."""
        
        p = Product.objects.create(
            name="Pembe Flour",
            normalized_name="pembe flour",
            brand=None,
            size=None,
            unit=None
        )
        StoreProduct.objects.create(product=p, store_name="Naivas", store_product_name="Pembe Flour", price=140.00)
        
        raw = RawScrapedProduct.objects.create(
            store_name="Carrefour",
            product_name="Pembe Flour 2kg",
            price=145.00
        )
        
        product, created, _ = ProductMatchService.process_raw_product(raw)
        
        self.assertFalse(created, "Must match existing product!")
        self.assertEqual(product.id, p.id)
        self.assertEqual(product.store_products.count(), 2)
        self.assertEqual(Product.objects.count(), 1)

    def test_repeated_import_from_same_supermarket_preserves_other_links(self):
        """Importing from the SAME supermarket multiple times should not
        affect StoreProduct records from OTHER supermarkets."""
        
        p = Product.objects.create(
            name="Sugar 1kg",
            normalized_name="sugar 1kg",
            brand="kabras",
            size="1",
            unit="kg"
        )
        StoreProduct.objects.create(product=p, store_name="Naivas", store_product_name="Sugar 1kg", price=200.00)
        StoreProduct.objects.create(product=p, store_name="Quickmart", store_product_name="Sugar 1kg", price=195.00)
        
        raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Kabras Sugar 1kg",
            price=190.00
        )
        
        product, created, _ = ProductMatchService.process_raw_product(raw)
        
        self.assertFalse(created)
        self.assertEqual(product.id, p.id)
        
        self.assertEqual(product.store_products.count(), 2)
        self.assertTrue(product.store_products.filter(store_name="Quickmart").exists())
        
        sp_naivas = product.store_products.get(store_name="Naivas")
        self.assertEqual(sp_naivas.price, 190.00)

    def test_brookside_uht_fino_quickmart_matches_existing_500ml_milk(self):
        """Quickmart Brookside UHT/Fino slug names should not split 500ml milk."""
        p = Product.objects.create(
            name="Brookside Dairy Best 500Ml",
            normalized_name="brookside dairy best 500ml",
            brand="brookside",
            size="500",
            unit="ml"
        )
        StoreProduct.objects.create(
            product=p,
            store_name="Naivas",
            store_product_name="Brookside Dairy Best 500Ml",
            price=58.00
        )

        raw = RawScrapedProduct.objects.create(
            store_name="quickmart",
            product_name="brookside-uht-fino-carton-500ml-50",
            price=58.00
        )

        product, created, _ = ProductMatchService.process_raw_product(raw)

        self.assertFalse(created)
        self.assertEqual(product.id, p.id)
        self.assertEqual(Product.objects.count(), 1)
        self.assertTrue(product.store_products.filter(store_name="Quickmart").exists())
        self.assertTrue(product.store_products.filter(store_name="Naivas").exists())

    def test_brand_size_only_name_matches_single_existing_brand_size_product(self):
        p = Product.objects.create(
            name="Elianto Corn Oil 1L",
            normalized_name="elianto corn oil 1l",
            brand="elianto",
            size="1",
            unit="l"
        )
        StoreProduct.objects.create(
            product=p,
            store_name="Naivas",
            store_product_name="Elianto Corn Oil 1L",
            price=600.00
        )

        raw = RawScrapedProduct.objects.create(
            store_name="Cleanshelf",
            product_name="Elianto 1Ltr",
            price=615.00
        )

        product, created, _ = ProductMatchService.process_raw_product(raw)

        self.assertFalse(created)
        self.assertEqual(product.id, p.id)
        self.assertEqual(Product.objects.count(), 1)
        self.assertTrue(product.store_products.filter(store_name="Naivas").exists())
        self.assertTrue(product.store_products.filter(store_name="CleanShelf").exists())

    def test_brand_size_only_name_does_not_match_ambiguous_brand_size_cluster(self):
        Product.objects.create(
            name="Brand Corn Oil 1L",
            normalized_name="brand corn oil 1l",
            brand="brand",
            size="1",
            unit="l"
        )
        Product.objects.create(
            name="Brand Olive Oil 1L",
            normalized_name="brand olive oil 1l",
            brand="brand",
            size="1",
            unit="l"
        )

        raw = RawScrapedProduct.objects.create(
            store_name="Cleanshelf",
            product_name="Brand 1L",
            price=615.00
        )

        product, created, _ = ProductMatchService.process_raw_product(raw)

        self.assertTrue(created)
        self.assertEqual(product.normalized_name, "brand 1l")
        self.assertEqual(Product.objects.count(), 3)

    def test_category_alias_identity_key_matches_equivalent_store_names(self):
        raw1 = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Elianto Corn Oil 1L",
            price=600.00
        )
        p1, created1, _ = ProductMatchService.process_raw_product(raw1)

        raw2 = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Elianto Cooking Oil 1Ltr",
            price=599.00
        )
        p2, created2, _ = ProductMatchService.process_raw_product(raw2)

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(p1.id, p2.id)
        self.assertEqual(p1.identity_key, "elianto|oil|1|l")
        self.assertEqual(Product.objects.count(), 1)
        self.assertTrue(p1.store_products.filter(store_name="Naivas").exists())
        self.assertTrue(p1.store_products.filter(store_name="Quickmart").exists())

    def test_extract_variant_for_blue_band_flavors(self):
        self.assertEqual(ProductMatchService.extract_variant("blue band original spread 500g"), "original")
        self.assertEqual(ProductMatchService.extract_variant("blue band choco spread 500g"), "chocolate")
        self.assertEqual(ProductMatchService.extract_variant("blue band chocolate spread 500g"), "chocolate")
        self.assertEqual(ProductMatchService.extract_variant("blue band vanilla spread 500g"), "vanilla")

    def test_blue_band_variants_remain_separate_products(self):
        names = [
            "Blue Band Original Spread 500G",
            "Blue Band Choco Spread 500G",
            "Blue Band Vanilla Spread 500G",
        ]
        products = []
        for index, name in enumerate(names, start=1):
            raw = RawScrapedProduct.objects.create(
                store_name="Quickmart",
                product_name=name,
                price=250 + index,
            )
            product, created, _ = ProductMatchService.process_raw_product(raw)
            products.append(product)
            self.assertTrue(created)

        self.assertEqual(Product.objects.count(), 3)
        self.assertEqual({product.variant for product in products}, {"original", "chocolate", "vanilla"})
        self.assertEqual(
            {product.identity_key for product in products},
            {
                "blue band|spread|original|500|g",
                "blue band|spread|chocolate|500|g",
                "blue band|spread|vanilla|500|g",
            },
        )

    def test_missing_blue_band_variant_goes_to_review_instead_of_merging(self):
        original_raw = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Blue Band Original Spread 500G",
            price=275.00,
        )
        original, created, _ = ProductMatchService.process_raw_product(original_raw)
        self.assertTrue(created)

        ambiguous_raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Blue Band Spread 500G",
            price=275.00,
        )
        ambiguous, ambiguous_created, _ = ProductMatchService.process_raw_product(ambiguous_raw)

        self.assertTrue(ambiguous_created)
        self.assertNotEqual(ambiguous.id, original.id)
        self.assertTrue(
            ProductImportReview.objects.filter(
                raw_product=ambiguous_raw,
                issue_type=ProductImportReview.IssueType.MISSING_VARIANT,
                candidate_product=original,
            ).exists()
        )

    def test_blueband_spelling_without_variant_goes_to_review_instead_of_merging(self):
        original_raw = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Blue Band Original Spread 500G",
            price=275.00,
        )
        original, created, _ = ProductMatchService.process_raw_product(original_raw)
        self.assertTrue(created)

        naivas_raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Blueband Margarine 500g",
            price=275.00,
        )
        naivas_product, naivas_created, _ = ProductMatchService.process_raw_product(naivas_raw)

        self.assertTrue(naivas_created)
        self.assertEqual(naivas_product.brand, "blue band")
        self.assertIsNone(naivas_product.identity_key)
        self.assertNotEqual(naivas_product.id, original.id)
        self.assertTrue(
            ProductImportReview.objects.filter(
                raw_product=naivas_raw,
                issue_type=ProductImportReview.IssueType.MISSING_VARIANT,
                candidate_product=original,
            ).exists()
        )

    def test_wrong_blue_band_variant_price_does_not_overwrite_original_product_price(self):
        quickmart = Supermarket.objects.create(name="Quickmart")
        quickmart_branch = Branch.objects.create(supermarket=quickmart, name="Website", city="Nairobi")
        naivas = Supermarket.objects.create(name="Naivas")
        naivas_branch = Branch.objects.create(supermarket=naivas, name="Website", city="Nairobi")

        original_raw = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Blue Band Original Spread 500G",
            price=275.00,
        )
        original, original_created, _ = ProductMatchService.process_raw_product(original_raw, branch=quickmart_branch)
        self.assertTrue(original_created)

        wrong_variant_raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Blue Band Choco Spread 500G",
            price=1199.00,
        )
        chocolate, chocolate_created, _ = ProductMatchService.process_raw_product(wrong_variant_raw, branch=naivas_branch)

        self.assertTrue(chocolate_created)
        self.assertNotEqual(chocolate.id, original.id)
        self.assertEqual(ProductPrice.objects.get(product=original, branch=quickmart_branch).price, 275.00)
        self.assertFalse(ProductPrice.objects.filter(product=original, branch=naivas_branch).exists())
        self.assertEqual(ProductPrice.objects.get(product=chocolate, branch=naivas_branch).price, 1199.00)

    def test_quickmart_lt_unit_does_not_overwrite_elianto_1l_with_2l_price(self):
        supermarket = Supermarket.objects.create(name="Quickmart")
        branch = Branch.objects.create(supermarket=supermarket, name="Website", city="Nairobi")
        raw1 = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Elianto Corn Oil 1L",
            price=599.00,
            product_url="https://www.quickmart.co.ke/elianto-corn-oil-1l-55",
        )
        one_litre, created1, one_litre_price_created = ProductMatchService.process_raw_product(raw1, branch=branch)

        raw2 = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Elianto Corn Oil 2Lt",
            price=1197.00,
            product_url="https://www.quickmart.co.ke/elianto-corn-oil-2lt-10",
        )
        two_litre, created2, two_litre_price_created = ProductMatchService.process_raw_product(raw2, branch=branch)

        self.assertTrue(created1)
        self.assertTrue(created2)
        self.assertTrue(one_litre_price_created)
        self.assertTrue(two_litre_price_created)
        self.assertNotEqual(one_litre.id, two_litre.id)
        self.assertEqual(one_litre.identity_key, "elianto|oil|1|l")
        self.assertEqual(two_litre.identity_key, "elianto|oil|2|l")
        self.assertEqual(one_litre.store_products.get(store_name="Quickmart").price, 599.00)
        self.assertEqual(two_litre.store_products.get(store_name="Quickmart").price, 1197.00)
        self.assertEqual(ProductPrice.objects.get(product=one_litre, branch=branch).price, 599.00)
        self.assertEqual(ProductPrice.objects.get(product=two_litre, branch=branch).price, 1197.00)

    def test_imported_alias_is_reused_for_future_matching(self):
        raw1 = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Elianto Corn Oil 1L",
            price=600.00
        )
        product, created, _ = ProductMatchService.process_raw_product(raw1)
        self.assertTrue(created)

        ProductAlias.objects.create(
            product=product,
            raw_name="Elianto 1Ltr",
            normalized_name="elianto 1l",
            store_name="Cleanshelf",
            source=ProductAlias.Source.REVIEWED,
            confidence=1.0,
        )

        raw2 = RawScrapedProduct.objects.create(
            store_name="Cleanshelf",
            product_name="Elianto 1Ltr",
            price=615.00
        )
        matched, created2, _ = ProductMatchService.process_raw_product(raw2)

        self.assertFalse(created2)
        self.assertEqual(matched.id, product.id)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(
            ProductAlias.objects.get(normalized_name="elianto 1l", store_name="Cleanshelf").product,
            product,
        )

    def test_store_product_update_or_create_uses_correct_lookup(self):
        """Verify that StoreProduct.update_or_create uses (product, store_name)
        so it never accidentally overwrites another supermarket's record."""
        
        p = Product.objects.create(
            name="Milk 500ml",
            normalized_name="milk 500ml",
            brand="brookside",
            size="500",
            unit="ml"
        )
        
        sp1 = StoreProduct.objects.create(
            product=p,
            store_name="Naivas",
            store_product_name="Fresh Milk 500ml",
            price=70.00
        )
        
        sp2 = StoreProduct.objects.create(
            product=p,
            store_name="Carrefour",
            store_product_name="Brookside Milk 500ml",
            price=75.00
        )
        
        sp1_updated, created = StoreProduct.objects.update_or_create(
            product=p,
            store_name="Naivas",
            defaults={
                'store_product_name': 'Fresh Milk 500ml Updated',
                'price': 65.00,
            }
        )
        
        self.assertFalse(created)
        self.assertEqual(sp1_updated.id, sp1.id)
        self.assertEqual(sp1_updated.price, 65.00)
        
        sp2.refresh_from_db()
        self.assertEqual(sp2.price, 75.00)
        self.assertEqual(sp2.store_product_name, "Brookside Milk 500ml")

    def test_import_review_created_for_low_confidence_auto_match(self):
        product = Product.objects.create(
            name="Tropical Heat Curry Powder 100g",
            normalized_name="tropical heat curry powder 100g",
            brand="tropical",
            size="100",
            unit="g"
        )

        raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Tropical Heat Spice Powder 100g",
            price=120.00
        )

        matched_product, created, _ = ProductMatchService.process_raw_product(raw)

        self.assertFalse(created)
        self.assertEqual(matched_product, product)

        review = ProductImportReview.objects.get(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.LOW_CONFIDENCE_MATCH,
        )
        self.assertEqual(review.status, ProductImportReview.Status.OPEN)
        self.assertEqual(review.matched_product, product)
        self.assertEqual(review.candidate_product, product)
        self.assertEqual(review.store_name, "Naivas")
        self.assertGreaterEqual(review.score, getattr(settings, "PRODUCT_SIMILARITY_THRESHOLD", 0.8))
        self.assertLess(review.score, getattr(settings, "PRODUCT_LOW_CONFIDENCE_MATCH_THRESHOLD", 0.92))

    def test_import_review_created_when_new_product_has_near_duplicate_candidate(self):
        existing_product = Product.objects.create(
            name="Blue Band Margarine 500g",
            normalized_name="blue band margarine 500g",
            brand="blue band",
            size="500",
            unit="g"
        )

        raw = RawScrapedProduct.objects.create(
            store_name="Quickmart",
            product_name="Blue Band Spread 500g",
            price=180.00
        )

        new_product, created, _ = ProductMatchService.process_raw_product(raw)

        self.assertTrue(created)
        self.assertNotEqual(new_product.id, existing_product.id)

        review = ProductImportReview.objects.get(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.POSSIBLE_DUPLICATE,
        )
        self.assertEqual(review.status, ProductImportReview.Status.OPEN)
        self.assertEqual(review.matched_product, new_product)
        self.assertEqual(review.candidate_product, existing_product)
        self.assertEqual(review.normalized_name, "blue band spread 500g")
        self.assertGreaterEqual(review.score, getattr(settings, "PRODUCT_REVIEW_MIN_SIMILARITY", 0.55))
        self.assertLess(review.score, getattr(settings, "PRODUCT_SIMILARITY_THRESHOLD", 0.8))

    def test_accept_import_review_creates_reviewed_alias_and_merges_store_product(self):
        target = Product.objects.create(
            name="Blue Band Original Spread 500G",
            normalized_name="blue band original spread 500g",
            brand="blue band",
            canonical_category="spread",
            variant="original",
            size="500",
            unit="g",
            identity_key="blue band|spread|original|500|g",
        )
        duplicate = Product.objects.create(
            name="Blueband Margarine 500g",
            normalized_name="blueband margarine 500g",
            brand="blue band",
            canonical_category="spread",
            size="500",
            unit="g",
        )
        raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Blueband Margarine 500g",
            price=275.00,
            product_url="https://www.naivas.online/blueband-margarine-500g",
        )
        StoreProduct.objects.create(
            product=duplicate,
            store_name="Naivas",
            store_product_name="Blueband Margarine 500g",
            price=275.00,
            product_url=raw.product_url,
        )
        review = ProductImportReview.objects.create(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.MISSING_VARIANT,
            matched_product=duplicate,
            candidate_product=target,
            store_name="Naivas",
            scraped_product_name="Blueband Margarine 500g",
            normalized_name="blueband margarine 500g",
            brand="blue band",
            size="500",
            unit="g",
            reason="Missing variant should be accepted as original after review.",
        )

        result = accept_import_review(review)

        self.assertTrue(result["accepted"])
        self.assertTrue(result["moved_store_product"])
        self.assertFalse(Product.objects.filter(id=duplicate.id).exists())
        self.assertTrue(
            StoreProduct.objects.filter(
                product=target,
                store_name="Naivas",
                store_product_name="Blueband Margarine 500g",
            ).exists()
        )
        alias = ProductAlias.objects.get(
            normalized_name="blueband margarine 500g",
            store_name="Naivas",
        )
        self.assertEqual(alias.product, target)
        self.assertEqual(alias.source, ProductAlias.Source.REVIEWED)
        review.refresh_from_db()
        self.assertEqual(review.status, ProductImportReview.Status.REVIEWED)
        self.assertEqual(review.matched_product, target)

    def test_accept_import_review_finds_source_product_from_store_row(self):
        target = Product.objects.create(
            name="Blue Band Original Spread 500G",
            normalized_name="blue band original spread 500g",
            brand="blue band",
            canonical_category="spread",
            variant="original",
            size="500",
            unit="g",
            identity_key="blue band|spread|original|500|g",
        )
        source = Product.objects.create(
            name="Blueband Margarine 500g",
            normalized_name="blueband margarine 500g",
            brand="blue band",
            canonical_category="spread",
            size="500",
            unit="g",
        )
        raw = RawScrapedProduct.objects.create(
            store_name="Naivas",
            product_name="Blueband Margarine 500g",
            price=275.00,
            product_url="https://www.naivas.online/blueband-margarine-500g",
        )
        StoreProduct.objects.create(
            product=source,
            store_name="Naivas",
            store_product_name="Blueband Margarine 500g",
            price=275.00,
            product_url=raw.product_url,
        )
        review = ProductImportReview.objects.create(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.MISSING_VARIANT,
            matched_product=target,
            candidate_product=target,
            store_name="Naivas",
            scraped_product_name="Blueband Margarine 500g",
            normalized_name="blueband margarine 500g",
            brand="blue band",
            size="500",
            unit="g",
            reason="Review already points to target but source row is separate.",
        )

        result = accept_import_review(review)

        self.assertTrue(result["accepted"])
        self.assertTrue(result["moved_store_product"])
        self.assertTrue(StoreProduct.objects.filter(product=target, store_name="Naivas").exists())
        self.assertFalse(StoreProduct.objects.filter(product=source, store_name="Naivas").exists())

    def test_reject_import_review_keeps_products_separate(self):
        target = Product.objects.create(name="Blue Band Original Spread 250G")
        duplicate = Product.objects.create(name="Blueband Spread 250Gm")
        raw = RawScrapedProduct.objects.create(
            store_name="CleanShelf",
            product_name="Blueband Spread 250Gm",
            price=110.00,
        )
        review = ProductImportReview.objects.create(
            raw_product=raw,
            issue_type=ProductImportReview.IssueType.POSSIBLE_DUPLICATE,
            matched_product=duplicate,
            candidate_product=target,
            store_name="CleanShelf",
            scraped_product_name="Blueband Spread 250Gm",
            normalized_name="blueband spread 250g",
            reason="Admin decided this is separate.",
        )

        ignore_import_review(review)

        review.refresh_from_db()
        self.assertEqual(review.status, ProductImportReview.Status.IGNORED)
        self.assertTrue(Product.objects.filter(id=target.id).exists())
        self.assertTrue(Product.objects.filter(id=duplicate.id).exists())
        self.assertFalse(ProductAlias.objects.filter(normalized_name="blueband spread 250g").exists())
