"""All business writes are explicit, authorized, transactional service operations."""
import hashlib
import io
import json
import math
import warnings
import re
from collections import defaultdict
from datetime import timedelta
from PIL import Image, UnidentifiedImageError
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from .models import (Profile, Listing, CartItem, Quote, Order, OrderLine, Checkout, Delivery,
                     Checkpoint, Receipt, ReceiptLine, Photo, Rental, Message, Event)

def ensure(test, message):
    if not test:
        raise ValidationError(message)

def integer(value, label, minimum=1, maximum=100000000):
    ensure(not isinstance(value, bool) and str(value).isdigit(), f'{label} must be a whole number.')
    value = int(value)
    ensure(minimum <= value <= maximum, f'{label} must be between {minimum} and {maximum}.')
    return value

def text(value, label, maximum=500, required=True):
    ensure(isinstance(value, str), f'{label} must be text.')
    value = value.strip()
    ensure((bool(value) or not required) and len(value) <= maximum, f'{label} is required and must be at most {maximum} characters.' if required else f'{label} must be at most {maximum} characters.')
    return value

def role(user, *allowed):
    if not user.is_active or not hasattr(user, 'profile') or not user.profile.verified or user.profile.role not in allowed:
        raise PermissionDenied('A verified account with the appropriate role is required.')

def audit(user, target, action, **detail):
    Event.objects.create(actor=user, target=target, action=action, detail=detail)

def listing_for_sale(pk):
    try:
        item = Listing.objects.select_for_update().select_related('supplier__profile').get(pk=pk, active=True, kind='sale')
    except Listing.DoesNotExist:
        raise NotFound('Available sale listing not found.')
    ensure(item.supplier.is_active and item.supplier.profile.verified, 'Supplier is not verified.')
    return item

def order_scope(user):
    role(user, 'purchaser', 'supplier', 'supervisor', 'transporter', 'admin')
    if user.profile.role == 'admin':
        return Order.objects.all()
    return Order.objects.filter(Q(purchaser=user) | Q(supplier=user) | Q(supervisor=user) | Q(delivery__transporter=user)).distinct()

def get_order(user, pk):
    try:
        return order_scope(user).get(pk=pk)
    except Order.DoesNotExist:
        raise NotFound('Order not found.')

def supervisor_id(pk):
    ensure(User.objects.filter(pk=pk, is_active=True, profile__role='supervisor', profile__verified=True).exists(), 'Select a verified site supervisor.')
    return pk

def add_cart(user, data):
    role(user, 'purchaser')
    item = listing_for_sale(integer(data.get('listing'), 'Listing'))
    qty = integer(data.get('quantity'), 'Quantity', 0, 100000)
    ensure(qty <= item.stock, 'Insufficient stock.')
    if qty:
        CartItem.objects.update_or_create(purchaser=user, listing=item, defaults={'quantity': qty})
    else:
        CartItem.objects.filter(purchaser=user, listing=item).delete()
    return {'message': 'Cart updated.'}

def reserve_order(user, supplier, supervisor, site, items, quote=None):
    order = Order.objects.create(purchaser=user, supplier=supplier, supervisor_id=supervisor, site=site, quote=quote)
    for listing, qty, price in items:
        changed = Listing.objects.filter(pk=listing.pk, stock__gte=qty).update(stock=F('stock')-qty)
        ensure(changed == 1, 'Stock changed. Refresh and try again.')
        OrderLine.objects.create(order=order, listing=listing, name=listing.name, quantity=qty,
                                 unit=listing.unit, unit_price_ngwee=price)
    audit(user, f'order:{order.pk}', 'order_placed', total_ngwee=order.total_ngwee, quote_id=quote.pk if quote else None)
    return order

