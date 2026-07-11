from rest_framework import viewsets
from savebasket.permissions import IsAdminOrReadOnly
from .models import Supermarket, Branch
from .serializers import SupermarketSerializer, BranchSerializer

class SupermarketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = Supermarket.objects.all().order_name() if hasattr(Supermarket.objects.all(), 'order_name') else Supermarket.objects.all()
    serializer_class = SupermarketSerializer

    def get_queryset(self):
        # Allow alphabetical ordering
        return Supermarket.objects.all().order_by('name')

class BranchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

    def get_queryset(self):
        queryset = Branch.objects.all().select_related('supermarket').order_by('name')
        supermarket_id = self.request.query_params.get('supermarket_id')
        city = self.request.query_params.get('city')
        
        if supermarket_id:
            queryset = queryset.filter(supermarket_id=supermarket_id)
        if city:
            queryset = queryset.filter(city__iexact=city)
            
        return queryset
