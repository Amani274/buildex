import os
from datetime import date
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from exchange.models import Profile,Storefront,Listing
from exchange.catalogue import STORES,PRODUCTS,SOURCES,VERIFIED_ON

class Command(BaseCommand):
    help='Add six research-based demo storefronts and a dated catalogue sample; preserve all existing orders/stock.'
    @transaction.atomic
    def handle(self,*args,**options):
        if not settings.DEBUG:raise CommandError('Research/demo seeding requires DEBUG mode.')
        password=os.getenv('DEMO_PASSWORD','BuildDemo2026!')
        for spec in STORES:
            user,created=User.objects.get_or_create(username=spec['slug'])
            if created:user.set_password(password)
            user.first_name=spec['name'];user.is_staff=user.is_superuser=False;user.save()
            Profile.objects.update_or_create(user=user,defaults={'role':'supplier','verified':True,'business_name':spec['name']+' · demo'})
            Storefront.objects.update_or_create(slug=spec['slug'],defaults={**spec,'user':user,'verified_on':date.fromisoformat(VERIFIED_ON)})
        for idx,(slug,title,category,image,unit,price,weight,basis,source) in enumerate(PRODUCTS):
            Listing.objects.get_or_create(catalogue_key=f'research-v2-{idx+1}',defaults={'supplier':User.objects.get(username=slug),
                'name':title,'kind':'sale','unit':unit,'price_ngwee':int(price*100),'stock':200 if category=='Cement' else 30,
                'category':category,'image_key':image,'source_url':SOURCES[source],'price_basis':basis,'weight_kg':weight})
        for title,cat,img,weight in [('5 kVA generator','Generators & pumps','generator',75),('Water pump','Generators & pumps','pump',30),('Power drill','Power tools','drill',4)]:
            Listing.objects.filter(name=title,kind='rental').update(category=cat,image_key=img,weight_kg=weight)
        User.objects.filter(profile__role='admin').update(is_staff=False,is_superuser=False)
        self.stdout.write(self.style.SUCCESS('Six sample storefronts and 37 catalogue items ready. No real supplier accounts, live stock or commercial partnerships implied.'))
