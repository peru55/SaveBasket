"""
supermarkets/serializers.py
---------------------------
Serializers for the `supermarkets` app.

Django REST Framework (DRF) serializers work like a two-way translator between
Python model instances and data formats like JSON:

  - READING  (serialization):   Model instance  →  Python dict  →  JSON response
  - WRITING  (deserialization): JSON request    →  Python dict  →  Model instance

The serializers here handle two models:
  • Supermarket  – a retail chain (e.g. "Carrefour", "Naivas")
  • Branch       – a physical store belonging to a Supermarket (e.g. "Carrefour Sarit Centre")
"""

from rest_framework import serializers
from .models import Supermarket, Branch


class SupermarketSerializer(serializers.ModelSerializer):
    """
    Serializes the Supermarket model.

    Exposes three fields in the JSON response:
      - id       : UUID primary key (auto-generated, read-only)
      - name     : Display name of the supermarket chain (e.g. "Naivas")
      - logo_url : Optional URL pointing to the supermarket's logo image

    Used as a nested (embedded) serializer inside BranchSerializer so that
    whenever a branch is returned, the full supermarket details are included
    in the same JSON object instead of just a raw UUID.
    """

    class Meta:
        model = Supermarket
        fields = ['id', 'name', 'logo_url']


class BranchSerializer(serializers.ModelSerializer):
    """
    Serializes the Branch model.

    A branch is a specific physical location belonging to a supermarket chain.

    Two separate fields handle the supermarket relationship:

      supermarket (read):
        A nested SupermarketSerializer object. When reading a branch from the API
        (GET request), the full supermarket JSON object is embedded here, e.g.:
            "supermarket": { "id": "...", "name": "Naivas", "logo_url": "..." }

      supermarket_id (write):
        A PrimaryKeyRelatedField used only when creating or updating a branch
        (POST/PUT/PATCH request). The client sends just the UUID of the supermarket,
        and DRF maps it to the correct Supermarket instance via source='supermarket'.
        It is marked write_only=True so it never appears in GET responses.

    This read/write split is a common DRF pattern that keeps GET responses rich
    with nested data while keeping write requests simple (just an ID).

    Additional fields exposed:
      - name      : Branch location label (e.g. "Westlands")
      - latitude  : GPS latitude (optional) – for map integrations
      - longitude : GPS longitude (optional) – for map integrations
      - city      : City the branch is in (defaults to "Nairobi")
      - address   : Full street address (optional)
    """

    # Nested read: returns the full Supermarket JSON when reading a branch
    supermarket = SupermarketSerializer(read_only=True)

    # Flat write: accepts a Supermarket UUID when creating/updating a branch
    supermarket_id = serializers.PrimaryKeyRelatedField(
        queryset=Supermarket.objects.all(),
        source='supermarket',   # Maps this field to the 'supermarket' model attribute
        write_only=True         # Hidden from GET responses; only used in POST/PUT/PATCH
    )

    class Meta:
        model = Branch
        fields = ['id', 'supermarket', 'supermarket_id', 'name', 'latitude', 'longitude', 'city', 'address']
