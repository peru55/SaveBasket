import uuid
from django.db import models
from django.utils import timezone
from supermarkets.models import Branch

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    # Normalized name used for cross-supermarket matching and fast lookup.
    normalized_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    sku = models.CharField(max_length=100, blank=True, null=True, unique=True)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    canonical_category = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    variant = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    identity_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    brand = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    size = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Avoid importing heavy modules at top-level to keep model import fast.
        try:
            from .utils import normalize_name
        except Exception:
            normalize_name = None
        try:
            from .match_service import ProductMatchService
        except Exception:
            ProductMatchService = None

        if normalize_name and self.name and not self.normalized_name:
            self.normalized_name = normalize_name(self.name)
        if ProductMatchService and self.normalized_name:
            if not self.canonical_category:
                self.canonical_category = ProductMatchService.extract_canonical_category(self.normalized_name)
            if not self.variant:
                self.variant = ProductMatchService.extract_variant(self.normalized_name)
            if not self.identity_key:
                self.identity_key = ProductMatchService.identity_key(
                    self.brand,
                    self.canonical_category,
                    self.variant,
                    self.size,
                    self.unit,
                )

        super().save(*args, **kwargs)

class StoreProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='store_products')
    store_name = models.CharField(max_length=100)
    store_product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_url = models.URLField(max_length=500, blank=True, null=True)
    scraped_image_url = models.URLField(max_length=500, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'store_name')
        indexes = [
            models.Index(fields=['store_name']),
        ]

    def __str__(self):
        return f"{self.store_product_name} at {self.store_name} (KSh {self.price})"


class ProductAlias(models.Model):
    class Source(models.TextChoices):
        REVIEWED = "reviewed", "Reviewed"
        IMPORTED = "imported", "Imported"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="aliases")
    raw_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True)
    store_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.IMPORTED)
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ["normalized_name", "store_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_name", "store_name"],
                name="unique_product_alias_name_store",
            )
        ]
        indexes = [
            models.Index(fields=["normalized_name", "store_name"]),
        ]

    def __str__(self):
        store = f" ({self.store_name})" if self.store_name else ""
        return f"{self.raw_name}{store} -> {self.product.name}"


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


class RawScrapedProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_name = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    product_url = models.URLField(max_length=500, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scraped_at']

    def __str__(self):
        return f"{self.product_name} from {self.store_name} ({'Processed' if self.processed else 'Pending'})"


class ProductImportReview(models.Model):
    class IssueType(models.TextChoices):
        POSSIBLE_DUPLICATE = "possible_duplicate", "Possible duplicate"
        LOW_CONFIDENCE_MATCH = "low_confidence_match", "Low-confidence match"
        AMBIGUOUS_VARIANT = "ambiguous_variant", "Ambiguous variant"
        MISSING_VARIANT = "missing_variant", "Missing variant"
        POSSIBLE_WRONG_PRICE_FROM_LISTING = "possible_wrong_price_from_listing", "Possible wrong price from listing"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWED = "reviewed", "Reviewed"
        IGNORED = "ignored", "Ignored"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue_type = models.CharField(max_length=40, choices=IssueType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    raw_product = models.ForeignKey(
        RawScrapedProduct,
        on_delete=models.CASCADE,
        related_name="import_reviews",
    )
    matched_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="import_match_reviews",
        help_text="Product that the import linked to, when a match was accepted.",
    )
    candidate_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="import_candidate_reviews",
        help_text="Existing product that may be a duplicate or needs admin review.",
    )
    store_name = models.CharField(max_length=100, db_index=True)
    scraped_product_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    brand = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    score = models.FloatField(default=0.0)
    reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "issue_type"]),
            models.Index(fields=["store_name", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["raw_product", "issue_type", "candidate_product"],
                name="unique_product_import_review_candidate",
            )
        ]

    def __str__(self):
        return f"{self.get_issue_type_display()}: {self.scraped_product_name} ({self.store_name})"


class IngestionHistory(models.Model):
    """Record of a scraper ingestion run pushed to the backend.

    Stores metadata about the run plus the raw payload for auditing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    supermarket = models.ForeignKey(
        'supermarkets.Supermarket', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    branch = models.ForeignKey(
        'supermarkets.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    source_name = models.CharField(max_length=200, blank=True, null=True, db_index=True)
    job_name = models.CharField(max_length=100, blank=True, null=True)
    urls = models.TextField(blank=True, null=True, help_text='Optional newline-separated URLs processed')
    products_processed = models.IntegerField(default=0)
    created_products = models.IntegerField(default=0)
    created_prices = models.IntegerField(default=0)
    updated_prices = models.IntegerField(default=0)
    success = models.BooleanField(default=False)
    error_text = models.TextField(blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    run_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ingest {self.source_name or 'unknown'} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    def payload_pretty(self):
        try:
            import json
            return json.dumps(self.payload, indent=2, ensure_ascii=False)
        except Exception:
            return str(self.payload)
