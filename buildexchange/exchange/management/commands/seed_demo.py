import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from exchange.models import Profile, Listing

class Command(BaseCommand):
    help = 'Create fictional local demo accounts and listings; does not reset existing records.'
    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo seeding is disabled outside DEBUG mode.')
        password = os.getenv('DEMO_PASSWORD', 'BuildDemo2026!')
        for username, role in [('buyer', 'purchaser'), ('supplier', 'supplier'), ('supplier2', 'supplier'),
                               ('driver', 'transporter'), ('driver2', 'transporter'), ('supervisor', 'supervisor'),
                               ('supervisor2', 'supervisor'), ('admin', 'admin')]:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.is_staff = user.is_superuser = False
                user.save()
            if role == 'admin' and (user.is_staff or user.is_superuser):
                user.is_staff = user.is_superuser = False
                user.save(update_fields=['is_staff','is_superuser'])
            Profile.objects.get_or_create(user=user, defaults={'role': role, 'verified': True,
                'business_name': {'supplier': 'Demo Lusaka Materials', 'supplier2': 'Demo Equipment Hub'}.get(username, '')})
        if not Listing.objects.exists():
            for owner, name, kind, unit, price, stock, deposit in [
                ('supplier', 'Cement 50 kg', 'sale', 'bag', 16000, 200, 0),
                ('supplier', 'Concrete blocks', 'sale', 'block', 650, 1500, 0),
                ('supplier2', 'Roofing sheets', 'sale', 'sheet', 24000, 100, 0),
                ('supplier2', '5 kVA generator', 'rental', 'day', 35000, 2, 100000),
                ('supplier2', 'Water pump', 'rental', 'day', 18000, 3, 50000),
                ('supplier', 'Power drill', 'rental', 'day', 9000, 4, 30000)]:
                Listing.objects.create(supplier=User.objects.get(username=owner), name=name, kind=kind,
                    unit=unit, price_ngwee=price, stock=stock, deposit_ngwee=deposit)
        self.stdout.write(self.style.SUCCESS('Fictional demo ready. Accounts: buyer, supplier, supplier2, driver, driver2, supervisor, supervisor2, admin.'))
        self.stdout.write('Default password: BuildDemo2026! (or DEMO_PASSWORD when accounts were created).')
