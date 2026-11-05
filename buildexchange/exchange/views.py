from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from django.db.models import Q
from . import services as s
from .models import Listing, CartItem, Quote, Order, Delivery, Rental, Event, Photo, Profile

@login_required
@ensure_csrf_cookie
def home(request):
    return render(request, 'exchange/home.html')

def time(value):
    return value.isoformat() if value else None

def serialize_order(o):
    job = getattr(o, 'delivery', None)
    receipt = getattr(o, 'receipt', None)
    return {'id': o.pk, 'supplier': o.supplier.username, 'purchaser': o.purchaser.username,
            'supervisor': o.supervisor.username, 'site': o.site, 'state': o.state, 'total_ngwee': o.total_ngwee,
            'payment_status': o.payment_status, 'payment_reference': o.payment_reference, 'created_at': time(o.created_at),
            'lines': list(o.lines.values('id', 'name', 'quantity', 'unit', 'unit_price_ngwee')),
            'delivery': {'id': job.pk, 'state': job.state, 'transporter': job.transporter.username if job.transporter else None,
                         'checkpoints': [{'state': c.state, 'note': c.note, 'latitude': c.latitude, 'longitude': c.longitude,
                                          'source': c.source, 'created_at': time(c.created_at)} for c in job.checkpoints.all()]} if job else None,
            'receipt': {'id': receipt.pk, 'discrepancies': receipt.discrepancies, 'created_at': time(receipt.created_at),
                        'notes': receipt.notes, 'lines': list(receipt.lines.values('order_line_id', 'received', 'condition', 'notes')),
                        'photos': [{'url': f'/evidence/{p.pk}/', 'sha256': p.sha256} for p in receipt.photos.all()]} if receipt else None,
            'messages': [{'author': m.author.username, 'text': m.text, 'created_at': time(m.created_at)} for m in o.messages.select_related('author').order_by('id')],
            'events': [{'action': e.action, 'actor': e.actor.username, 'detail': e.detail, 'created_at': time(e.created_at)}
                       for e in Event.objects.filter(target=f'order:{o.pk}').select_related('actor')]}

@api_view(['GET'])
def state(request):
    user = request.user
    s.role(user, 'purchaser', 'supplier', 'transporter', 'supervisor', 'admin')
    r = user.profile.role
    listings = Listing.objects.filter(active=True, supplier__is_active=True, supplier__profile__verified=True).select_related('supplier')
    quotes = Quote.objects.select_related('listing', 'purchaser').all()
    rentals = Rental.objects.select_related('listing__supplier', 'purchaser').all()
    if r != 'admin':
        quotes = quotes.filter(Q(purchaser=user) | Q(listing__supplier=user))
        rentals = rentals.filter(Q(purchaser=user) | Q(listing__supplier=user))
    orders = s.order_scope(user).select_related('purchaser', 'supplier', 'supervisor', 'delivery__transporter', 'receipt').prefetch_related('lines')
    return Response({'me': {'id': user.pk, 'username': user.username, 'role': r},
        'listings': [{'id': l.pk, 'supplier_id': l.supplier_id, 'supplier': l.supplier.username, 'name': l.name,
                      'kind': l.kind, 'unit': l.unit, 'price_ngwee': l.price_ngwee, 'stock': l.stock, 'deposit_ngwee': l.deposit_ngwee} for l in listings],
        'supervisors': list(User.objects.filter(profile__role='supervisor', profile__verified=True, is_active=True).values('id', 'username')),
        'cart': list(CartItem.objects.filter(purchaser=user).values('listing_id', 'quantity')) if r == 'purchaser' else [],
        'orders': [serialize_order(o) for o in orders.order_by('-id')],
        'quotes': [{'id': q.pk, 'listing': q.listing.name, 'quantity': q.quantity, 'purchaser': q.purchaser.username,
                    'supplier': q.listing.supplier.username, 'state': q.state, 'unit_price_ngwee': q.unit_price_ngwee,
                    'notes': q.notes, 'response': q.response} for q in quotes.order_by('-id')],
        'rentals': [{'id': x.pk, 'name': x.listing.name, 'supplier': x.listing.supplier.username,
                     'purchaser': x.purchaser.username, 'quantity': x.quantity, 'starts_at': time(x.starts_at),
                     'ends_at': time(x.ends_at), 'state': x.state, 'total_ngwee': x.total_ngwee,
                     'deposit_ngwee': x.deposit_ngwee, 'deposit_status': x.deposit_status,
                     'return_condition': x.return_condition, 'returned_at': time(x.returned_at)} for x in rentals.order_by('-id')],
        # Open job board reveals no purchaser identity, precise site or communications before acceptance.
        'jobs': [{'id': d.pk, 'order_id': d.order_id, 'supplier': d.order.supplier.username,
                   'materials': list(d.order.lines.values('name', 'quantity', 'unit'))}
                  for d in Delivery.objects.filter(state='OPEN').select_related('order__supplier')] if r == 'transporter' else [],
        'accounts': list(Profile.objects.select_related('user').values('user_id', 'user__username', 'role', 'verified')) if r == 'admin' else [],
        'audit': [{'id': e.pk, 'actor': e.actor.username, 'target': e.target, 'action': e.action,
                    'detail': e.detail, 'created_at': time(e.created_at)} for e in Event.objects.select_related('actor').order_by('-id')[:200]] if r == 'admin' else []})

@api_view(['POST'])
def action(request, action):
    try:
        result = s.dispatch(request.user, action, request.data, request.FILES.getlist('photos'))
    except (TypeError, ValueError, OverflowError):
        raise ValidationError('Invalid input. Check the submitted fields.')
    return Response(result)

@login_required
def receipt_document(request, order_id):
    try:
        o = s.get_order(request.user, order_id)
    except APIException as exc:
        return HttpResponse('Receipt not available to this account.', status=exc.status_code)
    if not hasattr(o, 'receipt'):
        raise Http404('No signed receipt exists.')
    return render(request, 'exchange/receipt.html', {'order': o, 'receipt': o.receipt,
                  'total_zmw': f'{o.total_ngwee/100:.2f}', 'events': Event.objects.filter(target=f'order:{o.pk}').select_related('actor')})

@login_required
def evidence(request, photo_id):
    photo = get_object_or_404(Photo.objects.select_related('receipt__order'), pk=photo_id)
    try:
        s.get_order(request.user, photo.receipt.order_id)
    except APIException as exc:
        return HttpResponse('Evidence not available to this account.', status=exc.status_code)
    response = FileResponse(photo.image.open('rb'), content_type='image/jpeg')
    response['Content-Disposition'] = 'inline; filename="receipt-evidence.jpg"'
    response['Cache-Control'] = 'private, no-store'
    return response
