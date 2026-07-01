# Generated migration to add IngestionHistory model
from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_add_normalized_name'),
        ('supermarkets', '__first__'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='IngestionHistory',
            fields=[
                (
                    'id',
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'source_name',
                    models.CharField(blank=True, db_index=True, max_length=200, null=True),
                ),
                ('job_name', models.CharField(blank=True, max_length=100, null=True)),
                ('urls', models.TextField(blank=True, null=True, help_text='Optional newline-separated URLs processed')),
                ('products_processed', models.IntegerField(default=0)),
                ('created_products', models.IntegerField(default=0)),
                ('created_prices', models.IntegerField(default=0)),
                ('updated_prices', models.IntegerField(default=0)),
                ('success', models.BooleanField(default=False)),
                ('error_text', models.TextField(blank=True, null=True)),
                ('payload', models.JSONField(blank=True, null=True)),
                (
                    'supermarket',
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supermarkets.supermarket'),
                ),
                (
                    'branch',
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supermarkets.branch'),
                ),
                (
                    'run_by',
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user'),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
