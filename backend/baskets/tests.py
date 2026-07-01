from django.test import TestCase
from decimal import Decimal
from supermarkets.models import Supermarket, Branch
from products.models import Product, ProductPrice
from baskets.models import Basket, BasketItem

class BasketComparisonTestCase(TestCase):
    def setUp(self):
        # Create Supermarkets
        self.carrefour = Supermarket.objects.create(name="Carrefour", logo_url="http://logo.com/carrefour.png")
        self.naivas = Supermarket.objects.create(name="Naivas", logo_url="http://logo.com/naivas.png")

        # Create Branches
        self.carrefour_sarit = Branch.objects.create(
            supermarket=self.carrefour,
            name="Sarit Centre",
            latitude=Decimal("-1.2588"),
            longitude=Decimal("36.8028")
        )
        self.naivas_westlands = Branch.objects.create(
            supermarket=self.naivas,
            name="Westlands",
            latitude=Decimal("-1.2612"),
            longitude=Decimal("36.8042")
        )

        # Create Products
        self.milk = Product.objects.create(name="Fresh Milk 1L", category="Dairy", brand="Brookside")
        self.bread = Product.objects.create(name="White Bread 400g", category="Bakery", brand="Supa Loaf")
        self.sugar = Product.objects.create(name="Local Sugar 1kg", category="Pantry", brand="Kabras")

        # Set Prices
        # Milk prices: Carrefour (KSh 100), Naivas (KSh 105)
        ProductPrice.objects.create(product=self.milk, branch=self.carrefour_sarit, price=Decimal("100.00"))
        ProductPrice.objects.create(product=self.milk, branch=self.naivas_westlands, price=Decimal("105.00"))

        # Bread prices: Carrefour (KSh 65), Naivas (KSh 60)
        ProductPrice.objects.create(product=self.bread, branch=self.carrefour_sarit, price=Decimal("65.00"))
        ProductPrice.objects.create(product=self.bread, branch=self.naivas_westlands, price=Decimal("60.00"))

        # Sugar prices: ONLY at Carrefour (KSh 200) - Naivas has no sugar price
        ProductPrice.objects.create(product=self.sugar, branch=self.carrefour_sarit, price=Decimal("200.00"))

        # Create a Basket
        self.basket = Basket.objects.create(name="Weekly Groceries")

    def test_basket_compare_prices_complete_vs_incomplete(self):
        # Add 1 Milk and 2 Breads to basket (both stores have these items)
        BasketItem.objects.create(basket=self.basket, product=self.milk, quantity=1)
        BasketItem.objects.create(basket=self.basket, product=self.bread, quantity=2)

        # Carrefour cost: 1*100 + 2*65 = 230
        # Naivas cost: 1*105 + 2*60 = 225
        comparison = self.basket.compare_prices()

        self.assertEqual(len(comparison), 2)
        
        # Naivas should be first because it is cheaper (225 vs 230) and both are complete
        self.assertEqual(comparison[0]['supermarket_name'], "Naivas")
        self.assertEqual(comparison[0]['total_cost'], 225.00)
        self.assertTrue(comparison[0]['is_complete'])

        self.assertEqual(comparison[1]['supermarket_name'], "Carrefour")
        self.assertEqual(comparison[1]['total_cost'], 230.00)
        self.assertTrue(comparison[1]['is_complete'])

    def test_basket_compare_prices_missing_items(self):
        # Add 1 Milk (at both) and 1 Sugar (ONLY at Carrefour)
        BasketItem.objects.create(basket=self.basket, product=self.milk, quantity=1)
        BasketItem.objects.create(basket=self.basket, product=self.sugar, quantity=1)

        comparison = self.basket.compare_prices()

        self.assertEqual(len(comparison), 2)

        # Carrefour has all items, so it should be complete and ranked first (even though Naivas' subset is cheaper)
        self.assertEqual(comparison[0]['supermarket_name'], "Carrefour")
        self.assertTrue(comparison[0]['is_complete'])
        self.assertEqual(comparison[0]['total_cost'], 300.00)  # 100 milk + 200 sugar

        # Naivas is missing sugar, so it is incomplete and ranked second
        self.assertEqual(comparison[1]['supermarket_name'], "Naivas")
        self.assertFalse(comparison[1]['is_complete'])
        self.assertEqual(comparison[1]['total_cost'], 105.00)  # Only milk price
        self.assertEqual(comparison[1]['items_available'], 1)
        self.assertEqual(comparison[1]['total_items'], 2)
        self.assertEqual(len(comparison[1]['missing_items']), 1)
        self.assertEqual(comparison[1]['missing_items'][0]['name'], "Local Sugar 1kg")

    def test_basket_compare_prices_aggregates_same_supermarket_branches(self):
        # Naivas has milk at Westlands and sugar at Website. It should be
        # complete at supermarket level instead of split into two partial rows.
        naivas_website = Branch.objects.create(supermarket=self.naivas, name="Website")
        ProductPrice.objects.create(product=self.sugar, branch=naivas_website, price=Decimal("190.00"))

        BasketItem.objects.create(basket=self.basket, product=self.milk, quantity=1)
        BasketItem.objects.create(basket=self.basket, product=self.sugar, quantity=1)

        comparison = self.basket.compare_prices()
        naivas_result = next(item for item in comparison if item["supermarket_name"] == "Naivas")

        self.assertTrue(naivas_result["is_complete"])
        self.assertEqual(naivas_result["items_available"], 2)
        self.assertEqual(naivas_result["total_items"], 2)
        self.assertEqual(naivas_result["total_cost"], 295.00)
        self.assertEqual(naivas_result["branch_name"], "Multiple branches")
