from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import Product, ProductPrice
from .serializers import ProductSerializer, ProductPriceSerializer

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all().order_by('name')
        search = self.request.query_params.get('search')
        category = self.request.query_params.get('category')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(brand__icontains=search) | 
                Q(description__icontains=search)
            )
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
