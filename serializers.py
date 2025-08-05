from rest_framework import serializers
from inventory.models import (
    Product, Warehouse, StockLocation,
    StockMovement, StockMovementLine, StockBalance, LotTracking
)
from core.serializers import UnitOfMeasureSerializer, CurrencySerializer, CompanySerializer
from hr.serializers import EmployeeSerializer
from finance.serializers import JournalSerializer

class ProductSerializer(serializers.ModelSerializer):
    company_details = CompanySerializer(source='company', read_only=True)
    stock_balance = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def get_stock_balance(self, obj):
        balances = StockBalance.objects.filter(product=obj)
        return {
            'total_quantity': sum(b.initial_quantity for b in balances),
            'total_reserved': sum(b.reserved_quantity for b in balances)
        }

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'created_at', 'updated_at']

class StockLocationSerializer(serializers.ModelSerializer):
    warehouse_details = WarehouseSerializer(source='warehouse', read_only=True)
    
    class Meta:
        model = StockLocation
        fields = '__all__'

class LotTrackingSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = LotTracking
        fields = '__all__'

class StockMovementLineSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    currency_details = CurrencySerializer(source='currency', read_only=True)
    lot_tracking_details = LotTrackingSerializer(source='lot_tracking', read_only=True)
    
    class Meta:
        model = StockMovementLine
        fields = ['id', 'product', 'quantity', 'unit_cost', 'currency', 'lot_tracking', 'product_details', 'currency_details', 'lot_tracking_details', 'created_at', 'updated_at']

class StockMovementSerializer(serializers.ModelSerializer):
    lines = StockMovementLineSerializer(many=True, required=False)
    destination_location_details = StockLocationSerializer(source='destination_location', read_only=True)
    performed_by_details = EmployeeSerializer(source='performed_by', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = ['id', 'reference', 'movement_type', 'date', 'destination_location', 'notes', 'lines', 'destination_location_details', 'performed_by_details', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        print(f"Creating movement with data: {validated_data}")
        lines_data = validated_data.pop('lines', [])
        print(f"Lines data for create: {lines_data}")
        
        movement = StockMovement.objects.create(**validated_data)
        
        for line_data in lines_data:
            print(f"Creating line with data: {line_data}")
            StockMovementLine.objects.create(movement=movement, **line_data)
        
        return movement
    
    def update(self, instance, validated_data):
        print(f"Updating movement {instance.id} with data: {validated_data}")
        lines_data = validated_data.pop('lines', [])
        print(f"Lines data: {lines_data}")
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        instance.lines.all().delete()
        for line_data in lines_data:
            print(f"Creating line with data: {line_data}")
            StockMovementLine.objects.create(movement=instance, **line_data)
        
        return instance

class StockBalanceSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    location_details = StockLocationSerializer(source='location', read_only=True)
    available_stock = serializers.ReadOnlyField()
    total_in = serializers.ReadOnlyField()
    total_out = serializers.ReadOnlyField()
    
    class Meta:
        model = StockBalance
        fields = '__all__'
