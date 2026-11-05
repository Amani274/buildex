import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    ROLES = [(x, x.title()) for x in ['purchaser', 'supplier', 'transporter', 'supervisor', 'admin']]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=16, choices=ROLES)
    verified = models.BooleanField(default=False)
    business_name = models.CharField(max_length=120, blank=True)

class Listing(models.Model):
    supplier = models.ForeignKey(User, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=[('sale', 'Sale'), ('rental', 'Rental')])
    unit = models.CharField(max_length=24, default='each')
    price_ngwee = models.PositiveIntegerField()
    stock = models.PositiveIntegerField()
    deposit_ngwee = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    category = models.CharField(max_length=40, default='Materials')
    image_key = models.CharField(max_length=30, default='materials')
    source_url = models.URLField(blank=True)
    price_basis = models.CharField(max_length=30, default='demo')
    weight_kg = models.FloatField(default=1)
    catalogue_key = models.CharField(max_length=80, unique=True, null=True, blank=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(price_ngwee__gt=0), name='listing_positive_price')]

class CartItem(models.Model):
    purchaser = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['purchaser', 'listing'], name='cart_unique_listing'),
                       models.CheckConstraint(condition=Q(quantity__gt=0), name='cart_positive_quantity')]

class Quote(models.Model):
    purchaser = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requested_quotes')
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    unit_price_ngwee = models.PositiveIntegerField(null=True)
    response = models.TextField(blank=True)
    state = models.CharField(max_length=16, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    purchaser = models.ForeignKey(User, on_delete=models.PROTECT, related_name='purchases')
    supplier = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    supervisor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='site_orders')
    site = models.CharField(max_length=240)
    state = models.CharField(max_length=20, default='PLACED')
    payment_status = models.CharField(max_length=20, default='PENDING')
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='+')
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    site_latitude = models.FloatField(default=-15.4067)
    site_longitude = models.FloatField(default=28.2871)
    location_source = models.CharField(max_length=24, default='demo-default')
    delivery_ngwee = models.PositiveBigIntegerField(default=0)
    labour_ngwee = models.PositiveBigIntegerField(default=0)
    commission_ngwee = models.PositiveBigIntegerField(default=0)
    distance_km = models.FloatField(default=0)
    eta_minutes = models.PositiveIntegerField(default=45)
    transport_class = models.CharField(max_length=40, default='Pickup')
    fee_details = models.JSONField(default=dict)
    @property
    def subtotal_ngwee(self):
        return sum(i.quantity * i.unit_price_ngwee for i in self.lines.all())
    @property
    def total_ngwee(self):
        return self.subtotal_ngwee + self.delivery_ngwee + self.labour_ngwee + self.commission_ngwee

class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='lines')
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=24)
    unit_price_ngwee = models.PositiveIntegerField()

class Checkout(models.Model):
    purchaser = models.ForeignKey(User, on_delete=models.PROTECT)
    key = models.CharField(max_length=80)
    fingerprint = models.CharField(max_length=64)
    order_ids = models.JSONField(default=list)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['purchaser', 'key'], name='checkout_idempotency')]

class Delivery(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='delivery')
    transporter = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    state = models.CharField(max_length=16, default='OPEN')

class Checkpoint(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT, related_name='checkpoints')
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    state = models.CharField(max_length=16)
    note = models.CharField(max_length=500)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    source = models.CharField(max_length=16, default='status-only')
    created_at = models.DateTimeField(auto_now_add=True)

class Receipt(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='receipt')
    supervisor = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    discrepancies = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ReceiptLine(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name='lines')
    order_line = models.OneToOneField(OrderLine, on_delete=models.PROTECT)
    received = models.PositiveIntegerField()
    condition = models.CharField(max_length=16)
    notes = models.CharField(max_length=500, blank=True)

def photo_path(instance, filename):
    return f'receipts/{instance.receipt_id}/{uuid.uuid4().hex}.jpg'

class Photo(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name='photos')
    image = models.FileField(upload_to=photo_path)
    sha256 = models.CharField(max_length=64)

class Rental(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT)
    purchaser = models.ForeignKey(User, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    rate_ngwee = models.PositiveIntegerField()
    total_ngwee = models.PositiveBigIntegerField()
    deposit_ngwee = models.PositiveBigIntegerField()
    deposit_status = models.CharField(max_length=20, default='PENDING')
    deposit_reference = models.CharField(max_length=120, blank=True)
    payment_status = models.CharField(max_length=20,default='PENDING')
    payment_reference = models.CharField(max_length=120,blank=True)
    state = models.CharField(max_length=16, default='BOOKED')
    return_condition = models.CharField(max_length=500, blank=True)
    returned_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(ends_at__gt=models.F('starts_at')), name='rental_valid_range'),
                       models.CheckConstraint(condition=Q(quantity__gt=0), name='rental_positive_quantity')]

class Message(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    text = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

class Event(models.Model):
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    target = models.CharField(max_length=80)
    action = models.CharField(max_length=60)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['id']

class Storefront(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='storefront')
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    focus = models.CharField(max_length=160)
    group = models.CharField(max_length=30, default='Zambia-focused')
    address = models.CharField(max_length=240)
    latitude = models.FloatField()
    longitude = models.FloatField()
    hours = models.JSONField(default=dict)
    hours_basis = models.CharField(max_length=30, default='unverified')
    hours_source_url = models.URLField(blank=True)
    source_url = models.URLField()
    catalogue_url = models.URLField()
    verified_on = models.DateField()

class PaymentAttempt(models.Model):
    purchaser = models.ForeignKey(User, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, related_name='payment_attempts')
    rental = models.ForeignKey(Rental, on_delete=models.PROTECT, null=True, related_name='payment_attempts')
    key = models.CharField(max_length=80)
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    method = models.CharField(max_length=24, default='bank-demo')
    bank_label = models.CharField(max_length=60)
    amount_ngwee = models.PositiveBigIntegerField()
    refunded_ngwee = models.PositiveBigIntegerField(default=0)
    state = models.CharField(max_length=16, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['purchaser', 'key'], name='payment_attempt_request_key'),
                       models.CheckConstraint(condition=(Q(order__isnull=False, rental__isnull=True) | Q(order__isnull=True, rental__isnull=False)), name='one_payment_target')]

class SupportTicket(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='support_tickets')
    opened_by = models.ForeignKey(User, on_delete=models.PROTECT)
    subject = models.CharField(max_length=120)
    description = models.CharField(max_length=1500)
    state = models.CharField(max_length=16, default='OPEN')
    response = models.CharField(max_length=1500, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TermsAcceptance(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    version = models.CharField(max_length=30)
    accepted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','version'], name='terms_acceptance_version')]

class DemoBankAccount(models.Model):
    user = models.ForeignKey(User,on_delete=models.PROTECT)
    bank_label = models.CharField(max_length=60)
    balance_ngwee = models.PositiveBigIntegerField(default=10000000)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','bank_label'],name='one_demo_bank_account')]
