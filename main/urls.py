from django.urls import path
from . import views 
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('ajax/add_record/', views.add_record_view, name='add_record'),
    path('ajax/filter_dashboard/', views.filter_dashboard_view, name='filter_dashboard'),
    path('ajax/create_payment/', views.create_payment_view, name='create_payment'),
    path('analytics/', views.analytics_view, name='analytics'),
    
]