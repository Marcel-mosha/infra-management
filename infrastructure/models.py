from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class Block(models.Model):
    """Represents the 5 campus blocks (A-E) with their specific configurations"""
    BLOCK_CHOICES = [
        ('A', 'Block A'),
        ('B', 'Block B'),
        ('C', 'Block C'),
        ('D', 'Block D'),
        ('E', 'Block E'),
    ]
    
    code = models.CharField(max_length=1, choices=BLOCK_CHOICES, unique=True)
    name = models.CharField(max_length=100, blank=True)
    has_multiple_floors = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "Campus Block"
        verbose_name_plural = "Campus Blocks"
        
    def __str__(self):
        return f"Block {self.code}"
    
    def save(self, *args, **kwargs):
        # Automatic configuration based on block type
        if self.code in ['A', 'B']:
            self.has_multiple_floors = True
        else:
            self.has_multiple_floors = False
        super().save(*args, **kwargs)

class Floor(models.Model):
    """Floors for Blocks A and B only"""
    block = models.ForeignKey(
        Block, 
        on_delete=models.CASCADE, 
        limit_choices_to={'code__in': ['A', 'B']},
        related_name='floors'
    )
    number = models.PositiveIntegerField(
        validators=[
            MinValueValidator(0),  # Ground floor = 0
            MaxValueValidator(4)   # Maximum 4 floors
        ]
    )
    name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        unique_together = ('block', 'number')
        ordering = ['block', 'number']
        
    def __str__(self):
        return f"Block {self.block.code} - Floor {self.number}"

class Room(models.Model):
    """Rooms across all blocks with special handling for Block E"""
    ROOM_TYPES = [
        ('CLASS', 'Classroom'),
        ('LAB', 'Laboratory'),
        ('OFFICE', 'Office'),
        ('STORAGE', 'Storage'),
        ('UTILITY', 'Utility'),
        ('OTHER', 'Other'),
    ]
    
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='rooms')
    floor = models.ForeignKey(
        Floor, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        limit_choices_to={'block__code__in': ['A', 'B']}
    )
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='CLASS')
    is_generator_room = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('block', 'number')
        ordering = ['block', 'number']
        
    def __str__(self):
        return f"{self.block.code}{self.number}"
    
    def save(self, *args, **kwargs):
        # Special handling for Block E's generator room
        if self.block.code == 'E':
            self.is_generator_room = True
            self.room_type = 'UTILITY'
            self.floor = None
            if not self.name:
                self.name = "Generator Room"
        
        # Ensure single-floor blocks don't have floor assignments
        if not self.block.has_multiple_floors:
            self.floor = None
            
        super().save(*args, **kwargs)

class EquipmentCategory(models.Model):
    """Categories for different equipment types"""
    name = models.CharField(max_length=100, unique=True)
    maintenance_interval = models.PositiveIntegerField(
        help_text="Recommended maintenance interval in days",
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name_plural = "Equipment Categories"
        
    def __str__(self):
        return self.name

class Equipment(models.Model):
    """Physical equipment installed in rooms"""
    EQUIPMENT_STATUS = [
        ('OK', 'Operational'),
        ('MAINT', 'Under Maintenance'),
        ('OUT', 'Out of Service'),
        ('REPLACE', 'Needs Replacement'),
    ]
    
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, related_name='equipment')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='equipment', null=True, blank=True)
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name='equipment',
        null=True,
        blank=True,
        limit_choices_to={'block__code__in': ['A', 'B']}
    )
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name='equipment',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    model_number = models.CharField(max_length=50, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True, unique=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=EQUIPMENT_STATUS, default='OK')
    last_maintenance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Equipment"
        ordering = ['room', 'name']
        
    def clean(self):
        """Ensure exactly one of room, floor, or block is specified"""
        location_fields = [self.room, self.floor, self.block]
        filled_fields = sum(1 for field in location_fields if field is not None)
        
        if filled_fields != 1:
            raise ValidationError("Exactly one of room, floor, or block must be specified.")
        
        if self.floor and self.block and self.floor.block != self.block:
            raise ValidationError("Floor and block must be consistent (floor must belong to the selected block).")
        
        if self.room and self.block and self.room.block != self.block:
            raise ValidationError("Room and block must be consistent (room must belong to the selected block).")
        
        if self.room and self.floor and self.room.floor != self.floor:
            raise ValidationError("Room and floor must be consistent (room must belong to the selected floor).")
        
        if self.floor and not self.floor.block.has_multiple_floors:
            raise ValidationError("Floor can only be specified for blocks with multiple floors (A or B).")
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name}"

