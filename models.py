from django.db import models
from core.models.base import BaseModel
from core.models.models import Company, UnitOfMeasure, Currency
from finance.models import Journal
from hr.models import Employee
from django.core.validators import MinValueValidator

class Product(BaseModel):
    CATEGORY_CHOICES = [
        ('raw_material', 'Raw Material'),
        ('semi_finished', 'Semi Finished Product'),
        ('finished', 'Finished Product'),
        ('consumable', 'Consumable'),
        ('spare_parts', 'Spare Parts'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='finished')
    description = models.TextField(null=True, blank=True)
    min_stock = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    max_stock = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Warehouse(BaseModel):
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class StockLocation(BaseModel):
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['warehouse', 'name']
    
    def __str__(self):
        return f"{self.warehouse.name} - {self.name}"

class StockMovement(BaseModel):
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Internal Transfer'),
        ('adjustment', 'Stock Adjustment'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    date = models.DateField()
    destination_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name='destination_movements')
    notes = models.TextField(null=True, blank=True)
    performed_by = models.ForeignKey(Employee, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.reference} ({self.get_movement_type_display()})"

class StockMovementLine(BaseModel):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    lot_tracking = models.ForeignKey('LotTracking', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.movement.reference} - {self.product.code}"

class StockBalance(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(StockLocation, on_delete=models.PROTECT)
    initial_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)  # Renamed from quantity
    reserved_quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    
    class Meta:
        unique_together = ['product', 'location']
    
    def __str__(self):
        return f"{self.product.code} @ {self.location.warehouse.name} - {self.location.name}"
    
    @property
    def total_in(self):
        """Calculate total in movements for this product and location"""
        return StockMovementLine.objects.filter(
            movement__movement_type='in',
            product=self.product,
            movement__destination_location=self.location
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_out(self):
        """Calculate total out movements for this product and location"""
        return StockMovementLine.objects.filter(
            movement__movement_type='out',
            product=self.product,
            movement__destination_location=self.location
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def available_stock(self):
        """
        Calculate available stock based on the new formula:
        available stock = initial_quantity + total_in - total_out - reserved_quantity
        """
        available = self.initial_quantity + self.total_in - self.total_out - self.reserved_quantity
        return max(available, 0)  # Ensure it's never negative
    
    def consume_stock(self, quantity_needed):
        """
        Consume stock following the priority: initial_quantity first, then reserved_quantity
        """
        remaining_to_consume = quantity_needed
        
        # First, consume from initial_quantity
        if self.initial_quantity > 0:
            if self.initial_quantity >= remaining_to_consume:
                self.initial_quantity -= remaining_to_consume
                remaining_to_consume = 0
            else:
                remaining_to_consume -= self.initial_quantity
                self.initial_quantity = 0
        
        # Then, consume from reserved_quantity if needed
        if remaining_to_consume > 0 and self.reserved_quantity > 0:
            if self.reserved_quantity >= remaining_to_consume:
                self.reserved_quantity -= remaining_to_consume
                remaining_to_consume = 0
            else:
                remaining_to_consume -= self.reserved_quantity
                self.reserved_quantity = 0
        
        self.save()
        return remaining_to_consume  # Return any remaining quantity that couldn't be consumed
    
    def add_stock(self, quantity_to_add, original_reserved_quantity=None):
        """
        Add stock following the priority: fill reserved_quantity first, then initial_quantity
        """
        if original_reserved_quantity is None:
            # If no original reserved quantity specified, use current as target
            target_reserved = self.reserved_quantity
        else:
            # Use the original reserved quantity as target
            target_reserved = original_reserved_quantity
        
        remaining_to_add = quantity_to_add
        
        # First, fill reserved_quantity up to target
        if self.reserved_quantity < target_reserved:
            needed_for_reserved = target_reserved - self.reserved_quantity
            if remaining_to_add >= needed_for_reserved:
                self.reserved_quantity = target_reserved
                remaining_to_add -= needed_for_reserved
            else:
                self.reserved_quantity += remaining_to_add
                remaining_to_add = 0
        
        # Then, add remaining to initial_quantity
        if remaining_to_add > 0:
            self.initial_quantity += remaining_to_add
        
        self.save()
        return remaining_to_add  # Return any remaining quantity that couldn't be added

class LotTracking(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    lot_number = models.CharField(max_length=50)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ['product', 'lot_number']
    
    def __str__(self):
        return f"{self.product.code} - Lot: {self.lot_number}"
