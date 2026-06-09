"""
URL configuration for savebasket project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from supermarkets.views import SupermarketViewSet, BranchViewSet
from products.views import ProductViewSet, ProductPriceViewSet
from baskets.views import BasketViewSet

router = DefaultRouter()
router.register(r'supermarkets', SupermarketViewSet, basename='supermarket')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'prices', ProductPriceViewSet, basename='price')
router.register(r'baskets', BasketViewSet, basename='basket')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
