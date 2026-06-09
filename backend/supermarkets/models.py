import uuid
from django.db import models

class Supermarket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supermarket = models.ForeignKey(Supermarket, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    city = models.CharField(max_length=100, default='Nairobi')
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Branches"
        unique_together = ('supermarket', 'name')

    def __str__(self):
        return f"{self.supermarket.name} - {self.name}"
