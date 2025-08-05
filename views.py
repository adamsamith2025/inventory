from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from inventory.models import (
    Product, Warehouse, StockLocation, 
    StockMovement, StockMovementLine, StockBalance, LotTracking
)
from inventory.serializers import (
    ProductSerializer, WarehouseSerializer,
    StockLocationSerializer, StockMovementSerializer, StockMovementLineSerializer,
    StockBalanceSerializer, LotTrackingSerializer
)
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import HasModulePermission
from hr.models import Employee, Department, JobRole
from rest_framework import serializers
from django.db.models import Sum

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'company']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name']

    @action(detail=True)
    def stock_status(self, request, pk=None):
        product = self.get_object()
        balances = StockBalance.objects.filter(product=product)
        data = {
            'total_quantity': balances.aggregate(total=Sum('initial_quantity'))['total'] or 0,
            'total_reserved': balances.aggregate(total=Sum('reserved_quantity'))['total'] or 0,
            'locations': StockBalanceSerializer(balances, many=True).data
        }
        return Response(data)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

class StockLocationViewSet(viewsets.ModelViewSet):
    queryset = StockLocation.objects.all()
    serializer_class = StockLocationSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse']
    search_fields = ['name']
    ordering_fields = ['warehouse', 'name']

    @action(detail=True)
    def stock_balance(self, request, pk=None):
        location = self.get_object()
        balances = StockBalance.objects.filter(location=location)
        serializer = StockBalanceSerializer(balances, many=True)
        return Response(serializer.data)

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'destination_location__warehouse']
    search_fields = ['reference', 'notes']
    ordering_fields = ['date', 'reference']

    def perform_create(self, serializer):
        # Find the employee by username or create a default one
        try:
            employee = Employee.objects.get(employee_code__iexact=self.request.user.username)
        except Employee.DoesNotExist:
            # For now, just use the first available employee or create a system employee
            employee = Employee.objects.first()
            if not employee:
                raise serializers.ValidationError("No employee records found. Please create at least one employee record first.")
        
        movement = serializer.save(performed_by=employee)
        
        # Automatically process the movement to update stock balances
        self.process_movement_automatically(movement)

    def perform_update(self, serializer):
        # Find the employee by username or create a default one
        try:
            employee = Employee.objects.get(employee_code__iexact=self.request.user.username)
        except Employee.DoesNotExist:
            # For now, just use the first available employee or create a system employee
            employee = Employee.objects.first()
            if not employee:
                raise serializers.ValidationError("No employee records found. Please create at least one employee record first.")
        
        movement = serializer.save(performed_by=employee)
        
        # Automatically process the movement to update stock balances
        self.process_movement_automatically(movement)

    def process_movement_automatically(self, movement):
        """
        Automatically process movement to update stock balances
        """
        with transaction.atomic():
            for line in movement.lines.all():
                # Get or create stock balance for this product and location
                stock_balance, created = StockBalance.objects.get_or_create(
                    product=line.product,
                    location=movement.destination_location,
                    defaults={'initial_quantity': 0, 'reserved_quantity': 0}
                )
                
                # Store original reserved quantity for replenishment logic
                original_reserved_quantity = stock_balance.reserved_quantity
                
                # Update stock balance based on movement type
                if movement.movement_type == 'in':
                    # For inbound movements, add stock following the priority logic
                    stock_balance.add_stock(line.quantity, original_reserved_quantity)
                elif movement.movement_type == 'out':
                    # For outbound movements, consume stock following the priority logic
                    remaining = stock_balance.consume_stock(line.quantity)
                    if remaining > 0:
                        # If we couldn't fulfill the entire order, log it or handle it
                        print(f"Warning: Could not fulfill {remaining} units for {line.product.code}")
                elif movement.movement_type == 'adjustment':
                    # For adjustments, set the initial_quantity directly
                    stock_balance.initial_quantity = line.quantity
                    stock_balance.save()
                # Note: Transfer movements don't change the base quantity
                # They are calculated in the available_stock property

    @action(detail=True, methods=['post'])
    def process_movement(self, request, pk=None):
        with transaction.atomic():
            movement = self.get_object()
            self.process_movement_automatically(movement)
            return Response({'status': 'Movement processed successfully'})

class LotTrackingViewSet(viewsets.ModelViewSet):
    queryset = LotTracking.objects.all()
    serializer_class = LotTrackingSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product']
    search_fields = ['lot_number']
    ordering_fields = ['expiry_date', 'manufacturer_date']

    @action(detail=True)
    def movements(self, request, pk=None):
        lot = self.get_object()
        movements = StockMovementLine.objects.filter(
            lot_tracking=lot
        )
        serializer = StockMovementLineSerializer(movements, many=True)
        return Response(serializer.data)

class StockBalanceViewSet(viewsets.ModelViewSet):
    queryset = StockBalance.objects.all()
    serializer_class = StockBalanceSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'location', 'location__warehouse']
    search_fields = ['product__code', 'product__name', 'location__name']
    ordering_fields = ['product__code', 'location__name', 'initial_quantity']
