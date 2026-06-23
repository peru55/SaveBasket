"""Tests for SaveBasket scrapers."""

import unittest

from scraper import EthicalScraper
from quickmart import parse_quickmart_search_results
from cleanshelf import fetch_cleanshelf_category_products, product_from_api_item


NAIVAS_PRODUCT_HTML = """
<html><head>
<meta property="og:title" content="Brookside Fresh Milk 1L" />
</head><body>
<h1>Hello there, please confirm that you are over 18 to proceed</h1>
<div class="text-xl mb-1">Brookside Fresh Milk 1L</div>
<div class="product-price"><span class="font-bold text-naivas-green">KES 135</span></div>
</body></html>
"""

NAIVAS_PRODUCT_HTML_WITH_COMMA = """
<html><head>
<meta property="og:title" content="Premium Cooking Oil 5L" />
</head><body>
<div class="text-xl mb-1">Premium Cooking Oil 5L</div>
<div class="product-price"><span class="font-bold text-naivas-green">KES 1,350</span></div>
</body></html>
"""

NAIVAS_PRODUCT_WITH_KSH = """
<html><head>
<meta property="og:title" content="Fresh Bread" />
</head><body>
<div class="text-xl mb-1">Fresh Bread</div>
<div class="product-price"><span class="font-bold text-naivas-green">KSh 65</span></div>
</body></html>
"""

QUICKMART_PRODUCT_HTML = """
<html><head>
<meta property="og:title" content="Brookside Uht Fino Carton 500Ml" />
</head><body>
<h1>Brookside Uht Fino Carton 500Ml</h1>
<div class="product-price">KES 58.00 KES 61.00 (4.92% Off)</div>
</body></html>
"""

# Quickmart HTML with comma-separated price (thousands)
QUICKMART_PRODUCT_WITH_COMMA = """
<html><head>
<meta property="og:title" content="Cooking Oil 5L" />
</head><body>
<h1>Cooking Oil 5L</h1>
<div class="product-price">KES 1,850.00</div>
</body></html>
"""

QUICKMART_SEARCH_HTML = """
<html><body>
<div class="products productInfoJs">
<div class="products-body">
<a title="Brookside Uht Whole Milk Tca 200Ml" href="/brookside-uht-whole-milk-tca-200ml-32">
  <div>KES 32.00</div>
</a>
</div>
</div>
</body></html>
"""

CARREFOUR_HTML = """
<html><body>
<h1>Brookside Whole Milk TCA 200ml Long Life</h1>
<p>## KES32.00(Inc. VAT)</p>
<script type="application/ld+json">
{"@type":"Product","name":"Brookside Whole Milk","offers":{"price":"32.00","priceCurrency":"KES"}}
</script>
</body></html>
"""

# Carrefour HTML with comma-separated price
CARREFOUR_HTML_WITH_COMMA = """
<html><body>
<h1>Premium Rice 5kg</h1>
<p>## KES 1,200.00 (Inc. VAT)</p>
<script type="application/ld+json">
{"@type":"Product","name":"Premium Rice","offers":{"price":"1200.00","priceCurrency":"KES"}}
</script>
</body></html>
"""

CLEANSHELF_PRODUCT_API_ITEM = {
    "id": 5121,
    "name": "CASSAVA PER KG",
    "slug": "cassava-per-kg",
    "price": "220.00",
    "sale_price": None,
    "stock_status": "instock",
    "category": {"id": 701, "name": "Groceries", "slug": "groceries"},
    "branchStock": [{"branch_id": "7", "is_in_stock": True}],
    "images": [
        {
            "url": "https://storage.chatcommerce.co.ke/Homechef/products/cassava.jpg",
            "alt": "CASSAVA PER KG",
            "order": 0,
        }
    ],
}

CLEANSHELF_PRODUCT_HTML = """
<html><body>
<div class="ProductDetail-module__page">
  <nav class="breadcrumb"><a>Home</a><a>Shop</a><a>Groceries</a></nav>
  <div class="ProductDetail-module__mainLayout">
    <img src="/_next/image?url=https%3A%2F%2Fstorage.chatcommerce.co.ke%2FHomechef%2Fproducts%2Fcassava.jpg&w=3840&q=75" />
    <div class="ProductDetail-module__detailColumn">
      <h1 class="ProductDetail-module__title">Cassava Per Kg</h1>
      <span>In stock</span>
      <span>KES 220.00</span>
    </div>
  </div>
</div>
</body></html>
"""


