from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone

from .models import Order, Product  # Be sure to import Product

@login_required
def order_list(request):
    """Display user's orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
        'pending_count': orders.filter(status='pending').count(),
        'confirmed_count': orders.filter(status='confirmed').count(),
        'processing_count': orders.filter(status='processing').count(),
        'shipped_count': orders.filter(status='shipped').count(),
        'delivered_count': orders.filter(status='delivered').count(),
        'cancelled_count': orders.filter(status='cancelled').count(),
        'total_count': orders.count(),
    }
    return render(request, 'orders/order_list.html', context)

@login_required
def order_detail(request, order_id):
    """Display order details"""
    order = get_object_or_404(
        Order.objects.select_related('shipping_method', 'payment'),
        order_id=order_id,
        user=request.user
    )
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
@require_POST
def mark_order_delivered(request, order_id):
    """Mark order as delivered by customer"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    if order.status != 'shipped':
        messages.error(request, 'Order must be shipped before marking as delivered.')
        return redirect('orders:order_detail', order_id=order_id)
    order.status = 'delivered'
    order.save()
    messages.success(request, 'Order marked as delivered successfully!')
    return redirect('orders:order_detail', order_id=order_id)

@login_required
def admin_order_list(request):
    """Admin view for listing all orders with AJAX support"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('store:home')

    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    is_ajax = request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    orders = (
        Order.objects
        .select_related('user', 'shipping_method')
        .prefetch_related('order_items__product', 'payment')
    )

    if status_filter:
        orders = orders.filter(status=status_filter)
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    orders = orders.order_by('-created_at')
    
    # Calculate statistics
    all_orders = Order.objects.all()  # For accurate stats
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'order_status_choices': getattr(Order, 'ORDER_STATUS_CHOICES', []),
        'total_orders': all_orders.count(),
        'pending_orders': all_orders.filter(status='pending').count(),
        'confirmed_orders': all_orders.filter(status='confirmed').count(),
        'processing_orders': all_orders.filter(status='processing').count(),
        'shipped_orders': all_orders.filter(status='shipped').count(),
        'delivered_orders': all_orders.filter(status='delivered').count(),
        'cancelled_orders': all_orders.filter(status='cancelled').count(),
        'refunded_orders': all_orders.filter(status='refunded').count(),
    }

    # Handle AJAX requests
    if is_ajax:
        # Return partial HTML response for AJAX requests
        return render(request, 'orders/admin/order_list_ajax.html', context)
    
    # Add info message for empty results (only for non-AJAX requests)
    if not orders.exists() and (status_filter or search_query):
        messages.info(request, 'No orders found matching your criteria.')

    return render(request, 'orders/admin/order_list.html', context)

@login_required
def admin_order_detail(request, order_id):
    """Admin view for order details"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('store:home')

    order = get_object_or_404(
        Order.objects.select_related('user', 'payment')
              .prefetch_related('order_items__product'),
        order_id=order_id
    )

    context = {
        'order': order,
        'status_choices': Order.ORDER_STATUS_CHOICES,
    }
    return render(request, 'orders/admin/order_detail.html', context)

@login_required
@require_POST
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Access denied'})

    order = get_object_or_404(Order, order_id=order_id)
    new_status = request.POST.get('status')

    if new_status not in dict(Order.ORDER_STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status'})

    old_status = order.status
    order.status = new_status
    order.save()

    # Update payment status when order status changes
    if hasattr(order, 'payment') and order.payment:
        payment = order.payment
        if new_status == 'confirmed' and payment.status == 'pending':
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
        elif new_status == 'cancelled' and payment.status in ['pending', 'processing']:
            payment.status = 'cancelled'
            payment.save()
        elif new_status in ['processing', 'shipped'] and payment.status == 'pending':
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
        elif new_status == 'delivered' and payment.status != 'completed':
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()

    return JsonResponse({
        'success': True,
        'new_status': new_status,
        'new_status_display': order.get_status_display(),
        'payment_status': order.payment.status if hasattr(order, 'payment') and order.payment else None
    })

@login_required
def admin_dashboard(request):
    """Admin dashboard with order statistics and product stats"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('store:home')

    # Order stats
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    shipped_orders = Order.objects.filter(status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()

    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]

    # Product stats (this is the fix for your dashboard!)
    products = Product.objects.all()
    total_products = products.count()
    in_stock = products.filter(quantity__gt=0).count()
    low_stock = products.filter(quantity__gt=0, quantity__lt=5).count()
    out_stock = products.filter(quantity=0).count()

    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'recent_orders': recent_orders,

        # Product stats for dashboard template!
        'products': products,
        'total_products': total_products,
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_stock': out_stock,
    }
    return render(request, 'store/dashboard.html', context)

@login_required
def get_pending_orders_count(request):
    """Get count of pending orders for admin notifications"""
    if not request.user.is_staff:
        return JsonResponse({'count': 0})

    pending_count = Order.objects.filter(status='pending').count()
    return JsonResponse({'count': pending_count})