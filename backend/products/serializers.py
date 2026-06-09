"""
products/serializers.py
-----------------------
Serializers for the `products` app.

This file converts Product and ProductPrice model instances to/from JSON so
the Flutter app (and any other API clients) can read and write product data.

Models handled:
  • Product      – a grocery item catalogued in the system (e.g. "Brookside Fresh Milk 1L")
  • ProductPrice – the price of a specific Product at a specific Branch,
                   updated whenever our scrapers or admin staff refreshes prices
"""

from rest_framework import serializers
from .models import Product, ProductPrice
from supermarkets.serializers import BranchSerializer  # Reuse branch serializer for nesting
from supermarkets.models import Branch


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializes the Product model.

    A Product represents a grocery item that exists independently of any store –
    it has a name, category, brand, barcode, and optional image. Prices are stored
    separately in ProductPrice so the same product can have different prices at
    different supermarket branches.

    Fields exposed:
      - id          : UUID primary key
      - name        : Full product name (e.g. "Jogoo Maize Meal 2kg")
      - sku         : Stock Keeping Unit – internal identifier used by retailers
      - barcode     : Product barcode (EAN/UPC) – useful for scanning
      - category    : Grouping label (e.g. "Dairy", "Bakery", "Pantry")
      - brand       : Manufacturer/brand name (e.g. "Brookside")
      - image_url   : URL to a product thumbnail image
      - description : Free-text product description

    This serializer is also reused as a nested object inside ProductPriceSerializer
    and BasketItemSerializer so product details are always embedded in price and
    basket responses.
    """

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'barcode', 'category', 'brand', 'image_url', 'description']


class ProductPriceSerializer(serializers.ModelSerializer):
    """
    Serializes the ProductPrice model.

    A ProductPrice ties together a Product, a Branch, and a decimal price. It is
    the core data point that SaveBasket uses to compare how much each supermarket
    charges for the same item.

    Like BranchSerializer, this uses the dual read/write field pattern:

      product (read):
        A nested ProductSerializer object embedded in GET responses so the client
        receives the full product details alongside the price, for example:
            "product": { "id": "...", "name": "Kabras Sugar 1kg", ... }

      product_id (write):
        A PrimaryKeyRelatedField for POST/PUT/PATCH requests. The client sends
        only the product's UUID. DRF resolves it to the Product instance via
        source='product'. Marked write_only=True so it is invisible in GET responses.

      branch (read):
        A nested BranchSerializer (which itself nests SupermarketSerializer) so the
        full branch + supermarket context is always present when reading a price.

      branch_id (write):
        The Branch UUID used when creating or updating a price record.

    Additional fields:
      - price       : Decimal price in Kenyan Shillings (KSh)
      - updated_at  : Timestamp automatically set when the record is saved – shows
                      how fresh the price data is
      - source_url  : The web page URL where this price was scraped from (optional),
                      useful for auditing and re-scraping
    """

    # Nested read: full product object embedded in the response
    product = ProductSerializer(read_only=True)

    # Flat write: accept just a product UUID when creating/updating a price
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',   # Maps to the 'product' foreign key on ProductPrice
        write_only=True     # Only used in write operations, hidden from GET responses
    )

    # Nested read: full branch (+ supermarket) object embedded in the response
    branch = BranchSerializer(read_only=True)

    # Flat write: accept just a branch UUID when creating/updating a price
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        source='branch',    # Maps to the 'branch' foreign key on ProductPrice
        write_only=True     # Only used in write operations, hidden from GET responses
    )

    class Meta:
        model = ProductPrice
        fields = ['id', 'product', 'product_id', 'branch', 'branch_id', 'price', 'updated_at', 'source_url']
