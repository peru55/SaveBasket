"""
baskets/serializers.py
----------------------
Serializers for the `baskets` app.

A Basket is a user's shopping list – a named collection of BasketItems. Each
BasketItem links a Product to a Basket with a quantity. These serializers
convert those models to/from JSON so the Flutter app can:
  • Create and retrieve baskets
  • Add, update, and remove items
  • Trigger the price comparison endpoint (see baskets/views.py → compare action)

Models handled:
  • BasketItem – one line in a shopping list: which product and how many
  • Basket     – the overall shopping list container (name, owner, list of items)
"""

from rest_framework import serializers
from .models import Basket, BasketItem
from products.serializers import ProductSerializer  # Reuse to embed full product details
from products.models import Product


class BasketItemSerializer(serializers.ModelSerializer):
    """
    Serializes the BasketItem model – a single line in a shopping basket.

    Uses the same dual read/write field pattern as BranchSerializer and
    ProductPriceSerializer:

      product (read):
        A nested ProductSerializer embedded in GET responses. Instead of returning
        just a product UUID, the full product object is included so the Flutter app
        has everything it needs to display the item (name, brand, image, etc.):
            "product": { "id": "...", "name": "Brookside Fresh Milk 1L", ... }

      product_id (write):
        A PrimaryKeyRelatedField used when adding an item to a basket via the
        add_item action (POST). The client sends only the product UUID, and DRF
        resolves it to the correct Product instance through source='product'.
        It is write_only=True so it is never returned in GET responses.

    Additional fields:
      - id       : UUID of this basket item record
      - quantity : How many units of the product are in the basket (default 1)
    """

    # Nested read: embed full product details when returning basket items
    product = ProductSerializer(read_only=True)

    # Flat write: accept a product UUID when adding items to the basket
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'    # Maps the incoming UUID to the 'product' FK on BasketItem
    )

    class Meta:
        model = BasketItem
        fields = ['id', 'product', 'product_id', 'quantity']


class BasketSerializer(serializers.ModelSerializer):
    """
    Serializes the Basket model – the top-level shopping list container.

    Fields exposed:
      - id         : UUID primary key of the basket
      - user       : The Django User who owns this basket. Read-only – it is set
                     automatically from the authenticated request in the view, so
                     clients never need to send it.
      - name       : A friendly label for the basket (e.g. "Weekly Groceries")
      - items      : A list of nested BasketItem objects (read-only). Every GET
                     response for a basket includes the full item list with embedded
                     product details, for example:
                         "items": [
                           { "id": "...", "product": { "name": "Milk", ... }, "quantity": 2 },
                           { "id": "...", "product": { "name": "Sugar", ... }, "quantity": 1 }
                         ]
      - created_at : Timestamp when the basket was first created. Read-only –
                     set automatically by the database.

    The `items` field is read_only=True because items are managed through dedicated
    actions on the BasketViewSet (add_item, remove_item, update_item_quantity)
    rather than through the basket serializer itself.
    """

    # Nested read: embed all basket items (with full product data) on every basket response
    items = BasketItemSerializer(many=True, read_only=True)

    class Meta:
        model = Basket
        fields = ['id', 'user', 'name', 'items', 'created_at']
        # user and created_at are set server-side; clients must not send them
        read_only_fields = ['user', 'created_at']
