from django.shortcuts import render

from products.models import Product

# Create your views here.
def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})

def dashboard(request):
    products = Product.objects.all()
    return render(request, 'store/dashboard.html', {'products': products})