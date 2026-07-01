# Generated migration to add normalized_name field and populate it for existing rows
from django.db import migrations, models
import django.db.models.deletion


def populate_normalized_names(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    import re

    normalize_re = re.compile(r'[^a-z0-9]+')

    for p in Product.objects.all():
        name = getattr(p, 'name', None)
        if not name:
            continue
        normalized = name.lower()
        normalized = normalized.replace('&', ' and ')
        normalized = normalize_re.sub(' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        if normalized:
            Product.objects.filter(pk=p.pk).update(normalized_name=normalized)


def clear_normalized_names(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Product.objects.all().update(normalized_name=None)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='normalized_name',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
        migrations.RunPython(populate_normalized_names, reverse_code=clear_normalized_names),
    ]