class Generator(models.Model):
    """Specialized equipment for the campus generator"""
    FUEL_TYPES = [
        ('DIESEL', 'Diesel'),
        ('GAS', 'Natural Gas'),
        ('BIO', 'Biodiesel'),
    ]
    
    room = models.OneToOneField(
        Room,
        on_delete=models.CASCADE,
        limit_choices_to={'is_generator_room': True},
        related_name='generator'
    )
    capacity_kva = models.PositiveIntegerField()
    fuel_type = models.CharField(max_length=10, choices=FUEL_TYPES, default='DIESEL')
    installation_date = models.DateField()
    last_service = models.DateField()
    next_service = models.DateField()
    service_provider = models.CharField(max_length=100, blank=True)
    service_contact = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name_plural = "Generator Details"
    
    def __str__(self):
        return f"{self.capacity_kva}kVA Generator in {self.room}"

class MaintenanceRequest(models.Model):
    """Tracking system for maintenance issues"""
    PRIORITY_LEVELS = [
        ('LOW', 'Low (Non-urgent)'),
        ('MED', 'Medium (Normal)'),
        ('HIGH', 'High (Urgent)'),
        ('CRIT', 'Critical (Campus Impact)'),
    ]
    
    STATUS_FLOW = [
        ('REPORTED', 'Reported'),
        ('REVIEWED', 'Reviewed'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    ISSUE_TYPES = [
        ('ELECTRICAL', 'Electrical issues'),
        ('PLUMBING', 'Water or pipe-related issues'),
        ('HVAC', 'heating, ventilation, and air conditioning problems'),
        ('STRUCTURAL', 'Building structure issues'),
        ('EQUIPMENT', 'Equipment Failure'),
        ('FURNITURE', 'Furniture-related issues'),
        ('OTHER', 'Other'),
    ]
    
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'block__code__in': ['A', 'B']}
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, blank=True, null=True)
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_requests'
    )
    
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_requests')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests'
    )
    equipment_name = models.CharField(max_length=100, blank=True, null=True)
    issue_type = models.CharField(max_length=15, choices=ISSUE_TYPES, default='EQUIPMENT')
    problem = models.CharField(max_length=200)
    model_number = models.CharField(max_length=50, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=5, choices=PRIORITY_LEVELS, default='MED')
    status = models.CharField(max_length=15, choices=STATUS_FLOW, default='REPORTED')
    image = models.ImageField(upload_to="issue_images/", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Maintenance Request"
        verbose_name_plural = "Maintenance Requests"
        
    def save(self, *args, **kwargs):
        if self.equipment and not self.equipment_name:
            self.equipment_name = self.equipment.name
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.get_issue_type_display()} issue in {self.room} ({self.get_status_display()})"

class MaintenanceLog(models.Model):
    """Detailed records of maintenance activities"""
    request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    technician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='maintenance_logs'
    )
    action_taken = models.TextField()
    parts_used = models.TextField(blank=True)
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    completion_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-completion_date']
        verbose_name = "Maintenance Log Entry"
        verbose_name_plural = "Maintenance Logs"
    
    def __str__(self):
        return f"Maintenance on {self.request} by {self.technician}"