def checkout(user, data):
    role(user, 'purchaser')
    key = text(data.get('key'), 'Request key', 80)
    ensure(len(key) >= 10, 'Request key must contain at least 10 characters.')
    site = text(data.get('site'), 'Site / delivery instructions', 240)
    supervisor = supervisor_id(integer(data.get('supervisor'), 'Supervisor'))
    fingerprint = hashlib.sha256(json.dumps({'site': site, 'supervisor': supervisor}, sort_keys=True).encode()).hexdigest()
    # Serialize checkouts for this purchaser, then lock products in stable ID order.
    User.objects.select_for_update().get(pk=user.pk)
    prior = Checkout.objects.filter(purchaser=user, key=key).first()
    if prior:
        ensure(prior.fingerprint == fingerprint, 'Request key already used with different delivery details.')
        return {'order_ids': prior.order_ids, 'replayed': True}
    cart = list(CartItem.objects.filter(purchaser=user).order_by('listing_id'))
    ensure(cart, 'Add materials to your cart first.')
    groups = defaultdict(list)
    for line in cart:
        listing = listing_for_sale(line.listing_id)
        ensure(listing.stock >= line.quantity, f'Insufficient stock: {listing.name}.')
        groups[listing.supplier_id].append((listing, line.quantity, listing.price_ngwee))
    ids = [reserve_order(user, User.objects.get(pk=supplier), supervisor, site, items).pk for supplier, items in groups.items()]
    Checkout.objects.create(purchaser=user, key=key, fingerprint=fingerprint, order_ids=ids)
    CartItem.objects.filter(purchaser=user).delete()
    return {'order_ids': ids}

def request_quote(user, data):
    role(user, 'purchaser')
    listing = listing_for_sale(integer(data.get('listing'), 'Listing'))
    q = Quote.objects.create(purchaser=user, listing=listing, quantity=integer(data.get('quantity'), 'Quantity'),
                              notes=text(data.get('notes', ''), 'Notes', 1000, False))
    audit(user, f'quote:{q.pk}', 'quote_requested')
    return {'quote_id': q.pk}

def quote_action(user, data):
    role(user, 'purchaser', 'supplier')
    ensure(data.get('operation') in ['reply', 'accept'], 'Choose reply or accept.')
    try:
        q = Quote.objects.select_for_update().select_related('listing').get(pk=integer(data.get('id'), 'Quote'))
    except Quote.DoesNotExist:
        raise NotFound('Quote not found.')
    if data.get('operation') == 'reply':
        ensure(q.listing.supplier_id == user.pk and user.profile.role == 'supplier', 'Only the listing supplier can quote.')
        ensure(q.state == 'REQUESTED', 'Quote has already been answered.')
        q.unit_price_ngwee = integer(data.get('price_ngwee'), 'Unit price in ngwee')
        q.response = text(data.get('notes', ''), 'Response', 1000, False)
        q.state = 'OFFERED'
    else:
        ensure(q.purchaser_id == user.pk and user.profile.role == 'purchaser', 'Only the requesting purchaser can accept.')
        if q.state == 'ACCEPTED':
            return {'order_ids': [q.order.pk], 'replayed': True}
        ensure(q.state == 'OFFERED', 'Supplier must offer a price first.')
        listing = listing_for_sale(q.listing_id)
        order = reserve_order(user, listing.supplier, supervisor_id(integer(data.get('supervisor'), 'Supervisor')),
                              text(data.get('site'), 'Site', 240), [(listing, q.quantity, q.unit_price_ngwee)], q)
        q.state = 'ACCEPTED'
        q.save()
        audit(user, f'quote:{q.pk}', 'quote_accepted', order_id=order.pk)
        return {'order_ids': [order.pk]}
    q.save()
    audit(user, f'quote:{q.pk}', 'quote_offered', unit_price_ngwee=q.unit_price_ngwee)
    return {'message': 'Quote updated.'}

def supplier_order(user, data):
    role(user, 'supplier')
    order = Order.objects.select_for_update().get(pk=get_order(user, integer(data.get('id'), 'Order')).pk)
    ensure(order.supplier_id == user.pk, 'Only the supplier can prepare this order.')
    operation = data.get('operation')
    if operation in ['REJECTED', 'CANCELLED']:
        ensure(operation == 'REJECTED' and order.state == 'PLACED', 'Only new orders can be rejected.')
        reason = text(data.get('notes'), 'Reason')
        for line in order.lines.order_by('listing_id'):
            Listing.objects.filter(pk=line.listing_id).update(stock=F('stock')+line.quantity)
        if order.payment_status == 'RECORDED_MANUAL':
            order.payment_status = 'REFUND_PENDING'
        audit(user, f'order:{order.pk}', 'order_rejected', reason=reason)
    else:
        ensure({'PLACED': 'ACCEPTED', 'ACCEPTED': 'READY'}.get(order.state) == operation, 'Invalid order transition.')
        if operation == 'READY':
            Delivery.objects.create(order=order)
        audit(user, f'order:{order.pk}', 'supplier_status', state=operation)
    order.state = operation
    order.save()
    return {'message': 'Supplier status recorded.'}

