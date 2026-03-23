"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from main_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- CORE ---
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='main_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('verify/', views.verify_account, name='verify_account'),

    # --- RESTAURANT ---
    path('restaurant/dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant/profile/', views.restaurant_profile, name='restaurant_profile'),
    path('restaurant/donate/', views.donate_food, name='donate_food'),
    path('restaurant/delete/<int:id>/', views.delete_donation, name='delete_donation'),
    path('restaurant/certificate/', views.download_csr_certificate, name='download_csr_certificate'),

    # --- NGO ---
    path('ngo/dashboard/', views.ngo_dashboard, name='ngo_dashboard'),
    path('ngo/claim/<int:donation_id>/', views.claim_donation, name='claim_donation'),
    path('ngo/confirm/<int:claim_id>/', views.confirm_distribution, name='confirm_distribution'),

# --- DELIVERY PARTNER ---
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/profile/', views.delivery_profile, name='delivery_profile'), # NEW
    path('delivery/accept/<int:claim_id>/', views.accept_delivery, name='accept_delivery'),
    path('delivery/complete/<int:claim_id>/', views.complete_delivery, name='complete_delivery'),
    path('delivery/certificate/', views.download_certificate, name='download_certificate'),

# --- CUSTOM ADMIN PORTAL ---
    path('portal/dashboard/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('portal/verify/<int:user_id>/', views.verify_user, name='verify_user'), # CHANGED NAME HERE
]

# Add this magic line at the end to serve images during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)