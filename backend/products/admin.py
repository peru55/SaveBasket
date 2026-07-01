from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from .models import IngestionHistory, Product, ProductAlias, ProductImportReview, StoreProduct
from .review_actions import accept_import_review, ignore_import_review
from django.utils.html import format_html


class StoreProductInline(admin.TabularInline):
	model = StoreProduct
	extra = 0
	readonly_fields = ('last_updated',)


class ProductAliasInline(admin.TabularInline):
	model = ProductAlias
	extra = 0
	readonly_fields = ('created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('name', 'brand', 'canonical_category', 'size', 'unit', 'identity_key', 'store_count', 'updated_at')
	list_filter = ('brand', 'canonical_category', 'unit', 'created_at')
	search_fields = ('name', 'normalized_name', 'identity_key', 'brand', 'store_products__store_name', 'aliases__raw_name')
	readonly_fields = ('id', 'created_at', 'updated_at')
	inlines = (StoreProductInline, ProductAliasInline)
	ordering = ('name',)

	def store_count(self, obj):
		return obj.store_products.count()


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
	list_display = ('store_name', 'store_product_name', 'product', 'price', 'last_updated')
	list_filter = ('store_name', 'last_updated')
	search_fields = ('store_name', 'store_product_name', 'product__name', 'product__normalized_name')
	readonly_fields = ('id', 'last_updated')


@admin.register(ProductAlias)
class ProductAliasAdmin(admin.ModelAdmin):
	list_display = ('raw_name', 'store_name', 'product', 'source', 'confidence', 'created_at')
	list_filter = ('source', 'store_name', 'created_at')
	search_fields = ('raw_name', 'normalized_name', 'store_name', 'product__name', 'product__identity_key')
	readonly_fields = ('id', 'created_at')


@admin.register(IngestionHistory)
class IngestionHistoryAdmin(admin.ModelAdmin):
	list_display = (
		'created_at', 'source_name', 'supermarket', 'branch', 'products_processed',
		'created_products', 'created_prices', 'updated_prices', 'success'
	)
	list_filter = ('success', 'supermarket', 'created_at')
	search_fields = ('source_name', 'supermarket__name', 'branch__name')
	readonly_fields = ('created_at', 'payload_pretty', 'error_text', 'run_by')
	ordering = ('-created_at',)

	fieldsets = (
		(None, {
			'fields': ('created_at', 'source_name', 'supermarket', 'branch', 'job_name', 'urls', 'run_by')
		}),
		('Counts', {
			'fields': ('products_processed', 'created_products', 'created_prices', 'updated_prices', 'success')
		}),
		('Payload & Errors', {
			'fields': ('payload_pretty', 'error_text'),
		}),
	)

	def payload_pretty(self, obj):
		payload = getattr(obj, 'payload', None)
		if not payload:
			return ''
		import json
		pretty = json.dumps(payload, indent=2, ensure_ascii=False)
		return format_html('<pre style="white-space:pre-wrap;">{}</pre>', pretty)

	payload_pretty.short_description = 'Payload (JSON)'


@admin.register(ProductImportReview)
class ProductImportReviewAdmin(admin.ModelAdmin):
	list_display = (
		'created_at', 'issue_type', 'status', 'store_name', 'scraped_product_name',
		'score', 'matched_product_link', 'candidate_product_link'
	)
	list_filter = ('status', 'issue_type', 'store_name', 'created_at')
	search_fields = (
		'scraped_product_name', 'normalized_name', 'brand', 'store_name',
		'matched_product__name', 'candidate_product__name'
	)
	readonly_fields = (
		'created_at', 'raw_product', 'issue_type', 'store_name', 'scraped_product_name',
		'normalized_name', 'brand', 'size', 'unit', 'score', 'reason',
		'matched_product', 'candidate_product'
	)
	actions = ('accept_as_alias', 'reject_keep_separate', 'mark_reviewed', 'mark_ignored', 'reopen')
	ordering = ('-created_at',)

	fieldsets = (
		('Review', {
			'fields': ('status', 'admin_notes', 'reviewed_at')
		}),
		('Import Signal', {
			'fields': (
				'issue_type', 'score', 'reason', 'raw_product', 'store_name',
				'scraped_product_name', 'normalized_name', 'brand', 'size', 'unit'
			)
		}),
		('Products', {
			'fields': ('matched_product', 'candidate_product')
		}),
		('Timestamps', {
			'fields': ('created_at',)
		}),
	)

	def _product_link(self, product):
		if not product:
			return '-'
		return format_html(
			'<a href="/admin/products/product/{}/change/">{}</a>',
			product.id,
			product.name,
		)

	def matched_product_link(self, obj):
		return self._product_link(obj.matched_product)

	def candidate_product_link(self, obj):
		return self._product_link(obj.candidate_product)

	def mark_reviewed(self, request, queryset):
		queryset.update(status=ProductImportReview.Status.REVIEWED, reviewed_at=timezone.now())

	def mark_ignored(self, request, queryset):
		queryset.update(status=ProductImportReview.Status.IGNORED, reviewed_at=timezone.now())

	def reopen(self, request, queryset):
		queryset.update(status=ProductImportReview.Status.OPEN, reviewed_at=None)

	def accept_as_alias(self, request, queryset):
		accepted = 0
		skipped = 0
		for review in queryset.select_related('raw_product', 'matched_product', 'candidate_product'):
			result = accept_import_review(review, request.user)
			if result.get('accepted'):
				accepted += 1
			else:
				skipped += 1
		if accepted:
			self.message_user(
				request,
				f"Accepted {accepted} review(s): aliases created and matching store/price rows relinked.",
				messages.SUCCESS,
			)
		if skipped:
			self.message_user(
				request,
				f"Skipped {skipped} review(s) because no target product was available.",
				messages.WARNING,
			)

	def reject_keep_separate(self, request, queryset):
		for review in queryset:
			ignore_import_review(review, request.user)
		self.message_user(
			request,
			f"Rejected {queryset.count()} review(s); products were left separate.",
			messages.SUCCESS,
		)

	matched_product_link.short_description = 'Matched product'
	candidate_product_link.short_description = 'Candidate product'
	accept_as_alias.short_description = 'Accept: create reviewed alias and merge into candidate'
	reject_keep_separate.short_description = 'Reject: keep products separate'
	mark_reviewed.short_description = 'Mark selected reviews as reviewed'
	mark_ignored.short_description = 'Mark selected reviews as ignored'
	reopen.short_description = 'Reopen selected reviews'