def accept_job(user, data):
    role(user, 'transporter')
    pk = integer(data.get('id'), 'Delivery')
    changed = Delivery.objects.filter(pk=pk, state='OPEN', transporter__isnull=True).update(transporter=user, state='ASSIGNED')
    ensure(changed == 1, 'This job was already accepted or is unavailable.')
    job = Delivery.objects.get(pk=pk)
    Order.objects.filter(pk=job.order_id).update(state='ASSIGNED')
    Checkpoint.objects.create(delivery=job, actor=user, state='ASSIGNED', note='Transporter accepted the job.')
    audit(user, f'order:{job.order_id}', 'job_accepted', delivery_id=job.pk)
    return {'message': 'Delivery job accepted.'}

def delivery_update(user, data):
    role(user, 'transporter')
    try:
        job = Delivery.objects.select_for_update().get(pk=integer(data.get('id'), 'Delivery'), transporter=user)
    except Delivery.DoesNotExist:
        raise NotFound('Assigned job not found.')
    next_state = data.get('state')
    if next_state == 'CHECKPOINT':
        ensure(job.state in ['PICKED_UP', 'IN_TRANSIT'], 'Checkpoints require goods in transit.')
        next_state = job.state
    else:
        ensure({'ASSIGNED': 'PICKED_UP', 'PICKED_UP': 'IN_TRANSIT', 'IN_TRANSIT': 'ARRIVED'}.get(job.state) == next_state,
               'Invalid delivery transition. Arrival does not confirm receipt.')
    lat = lng = None
    source = data.get('source', 'status-only')
    ensure(source in ['status-only', 'demo', 'consented-gps'], 'Invalid location source.')
    if source != 'status-only':
        ensure(data.get('consent') in [True, 'true', 'on'], 'Explicit consent is required to share coordinates.')
        try:
            lat, lng = float(data.get('latitude')), float(data.get('longitude'))
        except (ValueError, TypeError):
            raise ValidationError('Enter both valid coordinates.')
        ensure(math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180, 'Coordinates out of range.')
    job.state = next_state
    job.save()
    Order.objects.filter(pk=job.order_id).update(state=next_state)
    Checkpoint.objects.create(delivery=job, actor=user, state=next_state,
                               note=text(data.get('notes'), 'Checkpoint note'), latitude=lat, longitude=lng, source=source)
    audit(user, f'order:{job.order_id}', 'delivery_update', state=next_state, location_source=source)
    return {'message': 'Delivery checkpoint recorded.'}

def clean_photos(files):
    ensure(len(files) <= 4, 'At most four photos per receipt.')
    result = []
    for file in files:
        ensure(file.size <= 2*1024*1024, 'Each photo must be at most 2 MB.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                image = Image.open(file)
                ensure(image.format in ['JPEG', 'PNG', 'WEBP'], 'Use JPEG, PNG or WebP photos.')
                ensure(image.width*image.height <= 16000000, 'Photo dimensions are too large.')
                image.load()
                # Re-encode pixels to discard EXIF/GPS metadata and active/polyglot contents.
                image = image.convert('RGB')
                image.thumbnail((2000, 2000))
                out = io.BytesIO()
                image.save(out, format='JPEG', quality=85)
                result.append(out.getvalue())
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError):
            raise ValidationError('Invalid or unsafe image.')
    return result

