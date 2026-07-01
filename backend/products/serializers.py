from rest_framework import serializers
from .models import Product, ProductPrice, StoreProduct
from supermarkets.serializers import BranchSerializer
from supermarkets.models import Branch
from urllib.parse import quote


class StorePriceSerializer(serializers.ModelSerializer):
    store = serializers.CharField(source='store_name')
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    scraped_image_url = serializers.SerializerMethodField()

    def get_scraped_image_url(self, obj):
        return proxied_image_url(self.context.get('request'), obj.scraped_image_url)

    class Meta:
        model = StoreProduct
        fields = ['store', 'price', 'product_url', 'scraped_image_url']


class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    stores = StorePriceSerializer(source='store_products', many=True, read_only=True)

    def get_image_url(self, obj):
        image_url = obj.image_url
        if not image_url:
            store_products = list(obj.store_products.all())
            context_store = self.context.get('store_name')
            store_product = None
            if context_store:
                store_product = next(
                    (
                        sp for sp in store_products
                        if sp.scraped_image_url and sp.store_name.lower() == context_store.lower()
                    ),
                    None,
                )
            store_product = store_product or next(
                (sp for sp in store_products if sp.scraped_image_url),
                None,
            )
            image_url = store_product.scraped_image_url if store_product else None
        return proxied_image_url(self.context.get('request'), image_url)

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'barcode', 'category', 'brand', 'variant', 'size', 'unit', 'image_url', 'description', 'stores']


class ProductPriceSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    branch = BranchSerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        source='branch',
        write_only=True
    )

    class Meta:
        model = ProductPrice
        fields = ['id', 'product', 'product_id', 'branch', 'branch_id', 'price', 'updated_at', 'source_url']


def proxied_image_url(request, image_url):
    if not image_url:
        return None
    if image_url.startswith('/api/products/image-proxy/'):
        return image_url
    if request is None:
        return image_url
    return request.build_absolute_uri(f"/api/products/image-proxy/?url={quote(image_url, safe='')}")
