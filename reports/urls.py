from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Sales Reports
    path('sales/', views.sales_report, name='sales_report'),
    
    # Export functionality
    path('export/', views.export_report, name='export_report'),
]