def reconcile(user, data, files):
    role(user, 'supervisor')
    order = Order.objects.select_for_update().get(pk=get_order(user, integer(data.get('id'), 'Order')).pk)
    ensure(order.supervisor_id == user.pk, 'Only the assigned site supervisor can sign this receipt.')
    ensure(order.state == 'ARRIVED' and not Receipt.objects.filter(order=order).exists(), 'Only an arrived, unreconciled order can be receipted.')
    ensure(data.get('attest') in [True, 'true', 'on'], 'Confirm that you inspected the delivery.')
    lines = data.get('lines')
    if isinstance(lines, str):
        try:
            lines = json.loads(lines)
        except (ValueError, TypeError):
            raise ValidationError('Receipt lines must be valid JSON.')
    ensure(isinstance(lines, list) and all(isinstance(x, dict) for x in lines), 'Provide all receipt lines.')
    expected = {x.pk: x for x in order.lines.all()}
    ids = [integer(x.get('line'), 'Order line') for x in lines]
    ensure(len(ids) == len(set(ids)) and set(ids) == set(expected), 'Reconcile every ordered line exactly once.')
    validated = []
    discrepancy = False
    for row, pk in zip(lines, ids):
        received = integer(row.get('received'), 'Received quantity', 0, expected[pk].quantity)
        condition = row.get('condition')
        ensure(condition in ['good', 'damaged', 'missing'], 'Invalid condition.')
        ensure((condition == 'missing') == (received == 0), 'Use missing only for zero received quantity.')
        notes = text(row.get('notes', ''), 'Line notes', 500, False)
        issue = received != expected[pk].quantity or condition != 'good'
        ensure(not issue or notes, 'Explain every shortage or condition discrepancy.')
        discrepancy |= issue
        validated.append((pk, received, condition, notes))
    photos = clean_photos(files)
    receipt = Receipt.objects.create(order=order, supervisor=user, discrepancies=discrepancy,
                                       notes=text(data.get('notes', ''), 'Receipt notes', 2000, False))
    for pk, received, condition, notes in validated:
        ReceiptLine.objects.create(receipt=receipt, order_line_id=pk, received=received, condition=condition, notes=notes)
    for raw in photos:
        Photo.objects.create(receipt=receipt, image=ContentFile(raw, name='evidence.jpg'), sha256=hashlib.sha256(raw).hexdigest())
    order.state = 'DISPUTED' if discrepancy else 'RECEIVED'
    order.save()
    audit(user, f'order:{order.pk}', 'site_receipt_signed', receipt_id=receipt.pk, discrepancies=discrepancy,
           photo_hashes=list(receipt.photos.values_list('sha256', flat=True)))
    return {'receipt_id': receipt.pk, 'state': order.state}

def rental_range(data):
    try:
        start, end = parse_datetime(data.get('starts_at', '')), parse_datetime(data.get('ends_at', ''))
    except (ValueError, TypeError):
        raise ValidationError('Use valid ISO date-times.')
    ensure(start is not None and end is not None, 'Provide start and end date-times.')
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)
    ensure(start >= timezone.now()-timedelta(minutes=1) and end > start and end-start <= timedelta(days=366), 'Rental must start in the future and last at most 366 days.')
    return start, end

def capacity(listing, start, end):
    # Peak concurrent quantity, rather than summing disjoint bookings in the window.
    events = [(start, 0)]
    now = timezone.now()
    bookings = Rental.objects.filter(listing=listing, starts_at__lt=end).filter(
        Q(state__in=['BOOKED', 'COLLECTED'], ends_at__gt=start) | Q(state='COLLECTED', ends_at__lte=now))
    for r in bookings:
        effective_end = end if r.state == 'COLLECTED' and r.ends_at <= now else min(end, r.ends_at)
        events += [(max(start, r.starts_at), r.quantity), (effective_end, -r.quantity)]
    used = peak = 0
    for _, delta in sorted(events, key=lambda e: (e[0], e[1])):
        used += delta
        peak = max(peak, used)
    return max(0, listing.stock-peak)

