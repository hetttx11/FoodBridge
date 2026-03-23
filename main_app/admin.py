from django.contrib import admin
from .models import User, FoodDonation, DonationClaim

# --- Customizing the User view so Admin can easily verify restaurants ---
class CustomUserAdmin(admin.ModelAdmin):
    # What columns to show in the list
    list_display = ('username', 'role', 'is_verified', 'deliveries_completed', 'business_type')
    
    # Add a filter box on the right side
    list_filter = ('role', 'is_verified', 'business_type')
    
    # Add a search bar
    search_fields = ('username', 'email', 'phone')
    
    # Make these fields editable directly from the list view (super fast verifications!)
    list_editable = ('is_verified',)

# Registering the models to the Admin Panel
admin.site.register(User, CustomUserAdmin)
admin.site.register(FoodDonation)
admin.site.register(DonationClaim)