import uuid
from django.db import models
from django.contrib.auth.models import User
from products.models import Product, ProductPrice
from supermarkets.models import Branch

class Basket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='baskets', blank=True, null=True)
    name = models.CharField(max_length=100, default='My Basket')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.items.count()} items)"

    def compare_prices(self):
        """
        Compares the total cost of this basket across all supermarket branches.
        Returns a sorted list of branches with total costs and coverage metrics.
        """
        basket_items = self.items.all()
        if not basket_items.exists():
            return []

        # Get all product IDs in this basket
        product_ids = [item.product_id for item in basket_items]
        
        # Fetch all prices for these products
        prices = ProductPrice.objects.filter(product_id__in=product_ids).select_related('branch', 'branch__supermarket')
        
        # Group prices by branch
        branch_prices = {}
        for price_obj in prices:
            branch_id = price_obj.branch_id
            if branch_id not in branch_prices:
                branch_prices[branch_id] = {
                    'branch': price_obj.branch,
                    'prices': {}
                }
            branch_prices[branch_id]['prices'][price_obj.product_id] = price_obj.price

        comparison = []
        for branch_id, data in branch_prices.items():
            branch = data['branch']
            prices_dict = data['prices']
            
            total_cost = 0
            items_available = 0
            missing_items = []
            
            for item in basket_items:
                prod_id = item.product_id
                if prod_id in prices_dict:
                    total_cost += prices_dict[prod_id] * item.quantity
                    items_available += 1
                else:
                    missing_items.append({
                        'id': str(prod_id),
                        'name': item.product.name
                    })
            
            comparison.append({
                'branch_id': str(branch.id),
                'branch_name': branch.name,
                'supermarket_name': branch.supermarket.name,
                'logo_url': branch.supermarket.logo_url,
                'total_cost': float(total_cost),
                'items_available': items_available,
                'total_items': basket_items.count(),
                'is_complete': items_available == basket_items.count(),
                'missing_items': missing_items,
                'latitude': float(branch.latitude) if branch.latitude else None,
                'longitude': float(branch.longitude) if branch.longitude else None,
            })
            
        # Sort comparison by total cost (ascending), with completed baskets prioritized
        # If two branches have the same cost, sort by completeness (more items available first)
        comparison.sort(key=lambda x: (not x['is_complete'], x['total_cost'] if x['items_available'] > 0 else float('inf')))
        return comparison

class BasketItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='basket_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('basket', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.basket.name}"