def book_rental(user, data, preview=False):
    role(user, 'purchaser')
    try:
        listing = Listing.objects.select_for_update().select_related('supplier__profile').get(pk=integer(data.get('listing'), 'Listing'), kind='rental', active=True)
    except Listing.DoesNotExist:
        raise NotFound('Rental listing not found.')
    ensure(listing.supplier.is_active and listing.supplier.profile.verified, 'Supplier is not verified.')
    start, end = rental_range(data)
    available = capacity(listing, start, end)
    if preview:
        return {'available': available, 'billing_days': math.ceil((end-start).total_seconds()/86400)}
    qty = integer(data.get('quantity'), 'Quantity', 1, 10000)
    ensure(qty <= available, f'Only {available} units available for that range.')
    total = math.ceil((end-start).total_seconds()/86400)*listing.price_ngwee*qty
    rental = Rental.objects.create(listing=listing, purchaser=user, quantity=qty, starts_at=start, ends_at=end,
                                    rate_ngwee=listing.price_ngwee, total_ngwee=total, deposit_ngwee=listing.deposit_ngwee*qty,
                                    deposit_status='NOT_REQUIRED' if listing.deposit_ngwee == 0 else 'PENDING')
    audit(user, f'rental:{rental.pk}', 'rental_booked', total_ngwee=total, deposit_ngwee=rental.deposit_ngwee)
    return {'rental_id': rental.pk, 'total_ngwee': total, 'deposit_ngwee': rental.deposit_ngwee}

def rental_action(user, data):
    role(user, 'supplier', 'admin', 'purchaser')
    try:
        rental = Rental.objects.select_for_update().select_related('listing').get(pk=integer(data.get('id'), 'Rental'))
    except Rental.DoesNotExist:
        raise NotFound('Rental not found.')
    op = data.get('operation')
    if op == 'deposit':
        role(user, 'admin')
        ensure(rental.state == 'BOOKED' and rental.deposit_status == 'PENDING', 'No pending deposit exists.')
        rental.deposit_reference = text(data.get('reference'), 'Manual deposit reference', 120)
        rental.deposit_status = 'RECORDED_MANUAL'
    elif op == 'refund':
        role(user, 'admin')
        ensure(rental.deposit_status == 'REFUND_PENDING', 'No deposit refund is pending.')
        rental.deposit_reference = text(data.get('reference'), 'Manual refund reference', 120)
        rental.deposit_status = 'REFUNDED_MANUAL'
    elif op == 'cancel':
        ensure(user.pk == rental.purchaser_id and rental.state == 'BOOKED', 'Only purchaser can cancel a booked rental.')
        rental.state = 'CANCELLED'
        if rental.deposit_status == 'RECORDED_MANUAL':
            rental.deposit_status = 'REFUND_PENDING'
    else:
        role(user, 'supplier')
        ensure(rental.listing.supplier_id == user.pk, 'Only the equipment supplier can record collection or return.')
        if op == 'collect':
            ensure(rental.state == 'BOOKED' and rental.deposit_status in ['RECORDED_MANUAL', 'NOT_REQUIRED'], 'Record any deposit before collection.')
            ensure(rental.starts_at <= timezone.now() < rental.ends_at, 'Collection is allowed within the booked time range.')
            rental.state = 'COLLECTED'
        else:
            ensure(op == 'return' and rental.state == 'COLLECTED', 'Only collected rentals can be returned.')
            rental.return_condition = text(data.get('notes'), 'Return inspection / damage notes')
            rental.returned_at = timezone.now()
            rental.state = 'RETURNED'
            if rental.deposit_status == 'RECORDED_MANUAL':
                rental.deposit_status = 'REFUND_PENDING'
    rental.save()
    audit(user, f'rental:{rental.pk}', 'rental_'+str(op), state=rental.state, deposit_status=rental.deposit_status,
           condition=rental.return_condition, reference=rental.deposit_reference)
    return {'message': 'Rental updated.'}

