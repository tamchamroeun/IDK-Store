from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('add-product/', views.add_product, name='add_product'),
    path('add-category/', views.add_category, name='add_category'),
    path('product-management/', views.product_management, name='product_management'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
]