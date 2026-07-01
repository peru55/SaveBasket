from django.core.management.base import BaseCommand
from decimal import Decimal
from django.conf import settings

"""
Development-only seeder for SaveBasket.

This command is intentionally guarded: it must be run with `--dev` and
`settings.DEBUG` must be True. This prevents accidental seeding in production.

Usage:
    python manage.py seed_data --dev
"""

from supermarkets.models import Supermarket, Branch
from products.models import Product, ProductPrice


class Command(BaseCommand):
    help = "Seeds the database with initial Kenyan supermarkets, products, and prices for testing. Requires --dev and DEBUG=True."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dev', action='store_true', help='Allow seeding in development (required).'
        )

    def handle(self, *args, **options):
        if not options.get('dev'):
            self.stdout.write(self.style.ERROR('This command is guarded. Pass --dev to run (development only).'))
            return

        if not getattr(settings, 'DEBUG', False):
            self.stdout.write(self.style.ERROR('Refusing to run seed_data because settings.DEBUG is False. Only run in development with --dev.'))
            return

        self.stdout.write('Seeding database (development mode)...')

        # 1. Clear existing data to avoid duplicates
        ProductPrice.objects.all().delete()
        Product.objects.all().delete()
        Branch.objects.all().delete()
        Supermarket.objects.all().delete()

        # 2. Create Supermarkets
        carrefour = Supermarket.objects.create(
            name="Carrefour",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Carrefour_logo.svg/1200px-Carrefour_logo.svg.png",
        )
        naivas = Supermarket.objects.create(
            name="Naivas",
            logo_url="https://naivas.online/media/logo/stores/1/Naivas-Logo-Icon.png",
        )
        quickmart = Supermarket.objects.create(
            name="Quickmart",
            logo_url="https://quickmart.co.ke/wp-content/uploads/2021/04/quickmart-logo.png",
        )

        # 3. Create Branches
        cf_sarit = Branch.objects.create(
            supermarket=carrefour,
            name="Sarit Centre",
            latitude=Decimal("-1.2588"),
            longitude=Decimal("36.8028"),
            city="Nairobi",
            address="Sarit Centre Mall, Westlands",
        )
        cf_junction = Branch.objects.create(
            supermarket=carrefour,
            name="Junction Mall",
            latitude=Decimal("-1.3005"),
            longitude=Decimal("36.7618"),
            city="Nairobi",
            address="Junction Mall, Ngong Road",
        )

        nv_westlands = Branch.objects.create(
            supermarket=naivas,
            name="Westlands",
            latitude=Decimal("-1.2612"),
            longitude=Decimal("36.8042"),
            city="Nairobi",
            address="Westlands Commercial Centre",
        )
        nv_kilimani = Branch.objects.create(
            supermarket=naivas,
            name="Kilimani",
            latitude=Decimal("-1.2915"),
            longitude=Decimal("36.7885"),
            city="Nairobi",
            address="Lenana Road",
        )

        qm_lavington = Branch.objects.create(
            supermarket=quickmart,
            name="Lavington",
            latitude=Decimal("-1.2828"),
            longitude=Decimal("36.7725"),
            city="Nairobi",
            address="Lavington Mall, James Gichuru Rd",
        )

        # 4. Create Products
        milk = Product.objects.create(
            name="Brookside Fresh Milk 1L",
            sku="BROOK-MILK-1L",
            barcode="6001234567890",
            category="Dairy",
            brand="Brookside",
            description="Fresh cow milk, pasteurized and homogenized.",
            image_url="https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&auto=format&fit=crop&q=60",
        )
        sugar = Product.objects.create(
            name="Kabras Sugar 1kg",
            sku="KABRAS-SUGAR-1KG",
            barcode="6001234567891",
            category="Pantry",
            brand="Kabras",
            description="Pure white cane sugar locally milled.",
            image_url="https://images.unsplash.com/photo-1581798459219-318e76aecc7b?w=200&auto=format&fit=crop&q=60",
        )
        maize = Product.objects.create(
            name="Jogoo Maize Meal 2kg",
            sku="JOGOO-MAIZE-2KG",
            barcode="6001234567892",
            category="Pantry",
            brand="Jogoo",
            description="Sifted maize meal, Kenya's staple food brand.",
            image_url="https://images.unsplash.com/photo-1574316071802-0d684efa7bf5?w=200&auto=format&fit=crop&q=60",
        )
        bread = Product.objects.create(
            name="Broadways White Bread 400g",
            sku="BROADWAYS-BREAD-400G",
            barcode="6001234567893",
            category="Bakery",
            brand="Broadways",
            description="Freshly baked premium white bread sliced.",
            image_url="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&auto=format&fit=crop&q=60",
        )
        cooking_oil = Product.objects.create(
            name="Fresh Fri Cooking Oil 1L",
            sku="FRESHFRI-OIL-1L",
            barcode="6001234567894",
            category="Pantry",
            brand="Fresh Fri",
            description="Triple refined vegetable cooking oil.",
            image_url="https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&auto=format&fit=crop&q=60",
        )

        # 5. Create Product Prices
        ProductPrice.objects.create(product=milk, branch=cf_sarit, price=Decimal("102.00"))
        ProductPrice.objects.create(product=sugar, branch=cf_sarit, price=Decimal("210.00"))
        ProductPrice.objects.create(product=maize, branch=cf_sarit, price=Decimal("185.00"))
        ProductPrice.objects.create(product=bread, branch=cf_sarit, price=Decimal("65.00"))
        ProductPrice.objects.create(product=cooking_oil, branch=cf_sarit, price=Decimal("345.00"))

        ProductPrice.objects.create(product=milk, branch=cf_junction, price=Decimal("104.00"))
        ProductPrice.objects.create(product=sugar, branch=cf_junction, price=Decimal("208.00"))
        ProductPrice.objects.create(product=maize, branch=cf_junction, price=Decimal("182.00"))
        ProductPrice.objects.create(product=bread, branch=cf_junction, price=Decimal("67.00"))
        ProductPrice.objects.create(product=cooking_oil, branch=cf_junction, price=Decimal("340.00"))

        ProductPrice.objects.create(product=milk, branch=nv_westlands, price=Decimal("98.00"))
        ProductPrice.objects.create(product=sugar, branch=nv_westlands, price=Decimal("215.00"))
        ProductPrice.objects.create(product=maize, branch=nv_westlands, price=Decimal("180.00"))
        ProductPrice.objects.create(product=bread, branch=nv_westlands, price=Decimal("62.00"))
        ProductPrice.objects.create(product=cooking_oil, branch=nv_westlands, price=Decimal("350.00"))

        ProductPrice.objects.create(product=milk, branch=nv_kilimani, price=Decimal("99.00"))
        ProductPrice.objects.create(product=sugar, branch=nv_kilimani, price=Decimal("212.00"))
        ProductPrice.objects.create(product=maize, branch=nv_kilimani, price=Decimal("184.00"))
        ProductPrice.objects.create(product=bread, branch=nv_kilimani, price=Decimal("63.00"))

        ProductPrice.objects.create(product=milk, branch=qm_lavington, price=Decimal("105.00"))
        ProductPrice.objects.create(product=maize, branch=qm_lavington, price=Decimal("178.00"))
        ProductPrice.objects.create(product=bread, branch=qm_lavington, price=Decimal("60.00"))
        ProductPrice.objects.create(product=cooking_oil, branch=qm_lavington, price=Decimal("335.00"))

        self.stdout.write(self.style.SUCCESS("Database seeded successfully (development mode)."))
