from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
from .models import Cart, CartItem, WishList
from products.models import Product


def get_or_create_cart(user):
    """Helper function to get or create a cart for a user"""
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_view(request):
    """Display the shopping cart"""
    cart = get_or_create_cart(request.user)
    subtotal = cart.total_price
    tax_rate = 0.08  # 8% tax rate
    tax_amount = subtotal * Decimal(str(tax_rate))
    total_with_tax = subtotal + tax_amount
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'total_price': subtotal,
        'tax_amount': tax_amount,
        'total_with_tax': total_with_tax,
        'total_items': cart.total_items,
    }
    return render(request, 'cart/cart.html', context)


@login_required
@require_POST
def add_to_cart(request, product_id):
    """Add a product to the shopping cart"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request.user)
    
    # Get quantity from POST data
    quantity = int(request.POST.get('quantity', 1))
    
    # Check if product has sufficient stock
    if quantity > product.quantity:
        messages.error(request, f"Only {product.quantity} items available in stock.")
        return redirect('products:product_detail', product_id=product.id)
    
    # Check if item already exists in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        # Update quantity if item already exists
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.quantity:
            messages.error(request, f"Cannot add more items. Only {product.quantity} available.")
            return redirect('cart:cart_view')
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f"Updated {product.name} quantity in cart.")
    else:
        messages.success(request, f"Added {product.name} to cart.")
    
    return redirect('cart:cart_view')


@require_POST
@login_required
def update_cart_item(request, item_id):
    user = request.user
    try:
        item = CartItem.objects.get(id=item_id, cart__user=user)
        product = item.product
        quantity_raw = request.POST.get("quantity", 1)
        try:
            quantity = int(quantity_raw)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        # Always use the correct stock field, likely 'qty', not 'quantity'
        max_stock = getattr(product, 'qty', None) or getattr(product, 'quantity', None) or 0
        if 1 <= quantity <= max_stock:
            item.quantity = quantity
            item.save()
        else:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)

    # Recalculate totals
    cart = item.cart
    cart_items = cart.items.all()
    total_price = sum(i.product.price * i.quantity for i in cart_items)
    tax_amount = total_price * Decimal('0.1')
    total_with_tax = total_price + tax_amount
    total_items = sum(i.quantity for i in cart_items)

    return JsonResponse({
        "success": True,
        "item_total": str(item.product.price * item.quantity),
        "cart_total_items": total_items,
        "cart_total_price": str(total_price),
        "tax_amount": str(tax_amount),
        "total_with_tax": str(total_with_tax),
    })

@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove an item from the cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f"Removed {product_name} from cart.")
    return redirect('cart:cart_view')


@login_required
@require_POST
def clear_cart(request):
    """Clear all items from the cart"""
    cart = get_or_create_cart(request.user)
    cart.clear()
    messages.success(request, "Cart cleared successfully.")
    return redirect('cart:cart_view')


@login_required
def wishlist_view(request):
    """Display the wishlist"""
    wishlist, created = WishList.objects.get_or_create(user=request.user)
    context = {
        'wishlist': wishlist,
        'products': wishlist.products.all(),
    }
    return render(request, 'cart/wishlist.html', context)


@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """Add a product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = WishList.objects.get_or_create(user=request.user)
    
    if product in wishlist.products.all():
        messages.info(request, f"{product.name} is already in your wishlist.")
    else:
        wishlist.products.add(product)
        messages.success(request, f"Added {product.name} to wishlist.")
    
    return redirect('cart:wishlist_view')


@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    """Remove a product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = WishList.objects.get_or_create(user=request.user)
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        messages.success(request, f"Removed {product.name} from wishlist.")
    
    return redirect('cart:wishlist_view')


@login_required
@require_POST
def move_to_cart(request, product_id):
    """Move item from wishlist to cart"""
    product = get_object_or_404(Product, id=product_id)
    
    # Remove from wishlist
    wishlist, created = WishList.objects.get_or_create(user=request.user)
    if product in wishlist.products.all():
        wishlist.products.remove(product)
    
    # Add to cart
    cart = get_or_create_cart(request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        if cart_item.quantity + 1 <= product.quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.error(request, f"Cannot add more {product.name}. Stock limit reached.")
            return redirect('cart:wishlist_view')
    
    messages.success(request, f"Moved {product.name} from wishlist to cart.")
    return redirect('cart:cart_view')


# AJAX Views for better user experience
@login_required
@csrf_exempt
def cart_count(request):
    """AJAX endpoint to get cart item count"""
    cart = get_or_create_cart(request.user)
    return JsonResponse({'count': cart.total_items})


@login_required
@csrf_exempt
def quick_add_to_cart(request):
    """AJAX endpoint for quick add to cart"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id)
            cart = get_or_create_cart(request.user)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > product.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f'Only {product.quantity} items available.'
                    })
                cart_item.quantity = new_quantity
                cart_item.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Added {product.name} to cart',
                'cart_count': cart.total_items
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})
