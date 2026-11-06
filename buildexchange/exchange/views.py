from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from django.db.models import Q
from django.utils import timezone
from collections.abc import Mapping
from . import services as s
from . import operations as ops
from .models import (Listing, CartItem, Quote, Order, Delivery, Rental, Event, Photo, Storefront,
                     PaymentAttempt, SupportTicket, TermsAcceptance,DemoBankAccount)

@login_required
@ensure_csrf_cookie
def home(request):
    return render(request,'exchange/home.html')

def time(value):return value.isoformat() if value else None
def name(user):return user.get_full_name() or user.profile.business_name or user.username

def store_data(store):
    now=timezone.localtime();hours=store.hours.get(str(now.weekday()));status='Hours to confirm'
    if hours:
        clock=now.strftime('%H:%M')
        status=('Open · closes '+hours[1]) if hours[0] <= clock < hours[1] else 'Closed · opens '+hours[0]
    elif store.hours:status='Closed today'
    if store.hours_basis=='directory snapshot':status+=' · confirm'
    return {'id':store.user_id,'slug':store.slug,'name':store.name,'focus':store.focus,'group':store.group,
            'address':store.address,'latitude':store.latitude,'longitude':store.longitude,'hours':store.hours,
            'hours_basis':store.hours_basis,'hours_source_url':store.hours_source_url or store.source_url,'status':status,'source_url':store.source_url,
            'catalogue_url':store.catalogue_url,'verified_on':str(store.verified_on),
            'pin_basis':'Approximate area pin; confirm pickup entrance','affiliation':'Research-based demo storefront; not an onboarded partner'}

def serialize_order(o,user):
    job=getattr(o,'delivery',None);receipt=getattr(o,'receipt',None);r=user.profile.role
    points=list(job.checkpoints.order_by('-id')[:100])[::-1] if job else []
    result={'id':o.pk,'supplier':o.supplier.username,'supplier_name':name(o.supplier),
            'purchaser':o.purchaser.username,'purchaser_name':name(o.purchaser),
            'supervisor':o.supervisor.username,'site':o.site,'latitude':o.site_latitude,'longitude':o.site_longitude,
            'location_source':o.location_source,'origin':ops.origin(o.supplier),'state':o.state,'created_at':time(o.created_at),
            'eta_minutes':o.eta_minutes,'distance_km':o.distance_km,'transport_class':o.transport_class,
            'lines':list(o.lines.values('id','name','quantity','unit')),
            'delivery':{'id':job.pk,'state':job.state,'transporter':name(job.transporter) if job.transporter else None,
                        'transporter_username':job.transporter.username if job.transporter else None,
                        'checkpoints':[{'state':c.state,'note':c.note,'latitude':c.latitude,'longitude':c.longitude,
                                        'source':c.source,'created_at':time(c.created_at)} for c in points]} if job else None,
            'receipt':{'id':receipt.pk,'discrepancies':receipt.discrepancies,'created_at':time(receipt.created_at),
                       'notes':receipt.notes,'lines':list(receipt.lines.values('order_line_id','received','condition','notes')),
                       'photos':[{'url':f'/evidence/{p.pk}/'} for p in receipt.photos.all()]} if receipt else None,
            'messages':[{'author':name(m.author),'text':m.text,'created_at':time(m.created_at)} for m in o.messages.select_related('author').order_by('id')],
            'support':[{'id':t.pk,'subject':t.subject,'state':t.state,'response':t.response} for t in o.support_tickets.order_by('-id')]}
    if r in ['purchaser','supplier']:
        result.update({'subtotal_ngwee':o.subtotal_ngwee,'total_ngwee':o.total_ngwee,'payment_status':o.payment_status,
                       'payment_reference':o.payment_reference,'delivery_ngwee':o.delivery_ngwee,'labour_ngwee':o.labour_ngwee,
                       'commission_ngwee':o.commission_ngwee,'unit_prices':{l.pk:l.unit_price_ngwee for l in o.lines.all()}})
    if r=='transporter':result.update({'delivery_ngwee':o.delivery_ngwee,'labour_ngwee':o.labour_ngwee})
    # Support sees the payment status (not amounts or references) so it knows whether a refund applies.
    if r=='admin':result.update({'payment_status':o.payment_status,'has_receipt':receipt is not None})
    return result

