from django.contrib import admin
from .models import Category, Product, Table, Reservation, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'seats', 'is_active']
    list_filter = ['is_active']
    list_editable = ['is_active']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'table', 'date', 'pax', 'status']
    list_filter = ['status', 'date']
    search_fields = ['customer_name', 'customer_phone']
    list_editable = ['status']
    date_hierarchy = 'date'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ['price_at_order']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price_at_order']
    list_filter = ['order__status']
    readonly_fields = ['price_at_order']
