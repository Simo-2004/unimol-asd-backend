from rest_framework import serializers
from .models import Category, Product, Table, Reservation, Order, OrderItem


# ============================================
# Domain: Menu & Catalog
# ============================================

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'products_count']
    
    def get_products_count(self, obj):
        """Return the number of products in this category"""
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Product model
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'description', 
            'price', 
            'category', 
            'category_name',
            'is_active'
        ]
        read_only_fields = ['id']
    
    def validate_price(self, value):
        """Ensure price is positive"""
        if value < 0:
            raise serializers.ValidationError("Price must be greater than or equal to 0")
        return value


# ============================================
# Domain: Hall (Tables & Reservations)
# ============================================

class TableSerializer(serializers.ModelSerializer):
    """
    Serializer for Table model
    """
    class Meta:
        model = Table
        fields = ['id', 'number', 'seats', 'is_active']
        read_only_fields = ['id']


class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer for Reservation model with validation for overlapping bookings
    """
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'date',
            'pax',
            'table',
            'table_number',
            'status'
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        """
        Validate that the table is not already reserved at the same time
        """
        table = attrs.get('table')
        date = attrs.get('date')
        status = attrs.get('status', 'PENDING')
        
        if table and date and status in ['PENDING', 'CONFIRMED']:
            from datetime import timedelta
            start_time = date - timedelta(hours=2)
            end_time = date + timedelta(hours=2)
            
            # Build query
            overlapping = Reservation.objects.filter(
                table=table,
                date__range=(start_time, end_time),
                status__in=['PENDING', 'CONFIRMED']
            )
            
            # Exclude current instance if updating
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                existing = overlapping.first()
                raise serializers.ValidationError({
                    'table': f"Table {table.number} is already reserved around this time. "
                            f"Existing reservation: {existing.date.strftime('%Y-%m-%d %H:%M')}"
                })
        
        return attrs


# ============================================
# Domain: Order Management
# ============================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem model
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'quantity',
            'notes',
            'price_at_order',
            'subtotal'
        ]
        read_only_fields = ['id', 'price_at_order']
    
    def get_subtotal(self, obj):
        """Calculate subtotal for this item"""
        return obj.price_at_order * obj.quantity
    
    def validate_quantity(self, value):
        """Ensure quantity is at least 1"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model with nested OrderItems
    """
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'table',
            'table_number',
            'status',
            'created_at',
            'updated_at',
            'total_amount',
            'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount']


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an Order with nested OrderItems
    """
    items = OrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = ['id', 'table', 'status', 'items']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """
        Create order with nested items
        """
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        # Total is automatically calculated by OrderItem.save()
        return order
    
    def update(self, instance, validated_data):
        """
        Update order and handle nested items if provided
        """
        items_data = validated_data.pop('items', None)
        
        # Update order fields
        instance.table = validated_data.get('table', instance.table)
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        
        # If items are provided, replace existing items
        if items_data is not None:
            # Delete existing items
            instance.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                OrderItem.objects.create(order=instance, **item_data)
        
        return instance


# ============================================
# List Serializers (for optimized list views)
# ============================================

class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'category_name', 'is_active']


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order lists"""
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'table_number',
            'status',
            'total_amount',
            'items_count',
            'created_at'
        ]
    
    def get_items_count(self, obj):
        """Return the number of items in this order"""
        return obj.items.count()
