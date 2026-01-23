from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import Category, Product, Table, Reservation, Order, OrderItem
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductListSerializer,
    TableSerializer,
    ReservationSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    OrderItemSerializer
)


# ============================================
# Domain: Menu & Catalog
# ============================================

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations
    Supports filtering by category and active status
    """
    queryset = Product.objects.select_related('category').all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer
    
    def get_queryset(self):
        """
        Filter products by category and active status
        Query params: ?category=1&is_active=true
        """
        queryset = super().get_queryset()
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Custom endpoint to get only active products
        GET /api/products/active/
        """
        active_products = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_products, many=True)
        return Response(serializer.data)


# ============================================
# Domain: Hall (Tables & Reservations)
# ============================================

class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Table CRUD operations
    """
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get available tables
        GET /api/tables/available/
        """
        available_tables = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(available_tables, many=True)
        return Response(serializer.data)


class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Reservation CRUD operations with validation
    """
    queryset = Reservation.objects.select_related('table').all()
    serializer_class = ReservationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Filter reservations by status and date
        Query params: ?status=CONFIRMED&date=2025-12-25
        """
        queryset = super().get_queryset()
        
        # Filter by status
        reservation_status = self.request.query_params.get('status')
        if reservation_status:
            queryset = queryset.filter(status=reservation_status)
        
        # Filter by date (exact match)
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date__date=date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm a reservation
        POST /api/reservations/{id}/confirm/
        """
        reservation = self.get_object()
        reservation.status = 'CONFIRMED'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a reservation
        POST /api/reservations/{id}/cancel/
        """
        reservation = self.get_object()
        reservation.status = 'CANCELLED'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)


# ============================================
# Domain: Order Management
# ============================================

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order CRUD operations with nested items
    """
    queryset = Order.objects.select_related('table').prefetch_related('items__product').all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return OrderCreateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    def get_queryset(self):
        """
        Filter orders by status and table
        Query params: ?status=NEW&table=1
        """
        queryset = super().get_queryset()
        
        # Filter by status
        order_status = self.request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)
        
        # Filter by table
        table_id = self.request.query_params.get('table')
        if table_id:
            queryset = queryset.filter(table_id=table_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """
        Add an item to an existing order
        POST /api/orders/{id}/add_item/
        Body: {"product": 1, "quantity": 2, "notes": "No onions"}
        """
        order = self.get_object()
        serializer = OrderItemSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(order=order)
            # Total is automatically updated by OrderItem.save()
            order.refresh_from_db()
            order_serializer = OrderSerializer(order)
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        """
        Remove an item from an order
        DELETE /api/orders/{id}/remove_item/?item_id=1
        """
        order = self.get_object()
        item_id = request.query_params.get('item_id')
        
        if not item_id:
            return Response(
                {'error': 'item_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            item = order.items.get(id=item_id)
            item.delete()
            # Total is automatically updated by OrderItem.delete()
            order.refresh_from_db()
            order_serializer = OrderSerializer(order)
            return Response(order_serializer.data)
        except OrderItem.DoesNotExist:
            return Response(
                {'error': 'Item not found in this order'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update order status
        POST /api/orders/{id}/update_status/
        Body: {"status": "COOKING"}
        """
        order = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'status field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status choice
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Valid choices: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get active orders (not paid)
        GET /api/orders/active/
        """
        active_orders = self.get_queryset().exclude(status='PAID')
        serializer = self.get_serializer(active_orders, many=True)
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for OrderItem CRUD operations
    """
    queryset = OrderItem.objects.select_related('order', 'product').all()
    serializer_class = OrderItemSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Filter order items by order
        Query params: ?order=1
        """
        queryset = super().get_queryset()
        
        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        return queryset
