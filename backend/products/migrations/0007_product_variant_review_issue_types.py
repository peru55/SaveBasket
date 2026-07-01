from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_product_identity_alias"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="variant",
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="productimportreview",
            name="issue_type",
            field=models.CharField(
                choices=[
                    ("possible_duplicate", "Possible duplicate"),
                    ("low_confidence_match", "Low-confidence match"),
                    ("ambiguous_variant", "Ambiguous variant"),
                    ("missing_variant", "Missing variant"),
                    (
                        "possible_wrong_price_from_listing",
                        "Possible wrong price from listing",
                    ),
                ],
                db_index=True,
                max_length=40,
            ),
        ),
    ]
