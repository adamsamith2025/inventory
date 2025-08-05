from django.contrib import admin
from .models import (
    Product, Warehouse, StockLocation, 
    StockMovement, StockMovementLine, StockBalance, LotTracking
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'company')
    list_filter = ('category', 'company')
    search_fields = ('code', 'name')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'warehouse')
    list_filter = ('warehouse',)
    search_fields = ('name',)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'date', 'movement_type', 'destination_location', 'performed_by')
    list_filter = ('movement_type', 'date')
    search_fields = ('reference', 'notes')

@admin.register(StockMovementLine)
class StockMovementLineAdmin(admin.ModelAdmin):
    list_display = ('movement', 'product', 'quantity', 'unit_cost', 'lot_tracking')
    list_filter = ('movement', 'product')
    search_fields = ('movement__reference', 'product__code')

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'location', 'initial_quantity', 'total_in_display', 'total_out_display', 'reserved_quantity', 'available_stock_display')
    list_filter = ('location', 'product')
    search_fields = ('product__code', 'location__name')
    
    def total_in_display(self, obj):
        """Display total in movements"""
        return f"{obj.total_in:.0f} units"
    total_in_display.short_description = 'Total In'
    total_in_display.admin_order_field = 'initial_quantity'
    
    def total_out_display(self, obj):
        """Display total out movements"""
        return f"{obj.total_out:.0f} units"
    total_out_display.short_description = 'Total Out'
    total_out_display.admin_order_field = 'initial_quantity'
    
    def available_stock_display(self, obj):
        """Display available stock in admin"""
        return f"{obj.available_stock:.0f} units"
    available_stock_display.short_description = 'Available Stock'
    available_stock_display.admin_order_field = 'initial_quantity'

@admin.register(LotTracking)
class LotTrackingAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_number', 'notes')
    list_filter = ('product',)
    search_fields = ('product__code', 'lot_number')
