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
        
        # Group prices by supermarket, choosing the cheapest branch/channel price
        # for each product. Scraper imports may put online prices under "Website"
        # while seed/admin data may use a physical branch such as "Westlands".
        # The shopper-facing comparison is supermarket-level, so splitting these
        # channels would incorrectly show a supermarket as partial.
        supermarket_prices = {}
        for price_obj in prices:
            supermarket_id = price_obj.branch.supermarket_id
            if supermarket_id not in supermarket_prices:
                supermarket_prices[supermarket_id] = {
                    'supermarket': price_obj.branch.supermarket,
                    'prices': {}
                }
            current = supermarket_prices[supermarket_id]['prices'].get(price_obj.product_id)
            if current is None or price_obj.price < current['price']:
                supermarket_prices[supermarket_id]['prices'][price_obj.product_id] = {
                    'price': price_obj.price,
                    'branch': price_obj.branch,
                }

        comparison = []
        for supermarket_id, data in supermarket_prices.items():
            supermarket = data['supermarket']
            prices_dict = data['prices']
            
            total_cost = 0
            items_available = 0
            missing_items = []
            product_breakdown = []
            selected_branches = set()
            
            for item in basket_items:
                prod_id = item.product_id
                if prod_id in prices_dict:
                    selected_price = prices_dict[prod_id]
                    subtotal = selected_price['price'] * item.quantity
                    total_cost += subtotal
                    items_available += 1
                    selected_branches.add(selected_price['branch'].name)
                    product_breakdown.append({
                        'id': str(prod_id),
                        'name': item.product.name,
                        'quantity': item.quantity,
                        'unit_price': float(selected_price['price']),
                        'subtotal': float(subtotal),
                        'in_stock': True,
                    })
                else:
                    missing_items.append({
                        'id': str(prod_id),
                        'name': item.product.name
                    })
                    product_breakdown.append({
                        'id': str(prod_id),
                        'name': item.product.name,
                        'quantity': item.quantity,
                        'unit_price': None,
                        'subtotal': 0,
                        'in_stock': False,
                    })

            branch_name = (
                next(iter(selected_branches))
                if len(selected_branches) == 1
                else "Multiple branches"
            )
            
            comparison.append({
                'branch_id': str(supermarket_id),
                'branch_name': branch_name,
                'supermarket_name': supermarket.name,
                'logo_url': supermarket.logo_url,
                'total_cost': float(total_cost),
                'items_available': items_available,
                'total_items': basket_items.count(),
                'is_complete': items_available == basket_items.count(),
                'missing_items': missing_items,
                'product_breakdown': product_breakdown,
                'latitude': None,
                'longitude': None,
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
