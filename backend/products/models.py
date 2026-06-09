import uuid
from django.db import models
from supermarkets.models import Branch

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True, null=True, unique=True)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ProductPrice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    source_url = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        unique_together = ('product', 'branch')
        ordering = ['price']

    def __str__(self):
        return f"{self.product.name} at {self.branch}: KSh {self.price}"
