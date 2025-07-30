from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product
from .forms import ProductForm, CategoryForm

def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('store:dashboard')
    else:
        form = ProductForm()
    return render(request, 'products/add_product.html', {'form': form})

def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully!')
            return redirect('store:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm()
    return render(request, 'products/add_category.html', {'form': form})

def dashboard(request):
    products = Product.objects.all()
    return render(request, 'products/dashboard.html', {'products': products})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'products/product_detail.html', {'product': product})

def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('store:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/edit_product.html', {'form': form, 'product': product})

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('store:dashboard')
    return render(request, 'products/delete_product.html', {'product': product})

def product_management(request):
    products = Product.objects.all()
    return render(request, 'products/product_management.html', {'products': products})