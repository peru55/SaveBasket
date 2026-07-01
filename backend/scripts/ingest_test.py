import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'savebasket.settings')
django.setup()

from supermarkets.models import Supermarket, Branch
from products.services import get_or_create_product
from products.models import ProductPrice

# test_payload.json lives at the workspace root `Scrapper/`, not under backend/
payload_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Scrapper', 'test_payload.json')
payload_path = os.path.abspath(payload_path)
with open(payload_path, 'r', encoding='utf-8') as fh:
    payload = json.load(fh)

products = payload.get('products') or []
source = payload.get('source') or 'Unknown'
branch_obj = payload.get('branch')

# Find-or-create supermarket
sm = Supermarket.objects.filter(name__iexact=source).first()
if not sm:
    sm = Supermarket.objects.create(name=source)

# Determine branch
branch_name = None
if isinstance(branch_obj, dict):
    branch_name = branch_obj.get('name')
elif isinstance(branch_obj, str):
    branch_name = branch_obj
branch_name = branch_name or 'Website'

branch = Branch.objects.filter(supermarket=sm, name__iexact=branch_name).first()
if not branch:
    branch = Branch.objects.create(supermarket=sm, name=branch_name, city=(branch_obj.get('city') if isinstance(branch_obj, dict) else 'Nairobi'))

created_products = 0
created_prices = 0
updated_prices = 0

for raw in products:
    product, created = get_or_create_product(raw)
    if created:
        created_products += 1

    price = raw.get('price')
    if price is None:
        continue

    source_url = raw.get('url') or raw.get('source_url')
    pp, created_flag = ProductPrice.objects.update_or_create(product=product, branch=branch, defaults={'price': price, 'source_url': source_url})
    if created_flag:
        created_prices += 1
    else:
        updated_prices += 1

print('created_products:', created_products)
print('created_prices:', created_prices)
print('updated_prices:', updated_prices)