@api_view(['GET'])
def state(request):
    user=request.user;s.role(user,'purchaser','supplier','transporter','supervisor','admin');r=user.profile.role
    stores=Storefront.objects.select_related('user').all()
    listings=Listing.objects.filter(active=True,supplier__is_active=True,supplier__profile__verified=True).select_related('supplier')
    if r=='supplier':listings=listings.filter(supplier=user)
    elif r=='purchaser':listings=listings.filter(Q(catalogue_key__isnull=False)|Q(kind='rental'))
    else:listings=listings.none()
    quotes=Quote.objects.select_related('listing__supplier','purchaser').filter(Q(purchaser=user)|Q(listing__supplier=user))
    rentals=Rental.objects.select_related('listing__supplier','purchaser').filter(Q(purchaser=user)|Q(listing__supplier=user))
    orders=s.order_scope(user).select_related('purchaser__profile','supplier__profile','supervisor','delivery__transporter__profile','receipt').prefetch_related('lines')
    tickets=SupportTicket.objects.select_related('opened_by__profile','order').all() if r=='admin' else SupportTicket.objects.none()
    attempts=PaymentAttempt.objects.filter(purchaser=user).order_by('-id')[:30] if r=='purchaser' else []
    return Response({'me':{'id':user.pk,'username':user.username,'name':name(user),'role':r},
        'terms_version':ops.TERMS_VERSION,'terms_accepted':TermsAcceptance.objects.filter(user=user,version=ops.TERMS_VERSION).exists(),
        'stores':[store_data(x) for x in stores] if r=='purchaser' else [],
        'listings':[{'id':l.pk,'supplier_id':l.supplier_id,'supplier':l.supplier.username,'supplier_name':name(l.supplier),
                     'name':l.name,'kind':l.kind,'unit':l.unit,'price_ngwee':l.price_ngwee,'stock':l.stock,
                     'deposit_ngwee':l.deposit_ngwee,'category':l.category,'image_key':l.image_key,
                     'source_url':l.source_url,'price_basis':l.price_basis} for l in listings],
        'supervisors':list(User.objects.filter(profile__role='supervisor',profile__verified=True,is_active=True).values('id','username')) if r in ['purchaser','admin'] else [],
        'cart':list(CartItem.objects.filter(purchaser=user).values('listing_id','quantity')) if r=='purchaser' else [],
        'orders':[serialize_order(o,user) for o in orders.order_by('-id')],
        'quotes':[{'id':q.pk,'listing':q.listing.name,'quantity':q.quantity,'purchaser':q.purchaser.username,
                   'supplier':q.listing.supplier.username,'supplier_name':name(q.listing.supplier),'state':q.state,
                   'unit_price_ngwee':q.unit_price_ngwee,'notes':q.notes,'response':q.response} for q in quotes.order_by('-id')] if r in ['supplier','purchaser'] else [],
        'rentals':[{'id':x.pk,'name':x.listing.name,'supplier':x.listing.supplier.username,'supplier_name':name(x.listing.supplier),
                    'purchaser':x.purchaser.username,'quantity':x.quantity,'starts_at':time(x.starts_at),'ends_at':time(x.ends_at),
                    'state':x.state,'total_ngwee':x.total_ngwee,'deposit_ngwee':x.deposit_ngwee,'deposit_status':x.deposit_status,'payment_status':x.payment_status,
                    'return_condition':x.return_condition,'returned_at':time(x.returned_at)} for x in rentals.order_by('-id')] if r in ['supplier','purchaser'] else [],
        'payments':[{'id':p.pk,'order_id':p.order_id,'rental_id':p.rental_id,'amount_ngwee':p.amount_ngwee,'state':p.state,
                     'bank':p.bank_label,'refunded_ngwee':p.refunded_ngwee,'reference':'SIM-'+str(p.reference).split('-')[0].upper(),'created_at':time(p.created_at)} for p in attempts],
        'jobs':[{'id':d.pk,'order_id':d.order_id,'supplier':name(d.order.supplier),'transport_class':d.order.transport_class,
                 'distance_km':d.order.distance_km,'delivery_ngwee':d.order.delivery_ngwee,'labour_ngwee':d.order.labour_ngwee,
                 'materials':list(d.order.lines.values('name','quantity','unit'))} for d in Delivery.objects.filter(state='OPEN').select_related('order__supplier__profile')] if r=='transporter' else [],
        'tickets':[{'id':t.pk,'order_id':t.order_id,'opened_by':name(t.opened_by),'subject':t.subject,'description':t.description,
                    'state':t.state,'response':t.response,'created_at':time(t.created_at)} for t in tickets.order_by('-id')]})

@api_view(['POST'])
def action(request,action):
    if not isinstance(request.data,Mapping):
        raise ValidationError('Submit an object containing the requested fields.')
    try:result=s.dispatch(request.user,action,request.data,request.FILES.getlist('photos'))
    except (TypeError,ValueError,OverflowError):raise ValidationError('Check the entered values and try again.')
    return Response(result)

@api_view(['GET'])
def tracking(request,order_id):
    return Response(serialize_order(s.get_order(request.user,order_id),request.user))

@login_required
def receipt_document(request,order_id):
    try:o=s.get_order(request.user,order_id)
    except APIException as exc:return HttpResponse('Receipt not available to this account.',status=exc.status_code)
    if not hasattr(o,'receipt'):raise Http404('No signed receipt exists.')
    return render(request,'exchange/receipt.html',{'order':o,'receipt':o.receipt,'total_zmw':f'{o.total_ngwee/100:.2f}'})

@login_required
def evidence(request,photo_id):
    photo=get_object_or_404(Photo.objects.select_related('receipt__order'),pk=photo_id)
    try:s.get_order(request.user,photo.receipt.order_id)
    except APIException as exc:return HttpResponse('Evidence not available to this account.',status=exc.status_code)
    response=FileResponse(photo.image.open('rb'),content_type='image/jpeg')
    response['Content-Disposition']='inline; filename="site-inspection.jpg"';response['Cache-Control']='private, no-store'
    return response

def terms_page(request):return render(request,'exchange/terms.html',{'version':ops.TERMS_VERSION})

@login_required
@ensure_csrf_cookie
def bank_sandbox(request,attempt_id):
    try:s.role(request.user,'purchaser')
    except APIException as exc:return HttpResponse('Only the purchasing account can view its demo bank session.',status=exc.status_code)
    attempt=get_object_or_404(PaymentAttempt,pk=attempt_id,purchaser=request.user)
    account,_=DemoBankAccount.objects.get_or_create(user=request.user,bank_label=attempt.bank_label)
    return render(request,'exchange/bank.html',{'attempt':attempt,'amount':f'{attempt.amount_ngwee/100:,.2f}',
                  'balance':f'{account.balance_ngwee/100:,.2f}','refund':f'{attempt.refunded_ngwee/100:,.2f}',
                  'reference':'SIM-'+str(attempt.reference).split('-')[0].upper()})
