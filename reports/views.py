from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import csv

from accounts.decorators import owner_required
from orders.models import Order, OrderItem
from .forms import ReportFilterForm

from django.template.loader import render_to_string
try:
    from weasyprint import HTML
    weasyprint_installed = True
except ImportError:
    weasyprint_installed = False

@login_required
@owner_required
def dashboard(request):
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_stats = {
        'total_orders': Order.objects.filter(created_at__date__gte=thirty_days_ago).count(),
        'total_revenue': Order.objects.filter(
            created_at__date__gte=thirty_days_ago,
            status='delivered'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00'),
        'average_order_value': Order.objects.filter(
            created_at__date__gte=thirty_days_ago,
            status='delivered'
        ).aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0.00'),
        'total_customers': Order.objects.filter(
            created_at__date__gte=thirty_days_ago
        ).values('user').distinct().count(),
    }
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=thirty_days_ago,
        order__status='delivered'
    ).values('product__name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_sold')[:5]

    context = {
        'stats': recent_stats,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'thirty_days_ago': thirty_days_ago,
    }
    return render(request, 'reports/dashboard.html', context)

@login_required
@owner_required
def sales_report(request):
    form = ReportFilterForm(request.GET or None)
    report_data = None
    if form.is_valid():
        report_type = form.cleaned_data['report_type']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        report_data = generate_sales_report(report_type, start_date, end_date)
    context = {
        'form': form,
        'report_data': report_data,
    }
    return render(request, 'reports/sales_report.html', context)

@login_required
@owner_required
def export_report(request):
    """
    Export sales report as CSV, JSON, or PDF.
    Accepts GET parameters: report_type, start_date, end_date, format
    """
    report_type = request.GET.get('report_type', 'sales')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    fmt = request.GET.get('format', 'csv')

    # Defensive: If no dates, use all data
    if not start_date or not end_date:
        earliest = Order.objects.order_by('created_at').first()
        latest = Order.objects.order_by('-created_at').first()
        start_date = earliest.created_at.date() if earliest else timezone.now().date()
        end_date = latest.created_at.date() if latest else timezone.now().date()

    report_data = generate_sales_report(report_type, start_date, end_date)

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order Status', 'Count', 'Revenue'])
        for status in report_data['status_breakdown']:
            writer.writerow([
                status['status'].title() if 'status' in status else '',
                status['count'],
                float(status['revenue']) if status['revenue'] is not None else 0.0,
            ])
        writer.writerow([])
        writer.writerow(['Date', 'Orders', 'Revenue'])
        for day in report_data['daily_sales']:
            writer.writerow([
                day['day'],
                day['orders_count'],
                float(day['revenue']) if day['revenue'] is not None else 0.0,
            ])
        return response

    elif fmt == 'json':
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return str(obj)
        response = HttpResponse(
            json.dumps(report_data, default=decimal_default, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.json"'
        return response

    elif fmt == 'pdf':
        if not weasyprint_installed:
            return HttpResponse("WeasyPrint is not installed. PDF export is unavailable.", content_type='text/plain', status=501)
        html_string = render_to_string('reports/sales_report_pdf.html', {'report_data': report_data})
        try:
            pdf_file = HTML(string=html_string).write_pdf()
        except Exception as e:
            return HttpResponse(f"PDF generation failed: {e}", content_type='text/plain', status=500)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.pdf"'
        return response

    else:
        return JsonResponse({'error': 'Unsupported format'}, status=400)

def generate_sales_report(report_type, start_date, end_date):
    """
    Generate comprehensive sales report data.
    Returns a dict with summary and breakdowns.
    """
    # Only delivered orders for main KPIs
    delivered_orders = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='delivered'
    )

    total_orders = delivered_orders.count()
    total_revenue = delivered_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    average_order_value = delivered_orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0.00')
    total_items_sold = OrderItem.objects.filter(
        order__in=delivered_orders
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0

    # All statuses for breakdown, revenue is sum for each status, not just delivered
    status_breakdown = list(
        Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('status').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('status')
    )
    for s in status_breakdown:
        s['revenue'] = float(s['revenue'] or 0.0)

    # Daily sales (delivered orders only for revenue)
    daily_sales = list(
        Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            orders_count=Count('id'),
            revenue=Sum('total_amount', filter=Q(status='delivered'))
        ).order_by('day')
    )
    for d in daily_sales:
        d['revenue'] = float(d['revenue'] or 0.0)

    return {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'average_order_value': float(average_order_value),
        'total_items_sold': total_items_sold,
        'status_breakdown': status_breakdown,
        'daily_sales': daily_sales,
    }