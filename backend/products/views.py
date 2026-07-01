from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from urllib.parse import urlparse
import requests

from .models import Product, ProductPrice, IngestionHistory, RawScrapedProduct
from .serializers import ProductSerializer, ProductPriceSerializer
from supermarkets.models import Supermarket, Branch
from .match_service import ProductMatchService
import traceback

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all().prefetch_related('store_products').order_by('name')
        search = self.request.query_params.get('search')
        category = self.request.query_params.get('category')
        
        if search:
            norm_search = ProductMatchService.normalize_name(search)
            query = Q(name__icontains=search) | Q(brand__icontains=search) | Q(description__icontains=search)
            if norm_search:
                query |= Q(normalized_name__icontains=norm_search)
            queryset = queryset.filter(query)
        if category:
            queryset = queryset.filter(category__iexact=category)
            
        return queryset

class ProductPriceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer

    def get_queryset(self):
        queryset = ProductPrice.objects.all().select_related('product', 'branch', 'branch__supermarket')
        product_id = self.request.query_params.get('product_id')
        branch_id = self.request.query_params.get('branch_id')
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
            
        return queryset


class ProductImageProxyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        image_url = request.query_params.get("url")
        if not image_url:
            return Response({"detail": "Missing image url"}, status=status.HTTP_400_BAD_REQUEST)

        parsed = urlparse(image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return Response({"detail": "Invalid image url"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = requests.get(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Referer": f"{parsed.scheme}://{parsed.netloc}/",
                },
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return Response(
                {"detail": "Could not fetch image", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not content_type.startswith("image/"):
            return Response({"detail": "URL did not return an image"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        proxied = HttpResponse(response.content, content_type=content_type)
        proxied["Cache-Control"] = "public, max-age=86400"
        return proxied


class ScraperIngestView(APIView):
    permission_classes = [permissions.AllowAny]

    def _payload_parts(self, payload, request):
        if isinstance(payload, list):
            return payload, request.query_params.get("source") or "Unknown", None
        return (
            payload.get("products") or [],
            payload.get("source") or payload.get("supermarket") or payload.get("domain") or "Unknown",
            payload.get("branch"),
        )

    def _get_branch(self, supermarket, branch_obj):
        branch_name = branch_obj.get("name") if isinstance(branch_obj, dict) else branch_obj
        branch_name = branch_name or "Website"
        branch = Branch.objects.filter(supermarket=supermarket, name__iexact=branch_name).first()
        if branch:
            return branch
        city = branch_obj.get("city") if isinstance(branch_obj, dict) else "Nairobi"
        return Branch.objects.create(supermarket=supermarket, name=branch_name, city=city)

    def _payload_urls(self, products):
        try:
            urls = [p.get('url') for p in products if isinstance(p, dict) and p.get('url')]
            return "\n".join(urls) if urls else None
        except Exception:
            return None

    def post(self, request, *args, **kwargs):
        api_key = getattr(settings, "SCRAPER_API_KEY", None)
        if api_key:
            header = request.headers.get("X-SCRAPER-KEY") or request.META.get("HTTP_X_SCRAPER_KEY")
            if header != api_key:
                return Response({"detail": "Invalid API key"}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        products, supermarket_name, branch_obj = self._payload_parts(payload, request)

        if not products:
            return Response({"detail": "No products provided"}, status=status.HTTP_400_BAD_REQUEST)

        sm = Supermarket.objects.filter(name__iexact=supermarket_name).first()
        if not sm:
            sm = Supermarket.objects.create(name=supermarket_name)

        branch = self._get_branch(sm, branch_obj)

        history = IngestionHistory.objects.create(
            supermarket=sm,
            branch=branch,
            source_name=str(supermarket_name)[:200] if supermarket_name else None,
            urls=self._payload_urls(products),
            products_processed=len(products),
            success=False,
            payload=payload if isinstance(payload, dict) else None,
            run_by=(request.user if getattr(request, 'user', None) and request.user.is_authenticated else None),
        )

        created_products = 0
        created_prices = 0
        updated_prices = 0

        try:
            with transaction.atomic():
                for raw in products:
                    name = (raw.get("name") or raw.get("title") or "").strip()
                    price = raw.get("price")
                    image = raw.get("image_url") or raw.get("image")
                    source_url = raw.get("url") or raw.get("source_url")
                    
                    raw_scraped = RawScrapedProduct.objects.create(
                        store_name=supermarket_name,
                        product_name=name,
                        price=price,
                        product_url=source_url,
                        image_url=image
                    )
                    
                    product, created, price_created = ProductMatchService.process_raw_product(raw_scraped, branch=branch)
                    
                    if created:
                        created_products += 1
                        
                    if price is not None:
                        if price_created:
                            created_prices += 1
                        else:
                            updated_prices += 1

            history.created_products = created_products
            history.created_prices = created_prices
            history.updated_prices = updated_prices
            history.success = True
            history.save()

            return Response({"created_products": created_products, "created_prices": created_prices, "updated_prices": updated_prices})
        except Exception as exc:
            tb = traceback.format_exc()
            history.error_text = f"{str(exc)}\n\n{tb}"
            history.success = False
            history.save()
            return Response({"detail": "Ingestion failed", "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
