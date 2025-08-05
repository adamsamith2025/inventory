from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views import (
    ProductViewSet, WarehouseViewSet,
    StockLocationViewSet, StockMovementViewSet, StockBalanceViewSet, LotTrackingViewSet
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'locations', StockLocationViewSet)
router.register(r'movements', StockMovementViewSet)
router.register(r'balances', StockBalanceViewSet)
router.register(r'lots', LotTrackingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
