from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    TableViewSet,
    ReservationViewSet,
    OrderViewSet,
    OrderItemViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-items', OrderItemViewSet, basename='orderitem')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]
