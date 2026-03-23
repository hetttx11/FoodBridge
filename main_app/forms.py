from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import User, FoodDonation

# --- 1. USER REGISTRATION FORM ---
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


# --- 2. USER VERIFICATION FORM ---
class VerificationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['verification_document']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['verification_document'].widget.attrs.update({'class': 'form-control'})


# --- 3. FOOD DONATION FORM (With Analytics & Validation) ---
class FoodDonationForm(forms.ModelForm):
    class Meta:
        model = FoodDonation
        fields = [
            'food_name', 'food_category', 'perishability_level', 'quantity', 
            'estimated_weight_kg', 'estimated_value_inr', 'description', 
            'image', 'prepared_time', 'expiry_time'
        ]
        widgets = {
            'prepared_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expiry_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Apply Bootstrap styling to all fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # 2. NEW: HTML Frontend Calendar Locking
        # Get current time in the exact string format HTML needs: YYYY-MM-DDTHH:MM
        now_str = timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')
        
        # Prepared time cannot be in the future (Max limit = right now)
        self.fields['prepared_time'].widget.attrs['max'] = now_str
        
        # Expiry time cannot be in the past (Min limit = right now)
        self.fields['expiry_time'].widget.attrs['min'] = now_str

    # 3. BACKEND VALIDATION (Keep this for security!)
    def clean(self):
        cleaned_data = super().clean()
        prepared_time = cleaned_data.get('prepared_time')
        expiry_time = cleaned_data.get('expiry_time')
        now = timezone.now()

        if prepared_time and prepared_time > now:
            self.add_error('prepared_time', "Preparation time cannot be in the future.")

        if expiry_time and expiry_time < now:
            self.add_error('expiry_time', "Expiry time cannot be in the past (already expired).")

        if prepared_time and expiry_time and expiry_time <= prepared_time:
            self.add_error('expiry_time', "Expiry time must be strictly after the preparation time.")

        return cleaned_data

# --- 4. RESTAURANT ML PROFILE FORM ---
class RestaurantProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'phone', 'address', 'business_type', 
            'closing_time', 'peak_surplus_day', 'seating_capacity'
        ]
        widgets = {
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

# --- 5. DELIVERY PARTNER PROFILE FORM ---
class DeliveryProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'phone', 'age', 'occupation', 
            'vehicle_type', 'preferred_shift'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})