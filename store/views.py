from django.shortcuts import render

from products.models import Product
from orders.models import Order

# Create your views here.
def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})

def dashboard(request):
    products = Product.objects.all()
    context = {
        'products': products,
        'total_products': products.count(),
        'in_stock': products.filter(quantity__gt=0).count(),
        'low_stock': products.filter(quantity__gt=0, quantity__lt=5).count(),
        'out_stock': products.filter(quantity=0).count(),

        'total_orders': Order.objects.count(),

    }
    return render(request, 'store/dashboard.html', context)