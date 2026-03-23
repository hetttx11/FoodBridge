# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 1. CUSTOM USER MODEL
# We extend the default Django User to add our specific roles and verification logic.
class User(AbstractUser):
    # Defining Roles
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('RESTAURANT', 'Restaurant'),
        ('NGO', 'NGO'),
        ('DELIVERY', 'Delivery Partner'),
    )
    
    # --- CHOICES FOR RESTAURANT ML DATA ---
    BUSINESS_CHOICES = (
        ('RESTAURANT', 'Standard Restaurant'),
        ('BAKERY', 'Bakery / Cafe'),
        ('HOTEL', 'Hotel / Buffet'),
        ('CATERER', 'Event Caterer'),
        ('GROCERY', 'Grocery / Supermarket'),
    )
    DAY_CHOICES = (
        ('MONDAY', 'Monday'), ('TUESDAY', 'Tuesday'), ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'), ('FRIDAY', 'Friday'), ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'), ('EVERYDAY', 'Consistent Every Day'), ('WEEKEND', 'Weekends'),
    )

    # --- CHOICES FOR DELIVERY ML DATA ---
    OCCUPATION_CHOICES = (
        ('STUDENT', 'Student'),
        ('PROFESSIONAL', 'Working Professional'),
        ('FREELANCE', 'Freelancer / Gig Worker'),
        ('OTHER', 'Other'),
    )
    VEHICLE_CHOICES = (
        ('BIKE', 'Motorcycle / Scooter'),
        ('BICYCLE', 'Bicycle'),
        ('CAR', 'Car / Van'),
        ('WALK', 'Walking'),
    )
    SHIFT_CHOICES = (
        ('MORNING', 'Morning (8 AM - 12 PM)'),
        ('AFTERNOON', 'Afternoon (12 PM - 4 PM)'),
        ('EVENING', 'Evening (4 PM - 8 PM)'),
        ('NIGHT', 'Late Night (8 PM onwards)'),
    )

    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='ADMIN')
    
    # Common fields
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_document = models.ImageField(upload_to='documents/', null=True, blank=True)
    
    # RESTAURANT FIELDS
    total_people_served = models.IntegerField(default=0)
    total_carbon_saved = models.FloatField(default=0.0) 
    business_type = models.CharField(max_length=20, choices=BUSINESS_CHOICES, null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True, help_text="Critical for predicting delivery surges.")
    peak_surplus_day = models.CharField(max_length=15, choices=DAY_CHOICES, null=True, blank=True)
    seating_capacity = models.IntegerField(null=True, blank=True, help_text="Correlates to max surplus volume.")

    # DELIVERY PARTNER FIELDS
    deliveries_completed = models.IntegerField(default=0)
    age = models.PositiveIntegerField(null=True, blank=True)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, null=True, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES, null=True, blank=True)
    preferred_shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.role}"

# 2. FOOD DONATION MODEL
# This is what the Restaurant posts.
class FoodDonation(models.Model):
    # Food Categories for Analytics
    CATEGORY_CHOICES = (
        ('COOKED_MEAL', 'Cooked Meals (Buffet/Restaurant)'),
        ('RAW_PRODUCE', 'Raw Produce (Vegetables/Fruits)'),
        ('BAKED_GOODS', 'Baked Goods (Bread/Pastries)'),
        ('PACKAGED', 'Packaged/Canned Food'),
    )
    
    # Perishability for Logistics Priority
    PERISHABILITY_CHOICES = (
        ('HIGH', 'High (Spoils in < 4 hours)'),
        ('MEDIUM', 'Medium (Spoils in < 24 hours)'),
        ('LOW', 'Low (Lasts for days)'),
    )

    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    food_name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # --- The Original Fields ---
    image = models.ImageField(upload_to='food_images/', null=True, blank=True)
    prepared_time = models.DateTimeField(null=True, blank=True)
    expiry_time = models.DateTimeField(null=True, blank=True)
    # ---------------------------
    
    status = models.CharField(max_length=20, default='AVAILABLE') 
    created_at = models.DateTimeField(auto_now_add=True)
    
    # --- NEW ANALYTICS FIELDS ---
    food_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='COOKED_MEAL')
    perishability_level = models.CharField(max_length=10, choices=PERISHABILITY_CHOICES, default='HIGH')
    estimated_weight_kg = models.FloatField(null=True, blank=True, help_text="Used for load-balancing bikes vs cars")
    estimated_value_inr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Economic value saved")

    def __str__(self):
        return f"{self.food_name} by {self.donor.username}"


class DonationClaim(models.Model):
    CONDITION_CHOICES = (
        ('EXCELLENT', 'Excellent'),
        ('ACCEPTABLE', 'Acceptable'),
        ('SPOILED', 'Spoiled/Unusable'),
    )

    food = models.OneToOneField(FoodDonation, on_delete=models.CASCADE, related_name='claim')
    ngo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    is_delivery_needed = models.BooleanField(default=False)
    delivery_partner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    delivery_status = models.CharField(max_length=20, default='PENDING') 
    
    # --- TIMESTAMPS ---
    claimed_at = models.DateTimeField(auto_now_add=True)
    is_distributed = models.BooleanField(default=False)
    
    # --- NEW ANALYTICS FIELDS: LOGISTICS ---
    time_picked_up = models.DateTimeField(null=True, blank=True)
    time_delivered = models.DateTimeField(null=True, blank=True)
    delivery_distance_km = models.FloatField(null=True, blank=True, help_text="Stored statically for historical analysis")
    
    # --- NEW ANALYTICS FIELDS: QUALITY ---
    condition_upon_arrival = models.CharField(max_length=20, choices=CONDITION_CHOICES, null=True, blank=True)
    was_rejected_by_ngo = models.BooleanField(default=False, help_text="Did the NGO refuse the food at the door?")
    cancellation_reason = models.TextField(null=True, blank=True, help_text="Why did the driver drop the job?")

    def __str__(self):
        return f"Claim for {self.food.food_name} by {self.ngo.username}"