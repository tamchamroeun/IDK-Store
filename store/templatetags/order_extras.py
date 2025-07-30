from django import template

register = template.Library()

@register.filter
def count_status(orders, status):
    """Counts the number of orders with the given status."""
    if hasattr(orders, 'filter'):
        return orders.filter(status=status).count()
    # fallback for plain lists
    return len([order for order in orders if order.status == status])