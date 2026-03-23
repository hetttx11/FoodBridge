from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
import datetime
from reportlab.pdfgen import canvas  # <--- THIS IS THE NEW LINE

from .models import User, FoodDonation, DonationClaim
from .forms import CustomUserCreationForm, FoodDonationForm, VerificationForm, RestaurantProfileForm, DeliveryProfileForm
# ==========================================
# 1. CORE AUTH & HOME LOGIC
# ==========================================

def home(request):
    # If the user is logged in, route them instantly to their dashboard
    if request.user.is_authenticated:
        if request.user.role == 'RESTAURANT':
            return redirect('restaurant_dashboard')
        elif request.user.role == 'NGO':
            return redirect('ngo_dashboard')
        elif request.user.role == 'DELIVERY':
            return redirect('delivery_dashboard')
        elif request.user.role == 'ADMIN' or request.user.is_superuser:
            # THIS IS THE NEW LINE! Routes you straight to the Command Center.
            return redirect('custom_admin_dashboard')
            
    # If they are NOT logged in, show the beautiful landing page
    return render(request, 'main_app/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'main_app/register.html', {'form': form})

@login_required
def verify_account(request):
    if request.user.is_verified:
        return redirect('home')

    # If they already uploaded a doc OR they are a cyclist/walker waiting for approval
    if request.user.verification_document or (request.user.role == 'DELIVERY' and request.user.vehicle_type in ['BICYCLE', 'WALK']):
        return render(request, 'main_app/verification_pending.html')

    if request.method == 'POST':
        # 1. DELIVERY PARTNER LOGIC
        if request.user.role == 'DELIVERY':
            vehicle = request.POST.get('vehicle_type')
            request.user.vehicle_type = vehicle
            
            # Require license for Motorized vehicles
            if vehicle in ['CAR', 'BIKE']:
                if 'document' in request.FILES:
                    request.user.verification_document = request.FILES['document']
                else:
                    messages.error(request, "Driving License is mandatory for Cars and Bikes.")
                    return redirect('verify_account')
            request.user.save()
            
        # 2. RESTAURANT & NGO LOGIC
        else:
            if 'document' in request.FILES:
                request.user.verification_document = request.FILES['document']
                request.user.save()
            else:
                messages.error(request, "Please upload your official verification document.")
                return redirect('verify_account')
                
        return render(request, 'main_app/verification_pending.html')

    return render(request, 'main_app/verify_upload.html')

# ==========================================
# 2. RESTAURANT LOGIC
# ==========================================

@login_required
def restaurant_dashboard(request):
    if request.user.role != 'RESTAURANT':
        return render(request, 'main_app/error.html', {'message': "Access Denied"})
    my_donations = FoodDonation.objects.filter(donor=request.user).order_by('-created_at')
    return render(request, 'main_app/restaurant_dashboard.html', {'donations': my_donations})

@login_required
def restaurant_profile(request):
    if request.user.role != 'RESTAURANT':
        messages.error(request, "Access Denied.")
        return redirect('home')

    if request.method == 'POST':
        form = RestaurantProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ ML Profile & Settings updated successfully!")
            return redirect('restaurant_dashboard')
    else:
        form = RestaurantProfileForm(instance=request.user)
    return render(request, 'main_app/restaurant_profile.html', {'form': form})

@login_required
def donate_food(request):
    if not request.user.is_verified:
        return redirect('verify_account')
    if request.user.role != 'RESTAURANT':
        return render(request, 'main_app/error.html', {'message': "Only Restaurants can donate food!"})

    if request.method == 'POST':
        form = FoodDonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user
            donation.save()
            return redirect('home')
    else:
        form = FoodDonationForm()
    return render(request, 'main_app/donate.html', {'form': form})

@login_required
def delete_donation(request, id):
    donation = get_object_or_404(FoodDonation, id=id)
    if donation.donor == request.user and donation.status == 'AVAILABLE':
        donation.delete()
    return redirect('restaurant_dashboard')

# ==========================================
# 3. NGO LOGIC
# ==========================================

@login_required
def ngo_dashboard(request):
    # 1. Security & Role Checks
    if request.user.role != 'NGO':
        messages.error(request, "Access Denied. Only NGOs can view this dashboard.")
        return redirect('home')
        
    if not request.user.is_verified:
        return redirect('verify_account')

    # 2. Fetch the Data (THIS IS THE CRITICAL FIX)
    # Pulls all food that is currently waiting to be claimed
    available_food = FoodDonation.objects.filter(status='AVAILABLE').order_by('-id')
    
    # Pulls all food that THIS specific NGO has already claimed
    my_claims = DonationClaim.objects.filter(ngo=request.user).order_by('-id')

    # 3. Send it to the HTML
    return render(request, 'main_app/ngo_dashboard.html', {
        'available_food': available_food,
        'my_claims': my_claims
    })

@login_required
def claim_donation(request, donation_id):
    if request.method == 'POST' and request.user.role == 'NGO':
        food = get_object_or_404(FoodDonation, id=donation_id, status='AVAILABLE')
        
        # 1. Did the NGO ask for a driver or self-pickup?
        delivery_method = request.POST.get('delivery_method')
        
        # 2. Create the claim connection
        claim = DonationClaim.objects.create(food=food, ngo=request.user)
        
        # 3. Route it based on their choice!
        if delivery_method == 'REQUEST_DRIVER':
            food.status = 'CLAIMED'  # This pushes it to the Driver's Map
            messages.success(request, f"✅ Claimed {food.food_name}! Awaiting a volunteer rider.")
        else:
            food.status = 'SELF_PICKUP' # This hides it from drivers
            messages.success(request, f"✅ Claimed {food.food_name}! You can now go pick it up.")
            
        food.save()
        
    return redirect('ngo_dashboard')

@login_required
def confirm_distribution(request, claim_id):
    if request.method == 'POST' and request.user.role == 'NGO':
        claim = get_object_or_404(DonationClaim, id=claim_id, ngo=request.user)
        
        # Change the status to DELIVERED so it stops being active
        claim.food.status = 'DELIVERED'
        claim.food.save()
        
        messages.success(request, "🎉 Amazing work! Food marked as received and distributed.")
        
    return redirect('ngo_dashboard')

# ==========================================
# 4. DELIVERY PARTNER LOGIC
# ==========================================

# ==========================================
# 4. DELIVERY PARTNER LOGIC
# ==========================================

@login_required
def delivery_dashboard(request):
    if request.user.role != 'DELIVERY':
        messages.error(request, "Access Denied. Delivery portal only.")
        return redirect('home')
        
    # Security check: must upload license/vehicle info first
    if not request.user.is_verified:
        return redirect('verify_account')

    # Fetch jobs where the NGO explicitly clicked "Request Volunteer Rider"
    available_jobs = DonationClaim.objects.filter(food__status='CLAIMED').order_by('-id')
    
    # Fetch jobs that are currently on the road
    my_active_jobs = DonationClaim.objects.filter(food__status='IN_TRANSIT').order_by('-id')

    return render(request, 'main_app/delivery_dashboard.html', {
        'available_jobs': available_jobs,
        'my_active_jobs': my_active_jobs
    })

@login_required
def accept_delivery(request, claim_id):
    if request.method == 'POST' and request.user.role == 'DELIVERY':
        job = get_object_or_404(DonationClaim, id=claim_id, food__status='CLAIMED')
        
        # Change status so it disappears from the map for other drivers
        job.food.status = 'IN_TRANSIT'
        job.food.save()
        
        messages.success(request, f"🛵 Job Accepted! Head to {job.food.donor.username} for pickup.")
        
    return redirect('delivery_dashboard')

@login_required
def complete_delivery(request, claim_id):
    if request.method == 'POST' and request.user.role == 'DELIVERY':
        job = get_object_or_404(DonationClaim, id=claim_id, food__status='IN_TRANSIT')
        
        # Mark as delivered
        job.food.status = 'DELIVERED'
        job.food.save()
        
        # Add +1 to the driver's total runs for their certificate!
        request.user.deliveries_completed += 1
        request.user.save()
        
        messages.success(request, "🎉 Delivery Complete! You've successfully rescued food today.")
        
    return redirect('delivery_dashboard')

@login_required
def delivery_profile(request):
    if request.user.role != 'DELIVERY':
        messages.error(request, "Access Denied. Only delivery partners can edit this profile.")
        return redirect('home')

    if request.method == 'POST':
        form = DeliveryProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Driver Profile & Logistics Data updated successfully!")
            return redirect('delivery_dashboard')
    else:
        form = DeliveryProfileForm(instance=request.user)

    return render(request, 'main_app/delivery_profile.html', {'form': form})

# ==========================================
# 5. PDF GENERATION LOGIC
# ==========================================

@login_required
def download_certificate(request):
    if request.user.role != 'DELIVERY':
         return render(request, 'main_app/error.html', {'message': "Only Delivery Partners can get certificates!"})
    if request.user.deliveries_completed == 0:
         return render(request, 'main_app/error.html', {'message': "You need to complete at least 1 delivery first!"})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{request.user.username}.pdf"'
    p = canvas.Canvas(response)
    p.setLineWidth(3)
    p.rect(50, 50, 500, 750)
    p.setFont("Helvetica-Bold", 30)
    p.drawCentredString(300, 700, "FOOD BRIDGE")
    p.setFont("Helvetica", 20)
    p.drawCentredString(300, 650, "Certificate of Appreciation")
    p.setFont("Helvetica", 14)
    p.drawCentredString(300, 550, "This is to certify that")
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(300, 500, request.user.username.upper())
    p.setFont("Helvetica", 14)
    p.drawCentredString(300, 450, f"has successfully volunteered as a Delivery Partner.")
    p.drawCentredString(300, 430, f"Total Deliveries Completed: {request.user.deliveries_completed}")
    p.drawCentredString(300, 350, f"Date: {datetime.date.today()}")
    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(300, 200, "Thank you for reducing food waste.")
    p.showPage()
    p.save()
    return response

@login_required
def download_csr_certificate(request):
    if request.user.role != 'RESTAURANT':
         return redirect('home')
         
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Green_Certificate_{request.user.username}.pdf"'
    p = canvas.Canvas(response)
    p.setLineWidth(5)
    p.setStrokeColorRGB(0, 0.5, 0)
    p.rect(50, 50, 500, 750)
    p.setFont("Helvetica-Bold", 30)
    p.setFillColorRGB(0, 0.5, 0)
    p.drawCentredString(300, 700, "SUSTAINABILITY HERO")
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 16)
    p.drawCentredString(300, 600, "Presented to")
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(300, 550, request.user.username.upper())
    p.setFont("Helvetica", 14)
    p.drawCentredString(300, 480, "For outstanding contribution to Zero Hunger & Climate Action.")
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(300, 400, f"People Fed: {request.user.total_people_served}")
    p.drawCentredString(300, 370, f"CO2 Emissions Saved: {request.user.total_carbon_saved} kg")
    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(300, 200, "FoodBridge Initiative - Govt Recognized")
    p.showPage()
    p.save()
    return response