def save_listing(user, data):
    role(user, 'supplier')
    kwargs = {'name': text(data.get('name'), 'Name', 120), 'unit': text(data.get('unit', 'each'), 'Unit', 24),
              'price_ngwee': integer(data.get('price_ngwee'), 'Unit price'), 'stock': integer(data.get('stock'), 'Stock', 0, 100000),
              'deposit_ngwee': integer(data.get('deposit_ngwee', 0), 'Deposit', 0)}
    if data.get('id'):
        try:
            listing = Listing.objects.select_for_update().get(pk=integer(data['id'], 'Listing'), supplier=user)
        except Listing.DoesNotExist:
            raise NotFound('Your listing was not found.')
        ensure(listing.kind != 'rental' or kwargs['stock'] == listing.stock or not Rental.objects.filter(listing=listing, state__in=['BOOKED', 'COLLECTED']).exists(), 'Rental capacity cannot change while active bookings exist.')
        for key, val in kwargs.items():
            setattr(listing, key, val)
        listing.save()
    else:
        ensure(data.get('kind') in ['sale', 'rental'], 'Choose sale or rental.')
        listing = Listing.objects.create(supplier=user, kind=data['kind'], **kwargs)
    audit(user, f'listing:{listing.pk}', 'listing_saved', **kwargs)
    return {'listing_id': listing.pk}

def payment(user, data):
    role(user, 'admin')
    order = Order.objects.select_for_update().get(pk=get_order(user, integer(data.get('id'), 'Order')).pk)
    reference = text(data.get('reference'), 'Manual payment / refund reference', 120)
    op = data.get('operation', 'record')
    ensure((op == 'record' and order.payment_status == 'PENDING' and order.state != 'REJECTED') or
           (op == 'refund' and order.payment_status == 'REFUND_PENDING'), 'Invalid payment state transition.')
    order.payment_status = 'RECORDED_MANUAL' if op == 'record' else 'REFUNDED_MANUAL'
    order.payment_reference = reference
    order.payment_recorded_by = user
    order.save()
    audit(user, f'order:{order.pk}', 'manual_payment_'+op, reference=reference, amount_ngwee=order.total_ngwee)
    return {'message': 'Manual bookkeeping recorded. No money was moved.'}

def message(user, data):
    order = get_order(user, integer(data.get('id'), 'Order'))
    Message.objects.create(order=order, author=user, text=text(data.get('text'), 'Message', 1000))
    audit(user, f'order:{order.pk}', 'message_sent')
    return {'message': 'Message saved to the order thread.'}

def verify(user, data):
    role(user, 'admin')
    try:
        profile = Profile.objects.select_for_update().get(user_id=integer(data.get('id'), 'Account'))
    except Profile.DoesNotExist:
        raise NotFound('Account not found.')
    ensure(profile.role != 'admin', 'Administrator verification cannot be changed here.')
    ensure(data.get('verified') in [True, False, 'true', 'false'], 'Choose verified or suspended.')
    profile.verified = data['verified'] in [True, 'true']
    profile.save()
    audit(user, f'user:{profile.user_id}', 'verification_changed', verified=profile.verified)
    return {'message': 'Account verification updated.'}

def account(user, data):
    role(user, 'admin')
    username = text(data.get('username'), 'Username', 80)
    ensure(re.fullmatch(r'[a-zA-Z0-9_]+', username), 'Use letters, numbers and underscores.')
    ensure(not User.objects.filter(username=username).exists(), 'Username already exists.')
    ensure(data.get('role') in ['purchaser', 'supplier', 'transporter', 'supervisor'], 'Invalid account role.')
    password = text(data.get('password'), 'Password', 128)
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages)
    created = User.objects.create_user(username=username, password=password)
    Profile.objects.create(user=created, role=data['role'], verified=False)
    audit(user, f'user:{created.pk}', 'account_created', role=data['role'])
    return {'message': 'Account created. Verify it after your checks.'}

@transaction.atomic
def dispatch(user, action, data, files=()):
    handlers = {'cart': add_cart, 'checkout': checkout, 'quote-request': request_quote, 'quote': quote_action,
                'supplier-order': supplier_order, 'accept-job': accept_job, 'delivery': delivery_update,
                'rental-book': book_rental, 'rental': rental_action, 'listing': save_listing,
                'payment': payment, 'message': message, 'verify': verify, 'account': account}
    if action == 'receipt':
        return reconcile(user, data, list(files))
    if action == 'rental-availability':
        return book_rental(user, data, preview=True)
    ensure(action in handlers, 'Unknown action.')
    return handlers[action](user, data)
