from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


# ============================================
# Domain: Menu & Catalog
# ============================================

class Category(models.Model):
    """
    Represents a product category (e.g., Pizzas, Drinks, Desserts)
    """
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Represents a product in the menu (e.g., Margherita Pizza, Coca Cola)
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0.00)]
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='products'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


# ============================================
# Domain: Hall (Tables & Reservations)
# ============================================

class Table(models.Model):
    """
    Represents a table in the restaurant
    """
    number = models.IntegerField(unique=True)
    seats = models.IntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        ordering = ['number']
    
    def __str__(self):
        return f"Table {self.number}"


class Reservation(models.Model):
    """
    Represents a table reservation
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Phone number validator: only digits, +, spaces, and hyphens allowed
    phone_validator = RegexValidator(
        regex=r'^[\d\s\+\-\(\)]+$',
        message="Phone number must contain only numbers, +, spaces, hyphens, or parentheses"
    )
    
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(
        max_length=20,
        validators=[phone_validator]
    )
    date = models.DateTimeField()
    pax = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of people"
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        ordering = ['-date']
    
    def __str__(self):
        return f"Reservation for {self.customer_name} on {self.date.strftime('%Y-%m-%d %H:%M')}"
    
    def clean(self):
        """
        Validate that the table is not already reserved at the same time
        """
        if self.table and self.date:
            # Check for overlapping reservations (within 2 hours window)
            from datetime import timedelta
            start_time = self.date - timedelta(hours=2)
            end_time = self.date + timedelta(hours=2)
            
            overlapping = Reservation.objects.filter(
                table=self.table,
                date__range=(start_time, end_time),
                status__in=['PENDING', 'CONFIRMED']
            ).exclude(pk=self.pk)
            
            if overlapping.exists():
                raise ValidationError(
                    f"Table {self.table.number} is already reserved around this time. "
                    f"Existing reservation: {overlapping.first().date.strftime('%Y-%m-%d %H:%M')}"
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ============================================
# Domain: Order Management
# ============================================

class Order(models.Model):
    """
    Represents an order placed at a table
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),       # Ordine ricevuto, in attesa
        ('PREPARING', 'Preparing'),   # In preparazione/cottura
        ('READY', 'Ready'),           # Pronto per essere servito
        ('COMPLETED', 'Completed'),   # Completato/Pagato
    ]
    
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - Table {self.table.number} - {self.status}"
    
    def calculate_total(self):
        """
        Calculate the total amount from all order items
        """
        total = sum(item.price_at_order * item.quantity for item in self.items.all())
        return total
    
    def update_total(self):
        """
        Update the total_amount field with calculated value
        """
        self.total_amount = self.calculate_total()
        self.save(update_fields=['total_amount'])


class OrderItem(models.Model):
    """
    Represents an item in an order
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    notes = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Special instructions (e.g., 'No onions')"
    )
    price_at_order = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text="Price frozen at the moment of order"
    )
    
    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order.id})"
    
    def save(self, *args, **kwargs):
        """
        Automatically set price_at_order from product's current price if not set
        """
        if not self.price_at_order:
            self.price_at_order = self.product.price
        
        super().save(*args, **kwargs)
        
        # Update the order's total amount after saving the item
        self.order.update_total()
    
    def delete(self, *args, **kwargs):
        """
        Update order total after deleting an item
        """
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()