class FakeCleanShelfScraper:
    def __init__(self, pages):
        self.pages = pages

    def fetch_json(self, url, timeout=None, headers=None):
        if "page=2" in url:
            return self.pages[2]
        return self.pages[1]


class ScraperParserTests(unittest.TestCase):
    def setUp(self):
        self.scraper = EthicalScraper()

    def test_parse_money_simple(self):
        """Test _parse_money with basic formats."""
        self.assertEqual(self.scraper._parse_money("KES 135"), 135.0)
        self.assertEqual(self.scraper._parse_money("KSh 135"), 135.0)
        self.assertEqual(self.scraper._parse_money("135"), 135.0)
        self.assertEqual(self.scraper._parse_money("135.50"), 135.5)
        self.assertEqual(self.scraper._parse_money("KES 135.50"), 135.5)
        self.assertIsNone(self.scraper._parse_money(""))
        self.assertIsNone(self.scraper._parse_money(None))

    def test_parse_money_with_thousands_separator(self):
        """Test _parse_money correctly handles comma as thousands separator."""
        # CRITICAL BUG FIX: "1,350" should be 1350.0, NOT 1.35
        self.assertEqual(self.scraper._parse_money("KES 1,350"), 1350.0)
        self.assertEqual(self.scraper._parse_money("KSh 1,350"), 1350.0)
        self.assertEqual(self.scraper._parse_money("1,350"), 1350.0)
        self.assertEqual(self.scraper._parse_money("12,500"), 12500.0)
        self.assertEqual(self.scraper._parse_money("KES 12,500"), 12500.0)
        self.assertEqual(self.scraper._parse_money("KES 1,350.50"), 1350.5)
        self.assertEqual(self.scraper._parse_money("12,345,678"), 12345678.0)

    def test_parse_money_decimal_only(self):
        """Test _parse_money with decimal without thousands."""
        self.assertEqual(self.scraper._parse_money("KES 135.99"), 135.99)
        self.assertEqual(self.scraper._parse_money("135.00"), 135.0)

    def test_parse_prices_no_thousands_bug(self):
        """Verify parse_prices doesn't corrupt comma-separated thousands."""
        prices = self.scraper.parse_prices(
            "<html><body>KES 1,500</body></html>"
        )
        # "1,500" should be 1500.0, NOT 1.5
        self.assertIn(1500.0, prices)
        self.assertNotIn(1.5, prices)

    def test_parse_prices_multiple_formats(self):
        """parse_prices handles various price formats correctly."""
        prices = self.scraper.parse_prices(
            "<html><body>KES 135 KES 1,500 KES 12,500.50 100</body></html>"
        )
        self.assertIn(135.0, prices)
        self.assertIn(1500.0, prices)
        self.assertIn(12500.5, prices)
        self.assertIn(100.0, prices)

    def test_naivas_product_page(self):
        result = self.scraper.parse_site(
            "https://www.naivas.online/brookside-fresh-milk-1l",
            NAIVAS_PRODUCT_HTML,
        )
        self.assertEqual(result["title"], "Brookside Fresh Milk 1L")
        self.assertEqual(result["price"], 135.0)
        self.assertEqual(result["currency"], "KES")

    def test_naivas_product_with_comma_price(self):
        """Naivas price with thousands comma should parse correctly."""
        result = self.scraper.parse_site(
            "https://www.naivas.online/premium-cooking-oil-5l",
            NAIVAS_PRODUCT_HTML_WITH_COMMA,
        )
        self.assertEqual(result["title"], "Premium Cooking Oil 5L")
        self.assertEqual(result["price"], 1350.0)
        self.assertEqual(result["currency"], "KES")

    def test_naivas_with_ksh_prefix(self):
        """Naivas price with KSh prefix should parse correctly."""
        result = self.scraper.parse_site(
            "https://www.naivas.online/fresh-bread",
            NAIVAS_PRODUCT_WITH_KSH,
        )
        self.assertEqual(result["title"], "Fresh Bread")
        self.assertEqual(result["price"], 65.0)
        self.assertEqual(result["currency"], "KES")

    def test_quickmart_product_page(self):
        result = self.scraper.parse_site(
            "https://www.quickmart.co.ke/brookside-uht-fino-carton-500ml-36",
            QUICKMART_PRODUCT_HTML,
        )
        self.assertEqual(result["title"], "Brookside Uht Fino Carton 500Ml")
        self.assertEqual(result["price"], 58.0)

    def test_quickmart_product_with_comma_price(self):
        """Quickmart price with thousands comma should parse correctly."""
        result = self.scraper.parse_site(
            "https://www.quickmart.co.ke/cooking-oil-5l",
            QUICKMART_PRODUCT_WITH_COMMA,
        )
        self.assertEqual(result["title"], "Cooking Oil 5L")
        self.assertEqual(result["price"], 1850.0)

    def test_quickmart_search_results(self):
        result = parse_quickmart_search_results(self.scraper, QUICKMART_SEARCH_HTML)
        self.assertEqual(result["title"], "Brookside Uht Whole Milk Tca 200Ml")
        self.assertEqual(result["price"], 32.0)

    def test_carrefour_html_fallback(self):
        result = self.scraper.parse_site(
            "https://www.carrefour.ke/mafken/en/uht-milk-full-fat/brookside-uht-whole-milk-tca-200ml/p/43282",
            CARREFOUR_HTML,
        )
        self.assertIn("Brookside", result["title"])
        self.assertEqual(result["price"], 32.0)

    def test_carrefour_with_comma_price(self):
        """Carrefour price with comma should parse correctly."""
        result = self.scraper.parse_site(
            "https://www.carrefour.ke/mafken/en/rice/p/12345",
            CARREFOUR_HTML_WITH_COMMA,
        )
        self.assertIn("Premium Rice", result["title"])
        self.assertEqual(result["price"], 1200.0)

    def test_cleanshelf_api_item_mapping(self):
        result = product_from_api_item(CLEANSHELF_PRODUCT_API_ITEM)
        self.assertEqual(result["title"], "Cassava Per Kg")
        self.assertEqual(result["price"], "220.00")
        self.assertEqual(result["image_url"], "https://storage.chatcommerce.co.ke/Homechef/products/cassava.jpg")
        self.assertEqual(result["url"], "https://cleanshelf.online/product/cassava-per-kg")
        self.assertEqual(result["category"], "Groceries")
        self.assertEqual(result["availability"], "in_stock")

    def test_cleanshelf_parse_site_uses_product_api(self):
        original = self.scraper.fetch_json
        self.scraper.fetch_json = lambda url, timeout=None, headers=None: {
            "status": "success",
            "data": {"product": CLEANSHELF_PRODUCT_API_ITEM},
        }
        try:
            result = self.scraper.parse_site(
                "https://cleanshelf.online/product/cassava-per-kg",
                CLEANSHELF_PRODUCT_HTML,
            )
        finally:
            self.scraper.fetch_json = original
        self.assertEqual(result["name"], "Cassava Per Kg")
        self.assertEqual(result["price"], 220.0)
        self.assertEqual(result["source"], "CleanShelf")
        self.assertEqual(result["category"], "Groceries")
        self.assertEqual(result["availability"], "in_stock")
        self.assertEqual(result["normalized_name"], "cassava per kg")

    def test_cleanshelf_html_fallback(self):
        original = self.scraper.fetch_json
        self.scraper.fetch_json = lambda url, timeout=None, headers=None: (_ for _ in ()).throw(RuntimeError("offline"))
        try:
            result = self.scraper.parse_site(
                "https://cleanshelf.online/product/cassava-per-kg",
                CLEANSHELF_PRODUCT_HTML,
            )
        finally:
            self.scraper.fetch_json = original
        self.assertEqual(result["name"], "Cassava Per Kg")
        self.assertEqual(result["price"], 220.0)
        self.assertEqual(result["source"], "CleanShelf")
        self.assertEqual(result["image_url"], "https://storage.chatcommerce.co.ke/Homechef/products/cassava.jpg")

    def test_cleanshelf_category_traversal_stops_on_duplicates(self):
        pages = {
            1: {
                "status": "success",
                "data": {"products": [CLEANSHELF_PRODUCT_API_ITEM], "total": 2, "page": 1, "limit": 1},
            },
            2: {
                "status": "success",
                "data": {"products": [CLEANSHELF_PRODUCT_API_ITEM], "total": 2, "page": 2, "limit": 1},
            },
        }
        products = fetch_cleanshelf_category_products(
            FakeCleanShelfScraper(pages),
            "groceries",
            limit=1,
        )
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["source"], "CleanShelf")

    def test_normalize_naivas_url(self):
        normalized = self.scraper._normalize_fetch_url(
            "https://naivas.online/brookside-fresh-milk-1l.html"
        )
        self.assertEqual(normalized, "https://www.naivas.online/brookside-fresh-milk-1l")

    def test_product_from_json_ld_basic(self):
        """JSON-LD product extraction works for basic case."""
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"Test Product","offers":{"price":"1500","priceCurrency":"KES"}}
        </script>
        """
        result = self.scraper._product_from_json_ld(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Product")
        self.assertEqual(result["price"], 1500.0)

    def test_product_from_json_ld_with_lowprice(self):
        """JSON-LD with AggregateOffer (lowPrice) should extract the low price."""
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"Test Multi Price","offers":{"@type":"AggregateOffer","lowPrice":"1450","highPrice":"1600","priceCurrency":"KES"}}
        </script>
        """
        result = self.scraper._product_from_json_ld(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Multi Price")
        self.assertEqual(result["price"], 1450.0)

    def test_product_from_json_ld_price_specification(self):
        """JSON-LD with priceSpecification should extract price."""
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"Spec Product","offers":{"priceSpecification":{"price":"2500","priceCurrency":"KES"}}}
        </script>
        """
        result = self.scraper._product_from_json_ld(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["price"], 2500.0)

    def test_product_from_json_ld_multiple_offers(self):
        """JSON-LD with multiple offers list should take first offer."""
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"Multi Offer","offers":[{"price":"100","priceCurrency":"KES"},{"price":"200","priceCurrency":"KES"}]}
        </script>
        """
        result = self.scraper._product_from_json_ld(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["price"], 100.0)

    def test_generic_price_from_html(self):
        """Generic price extraction from HTML with KES prefix."""
        html = "<html><body><h1>Test Item</h1><div class='price'>KES 2,500</div></body></html>"
        result = self.scraper._generic_price_from_html(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["price"], 2500.0)
        # Title should be extracted from h1
        self.assertEqual(result["title"], "Test Item")

    def test_generic_price_from_html_og_meta(self):
        """Generic price extraction via OG meta tags."""
        html = """
        <html><head>
        <meta property="og:title" content="OG Product" />
        <meta property="product:price:amount" content="999" />
        <meta property="product:price:currency" content="KES" />
        <meta property="og:image" content="https://example.test/product.jpg" />
        <meta property="product:category" content="Dairy" />
        </head><body></body></html>
        """
        result = self.scraper._generic_price_from_html(html)
        self.assertEqual(result["title"], "OG Product")
        self.assertEqual(result["price"], 999.0)
        self.assertEqual(result["currency"], "KES")
        self.assertEqual(result["image_url"], "https://example.test/product.jpg")
        self.assertEqual(result["category"], "Dairy")

    def test_parse_site_returns_stable_product_contract(self):
        """parse_site validates and enriches parser output without breaking title alias."""
        html = """
        <html><head>
        <meta property="og:title" content="Brookside Fresh Milk 1L" />
        <meta property="og:image" content="https://example.test/milk.jpg" />
        <meta property="product:category" content="Milk" />
        </head><body>
        <div class="text-xl mb-1">Brookside Fresh Milk 1L</div>
        <div class="product-price"><span>KES 135</span></div>
        <button>Add to cart</button>
        </body></html>
        """
        result = self.scraper.parse_site(
            "https://www.naivas.online/brookside-fresh-milk-1l",
            html,
        )
        self.assertEqual(result["name"], "Brookside Fresh Milk 1L")
        self.assertEqual(result["title"], "Brookside Fresh Milk 1L")
        self.assertEqual(result["source"], "Naivas")
        self.assertEqual(result["image_url"], "https://example.test/milk.jpg")
        self.assertEqual(result["category"], "Milk")
        self.assertEqual(result["availability"], "in_stock")
        self.assertEqual(result["normalized_name"], "brookside fresh milk 1l")

    def test_parse_site_contains_parser_errors(self):
        """Parser errors return a validated product-shaped payload."""
        original = self.scraper._generic_price_from_html
        self.scraper._generic_price_from_html = lambda html: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            result = self.scraper.parse_site("https://example.test/item", "<html></html>")
        finally:
            self.scraper._generic_price_from_html = original
        self.assertIsNone(result["price"])
        self.assertEqual(result["source"], "example.test")
        self.assertIn("boom", result["error"])

    def test_carrefour_json_ld_alternate_structure(self):
        """Carrefour JSON-LD with offers as list containing offer object."""
        html = """
        <script type="application/ld+json">
        {"@type":"Product","name":"Carrefour Item","offers":{"@type":"AggregateOffer","lowPrice":"890","priceCurrency":"KES","offerCount":1}}
        </script>
        """
        result = self.scraper._product_from_json_ld(html)
        self.assertIsNotNone(result)
        self.assertEqual(result["price"], 890.0)


if __name__ == "__main__":
    unittest.main()
