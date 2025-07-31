from django.core.management.base import BaseCommand
from orders.models import ShippingMethod


class Command(BaseCommand):
    help = 'Create sample shipping methods'

    def handle(self, *args, **options):
        shipping_methods = [
            {
                'name': 'Standard Shipping',
                'description': 'Standard delivery (5-7 business days)',
                'cost': 5.99,
                'estimated_days': 6,
            },
            {
                'name': 'Express Shipping',
                'description': 'Express delivery (2-3 business days)',
                'cost': 12.99,
                'estimated_days': 3,
            },
            {
                'name': 'Next Day Delivery',
                'description': 'Next business day delivery',
                'cost': 19.99,
                'estimated_days': 1,
            },
            {
                'name': 'Free Standard Shipping',
                'description': 'Free standard delivery (7-10 business days)',
                'cost': 0.00,
                'estimated_days': 8,
            },
        ]

        created_count = 0
        for method_data in shipping_methods:
            method, created = ShippingMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created shipping method: {method.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Shipping method already exists: {method.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} new shipping methods")
        )
