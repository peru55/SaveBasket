from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Basket, BasketItem
from .serializers import BasketSerializer
from products.models import Product

class BasketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Basket.objects.all()
    serializer_class = BasketSerializer

    def get_queryset(self):
        # In a real app, filter by user: self.request.user.baskets.all()
        # For initial development and testing, show all baskets.
        return Basket.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        basket = self.get_object()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        basket_item, created = BasketItem.objects.get_or_create(
            basket=basket,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            basket_item.quantity += quantity
            basket_item.save()

        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        basket = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            basket_item = BasketItem.objects.get(basket=basket, product_id=product_id)
        except BasketItem.DoesNotExist:
            return Response({'error': 'Product is not in the basket'}, status=status.HTTP_404_NOT_FOUND)

        basket_item.delete()
        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def update_item_quantity(self, request, pk=None):
        basket = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        if not product_id or quantity is None:
            return Response({'error': 'product_id and quantity are required'}, status=status.HTTP_400_BAD_REQUEST)

        quantity = int(quantity)
        if quantity <= 0:
            BasketItem.objects.filter(basket=basket, product_id=product_id).delete()
        else:
            basket_item, created = BasketItem.objects.update_or_create(
                basket=basket,
                product_id=product_id,
                defaults={'quantity': quantity}
            )

        return Response(BasketSerializer(basket).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        basket = self.get_object()
        comparison = basket.compare_prices()
        return Response(comparison, status=status.HTTP_200_OK)