# ==========================================
# 6. CUSTOM ADMIN PORTAL
# ==========================================

@login_required
def custom_admin_dashboard(request):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        messages.error(request, "🛑 Access Denied. Command Center is for Admins only.")
        return redirect('home')

    # Fetch ALL unverified users
    pending_users = User.objects.filter(is_verified=False).exclude(role='ADMIN').order_by('-date_joined')
    
    # Platform Stats
    total_users = User.objects.count()
    total_food_rescued = FoodDonation.objects.filter(status='DELIVERED').count()

    # --- NEW: DATA SCIENCE CHART METRICS ---
    available_count = FoodDonation.objects.filter(status='AVAILABLE').count()
    claimed_count = FoodDonation.objects.filter(status__in=['CLAIMED', 'SELF_PICKUP']).count()
    transit_count = FoodDonation.objects.filter(status='IN_TRANSIT').count()
    delivered_count = FoodDonation.objects.filter(status='DELIVERED').count()

    return render(request, 'main_app/custom_admin.html', {
        'pending_users': pending_users,
        'total_users': total_users,
        'total_food_rescued': total_food_rescued,
        # Sending chart data to HTML
        'chart_data': [available_count, claimed_count, transit_count, delivered_count]
    })

@login_required
def verify_user(request, user_id):
    if request.method == 'POST' and (request.user.role == 'ADMIN' or request.user.is_superuser):
        user_to_verify = get_object_or_404(User, id=user_id)
        user_to_verify.is_verified = True
        user_to_verify.save()
        messages.success(request, f"✅ Successfully verified {user_to_verify.username} ({user_to_verify.role})!")
    return redirect('custom_admin_dashboard')