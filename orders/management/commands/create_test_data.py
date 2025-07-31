from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from cart.models import Cart, CartItem
from products.models import Product


class Command(BaseCommand):
    help = 'Create test user and cart for testing'

    def handle(self, *args, **options):
        # Create or get test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        self.stdout.write(f'User: {user.username} - Created: {created}')

        # Create or get cart
        cart, created = Cart.objects.get_or_create(user=user)
        self.stdout.write(f'Cart: {cart.id} - Created: {created}')

        # Add a product to cart if exists
        product = Product.objects.first()
        if product:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, 
                product=product,
                defaults={'quantity': 1}
            )
            self.stdout.write(f'CartItem: {cart_item.id} - Product: {product.name} - Created: {created}')
        else:
            self.stdout.write('No products found')

        self.stdout.write(
            self.style.SUCCESS('Test user and cart created successfully!')
        )
