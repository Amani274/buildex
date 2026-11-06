"""Prototype fees, payment sandbox, support scope and location handling."""
import hashlib
import math
from datetime import timedelta
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import NotFound
from .models import (Storefront, Order, PaymentAttempt, Rental, Event, SupportTicket, TermsAcceptance,
                     CartItem, Listing, Delivery, Checkpoint,DemoBankAccount,Message)
from .services import ensure, role, integer, text, audit

TERMS_VERSION = 'prototype-2026-11-v2'
BANKS = {'absa-demo': 'Absa · simulation', 'zanaco-demo': 'Zanaco · simulation',
         'fnb-demo': 'FNB · simulation', 'stanbic-demo': 'Stanbic · simulation'}

def coordinates(data, required=False):
    a, b = data.get('latitude'), data.get('longitude')
    if a in [None, ''] and b in [None, ''] and not required:
        return -15.4067, 28.2871
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        ensure(False, 'Choose a valid site pin on the map.')
    ensure(math.isfinite(a) and math.isfinite(b) and -18.1 <= a <= -8.0 and 21.9 <= b <= 33.8,
           'Choose a delivery location in Zambia.')
    return a, b

def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [*a, *b])
    d = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371*2*math.atan2(math.sqrt(d), math.sqrt(max(0,1-d)))

def origin(supplier):
    store = Storefront.objects.filter(user=supplier).first()
    return (store.latitude, store.longitude) if store else (-15.415,28.28)

def fee_quote(supplier, items, destination):
    # Distances are planning approximations; no traffic/road-routing API is implied.
    km = round(distance(origin(supplier), destination)*1.35, 1)
    ensure(km <= 150, 'This local prototype supports deliveries within an estimated 150 km of the supplier.')
    weight = sum(max(0.1, l.weight_kg)*qty for l,qty,_ in items)
    subtotal = sum(qty*price for _,qty,price in items)
    transport = 'Motorbike / light parcel' if weight <= 20 else 'Pickup' if weight <= 1000 else 'Flatbed truck'
    trips = max(1, math.ceil(weight/5000))
    base = 3500 if weight <= 20 else 6500 if weight <= 1000 else 14000
    delivery = trips*(base + math.ceil(km*650))
    labour = 0 if weight <= 20 else 2500 + math.ceil(weight/250)*1500
    commission = (subtotal*5+50)//100
    return {'delivery_ngwee': delivery, 'labour_ngwee': labour, 'commission_ngwee': commission,
            'distance_km': km, 'eta_minutes': 25+math.ceil(km/30*60)+math.ceil(weight/500)*5,
            'transport_class': transport, 'fee_details': {'version':'demo-fees-v2', 'weight_kg':round(weight,1),
            'trips':trips,'commission_rate':0.05,'distance_basis':'straight-line × 1.35; no live traffic',
            'rates_basis':'BuildExchange simulation; not a supplier or transporter quote'}}

def estimate(user, data):
    role(user,'purchaser')
    dest = coordinates(data)
    groups = {}
    for line in CartItem.objects.filter(purchaser=user).select_related('listing__supplier'):
        groups.setdefault(line.listing.supplier_id,[]).append((line.listing,line.quantity,line.listing.price_ngwee))
    quotes=[]
    for rows in groups.values():
        supplier=rows[0][0].supplier
        subtotal=sum(q*p for _,q,p in rows)
        fees=fee_quote(supplier, rows, dest)
        quotes.append({'supplier_id':supplier.pk,'supplier':supplier.get_full_name() or supplier.username,
                       'subtotal_ngwee':subtotal, **fees,'total_ngwee':subtotal+sum(fees[k] for k in ['delivery_ngwee','labour_ngwee','commission_ngwee'])})
    return {'quotes':quotes,'total_ngwee':sum(q['total_ngwee'] for q in quotes)}

def terms(user, data):
    role(user,'purchaser','supplier','transporter','supervisor','admin')
    ensure(data.get('accept') in [True,'true','on'], 'Confirm the prototype terms.')
    TermsAcceptance.objects.get_or_create(user=user,version=TERMS_VERSION)
    return {'message':'Prototype terms accepted.'}

def payment_start(user, data):
    role(user,'purchaser')
    ensure(TermsAcceptance.objects.filter(user=user,version=TERMS_VERSION).exists(), 'Read and accept the prototype terms before payment.')
    key = text(data.get('key'),'Payment request key',80)
    method = data.get('bank')
    ensure(method in BANKS,'Choose a demo bank.')
    target=data.get('target','order')
    ensure(target in ['order','rental'],'Choose order or rental deposit.')
    pk=integer(data.get('id'),'Payment target')
    existing=PaymentAttempt.objects.filter(purchaser=user,key=key).first()
    if existing:
        ensure((existing.order_id if target=='order' else existing.rental_id)==pk and existing.bank_label==BANKS[method],
               'Payment key was used for another transaction.')
        return {'attempt_id':existing.pk,'url':f'/bank-sandbox/{existing.pk}/','replayed':True}
    if target=='order':
        try: record=Order.objects.select_for_update().get(pk=pk,purchaser=user)
        except Order.DoesNotExist:raise NotFound('Your order was not found.')
        ensure(record.state not in ['REJECTED','CANCELLED'] and record.payment_status=='PENDING','This order cannot be paid again.')
        amount=record.total_ngwee
    else:
        try:record=Rental.objects.select_for_update().get(pk=pk,purchaser=user)
        except Rental.DoesNotExist:raise NotFound('Your rental was not found.')
        ensure(record.state=='BOOKED' and record.payment_status=='PENDING','No rental payment is due.')
        amount=record.total_ngwee+record.deposit_ngwee
    # A bank session older than 15 minutes can no longer be approved, so retire it instead of trapping the buyer in it.
    PaymentAttempt.objects.filter(purchaser=user,state='PENDING',created_at__lt=timezone.now()-timedelta(minutes=15),**{target:record}).update(state='CANCELLED',completed_at=timezone.now())
    pending=PaymentAttempt.objects.filter(purchaser=user,state='PENDING',**{target:record}).first()
    if pending:
        return {'attempt_id':pending.pk,'url':f'/bank-sandbox/{pending.pk}/','replayed':True}
    attempt=PaymentAttempt.objects.create(purchaser=user,key=key,bank_label=BANKS[method],amount_ngwee=amount,**{target:record})
    DemoBankAccount.objects.get_or_create(user=user,bank_label=attempt.bank_label)
    audit(user,f'{target}:{pk}','bank_demo_initiated',attempt_id=attempt.pk,amount_ngwee=amount)
    return {'attempt_id':attempt.pk,'url':f'/bank-sandbox/{attempt.pk}/'}

def payment_decide(user,data):
    role(user,'purchaser')
    try:attempt=PaymentAttempt.objects.select_for_update().get(pk=integer(data.get('id'),'Transaction'),purchaser=user)
    except PaymentAttempt.DoesNotExist:raise NotFound('Your transaction was not found.')
    decision=data.get('decision')
    ensure(decision in ['approve','decline','cancel'],'Choose approve, decline or cancel.')
    if attempt.state!='PENDING':
        ensure((attempt.state=='SUCCEEDED')==(decision=='approve'),'This transaction has already been decided.')
        return {'state':attempt.state,'replayed':True}
    record = Order.objects.select_for_update().get(pk=attempt.order_id) if attempt.order_id else Rental.objects.select_for_update().get(pk=attempt.rental_id)
    if decision=='approve':
        ensure(attempt.created_at >= timezone.now()-timedelta(minutes=15), 'This demo bank session expired. Cancel it and start again.')
        account=DemoBankAccount.objects.select_for_update().get(user=user,bank_label=attempt.bank_label)
        ensure(account.balance_ngwee>=attempt.amount_ngwee,'Insufficient fictitious funds in this demo bank account. Cancel or choose another demo bank.')
        if attempt.order_id:
            ensure(record.state not in ['REJECTED','CANCELLED'] and record.payment_status=='PENDING','Order is no longer payable.')
            ensure(attempt.amount_ngwee==record.total_ngwee,'Transaction amount no longer matches the order.')
            record.payment_status='PAID_DEMO'
            record.payment_reference='SIM-'+str(attempt.reference).split('-')[0].upper()
        else:
            ensure(record.state=='BOOKED' and record.payment_status=='PENDING','Rental is no longer payable.')
            record.payment_status='PAID_DEMO'
            record.payment_reference='SIM-'+str(attempt.reference).split('-')[0].upper()
            record.deposit_status='PAID_DEMO' if record.deposit_ngwee else 'NOT_REQUIRED'
            record.deposit_reference='SIM-'+str(attempt.reference).split('-')[0].upper()
        record.save()
        account.balance_ngwee-=attempt.amount_ngwee;account.save(update_fields=['balance_ngwee'])
        attempt.state='SUCCEEDED'
    else:attempt.state='DECLINED' if decision=='decline' else 'CANCELLED'
    attempt.completed_at=timezone.now();attempt.save()
    target=f'order:{record.pk}' if attempt.order_id else f'rental:{record.pk}'
    audit(user,target,'bank_demo_'+attempt.state.lower(),reference=str(attempt.reference),amount_ngwee=attempt.amount_ngwee)
    return {'state':attempt.state,'reference':'SIM-'+str(attempt.reference).split('-')[0].upper(),
            'message':'Demo transaction completed. No bank was contacted and no money moved.'}

def open_ticket(user,data):
    from .services import get_order
    role(user,'purchaser','supplier','transporter','supervisor','admin')
    pk=integer(data.get('id'),'Order')
    if user.profile.role=='admin':
        # Support can open a case from an order number (for example a buyer who phones in); the case then brings the order into its desk.
        try:order=Order.objects.get(pk=pk)
        except Order.DoesNotExist:raise NotFound('No order with that number.')
    else:order=get_order(user,pk)
    ticket=SupportTicket.objects.create(order=order,opened_by=user,subject=text(data.get('subject'),'Subject',120),
                                        description=text(data.get('description'),'Issue',1500))
    audit(user,f'order:{order.pk}','support_requested',ticket_id=ticket.pk,by_support=user.profile.role=='admin')
    return {'message':'Case BX-'+str(ticket.pk)+(' opened for order BE-'+str(order.pk) if user.profile.role=='admin' else ' sent to customer support.')}

def cancel_order_record(order,actor,reason,support=False):
    """Cancel an order that has not been collected: release stock, clear unpaid bank sessions and refund a simulated payment once."""
    ensure(order.state in (['PLACED','ACCEPTED','READY'] if support else ['PLACED']),
           'This order can no longer be cancelled here.' if support else 'Orders can be cancelled only until the supplier accepts them.')
    job=getattr(order,'delivery',None)
    ensure(job is None or (job.transporter_id is None and job.state=='OPEN'),'A driver has already accepted this delivery.')
    ensure(order.payment_status!='RECORDED_MANUAL','This order has a manually recorded payment that must be settled outside the demo bank.')
    for line in order.lines.order_by('listing_id'):
        Listing.objects.filter(pk=line.listing_id).update(stock=F('stock')+line.quantity)
    PaymentAttempt.objects.filter(order=order,state='PENDING').update(state='CANCELLED',completed_at=timezone.now())
    refunded=order.payment_status=='PAID_DEMO'
    if refunded:
        refund_demo(order=order);order.payment_status='REFUNDED_DEMO'
    elif order.payment_status=='PENDING':order.payment_status='VOIDED'
    if job:
        job.state='CANCELLED';job.save(update_fields=['state'])
    order.state='CANCELLED';order.save()
    audit(actor,f'order:{order.pk}','order_cancelled',reason=reason,by_support=support,refunded=refunded)
    return refunded

def order_cancel(user,data):
    from .services import get_order
    role(user,'purchaser')
    order=Order.objects.select_for_update().get(pk=get_order(user,integer(data.get('id'),'Order')).pk)
    ensure(order.purchaser_id==user.pk,'Only the buyer can cancel this order.')
    refunded=cancel_order_record(order,user,text(data.get('reason',''),'Reason',500,False))
    return {'message':'Order cancelled and your simulated payment was refunded.' if refunded else 'Order cancelled. Nothing was charged.'}

def support_fix(user,data):
    """Targeted, audited repairs for orders that have a support case. Support still cannot shop, dispatch, edit prices or manage accounts."""
    from .services import get_order, supervisor_id
    role(user,'admin')
    order=Order.objects.select_for_update().get(pk=get_order(user,integer(data.get('id'),'Order')).pk)
    op=data.get('operation')
    ensure(op in ['cancel_order','reset_payment','change_supervisor','update_site'],'Choose a support fix.')
    reason=text(data.get('reason'),'Reason for the change',500)
    live=order.state not in ['CANCELLED','REJECTED','RECEIVED','DISPUTED']
    if op=='cancel_order':
        refunded=cancel_order_record(order,user,reason,support=True)
        note='cancelled this order'+(' and refunded the simulated payment.' if refunded else '. Nothing was charged.')
        result='Order cancelled'+(' and the simulated payment refunded.' if refunded else '.')
    elif op=='reset_payment':
        ensure(live and order.payment_status=='PENDING','There is no unpaid bank session to clear.')
        cleared=PaymentAttempt.objects.filter(order=order,state='PENDING').update(state='CANCELLED',completed_at=timezone.now())
        note='cleared the stuck bank session. You can choose Pay by bank again.'
        result='Bank session cleared. The buyer can start the payment again.' if cleared else 'No open bank session was found; the buyer can already pay again.'
    elif op=='change_supervisor':
        ensure(live and not hasattr(order,'receipt'),'The receiving supervisor can no longer be changed.')
        new=supervisor_id(integer(data.get('supervisor'),'Supervisor'))
        order.supervisor_id=new;order.save(update_fields=['supervisor'])
        note='changed who receives this delivery on site.'
        result='Receiving supervisor changed.'
    else:
        ensure(live and not hasattr(order,'receipt'),'The site details can no longer be changed.')
        order.site=text(data.get('site'),'Site address / landmark',240);order.save(update_fields=['site'])
        note='corrected the site address or landmark. The map pin is unchanged.'
        result='Site details updated.'
    Message.objects.create(order=order,author=user,text='Customer support '+note+' Reason: '+reason)
    audit(user,f'order:{order.pk}','support_fix',operation=op,reason=reason)
    return {'message':result}

def support_reply(user,data):
    role(user,'admin')
    try:ticket=SupportTicket.objects.select_for_update().get(pk=integer(data.get('id'),'Support case'))
    except SupportTicket.DoesNotExist:raise NotFound('Support case was not found.')
    ticket.response=text(data.get('response'),'Support response',1500)
    ensure(data.get('state') in ['OPEN','IN_REVIEW','RESOLVED'],'Choose a valid case status.')
    ticket.state=data['state'];ticket.responded_by=user;ticket.save()
    audit(user,f'order:{ticket.order_id}','support_case_updated',ticket_id=ticket.pk,state=ticket.state)
    return {'message':'Customer-support response saved.'}

def location_update(user,data):
    role(user,'transporter')
    try:job=Delivery.objects.select_for_update().get(pk=integer(data.get('id'),'Delivery'),transporter=user)
    except Delivery.DoesNotExist:raise NotFound('Your assigned delivery was not found.')
    ensure(job.state in ['ASSIGNED','PICKED_UP','IN_TRANSIT'],'Location sharing is available only for an active job.')
    ensure(data.get('consent') in [True,'true','on'],'Consent is required before sharing location.')
    source=data.get('source')
    ensure(source in ['demo','consented-gps'],'Choose demo or consented GPS.')
    lat,lng=coordinates(data,required=True)
    if source=='demo':
        ensure(data.get('purpose')=='route-rehearsal','Demo locations must be labelled route rehearsals.')
    point=Checkpoint.objects.create(delivery=job,actor=user,state=job.state,note='Simulated vehicle position' if source=='demo' else 'Consented device location',latitude=lat,longitude=lng,source=source)
    return {'point_id':point.pk,'source':source,'created_at':point.created_at.isoformat()}

def supplier_refund(user,data):
    role(user,'supplier')
    try:order=Order.objects.select_for_update().get(pk=integer(data.get('id'),'Order'),supplier=user)
    except Order.DoesNotExist:raise NotFound('Your order was not found.')
    ensure(order.state=='REJECTED' and order.payment_status=='REFUND_PENDING','No rejected-order refund is pending.')
    refund_demo(order=order)
    order.payment_status='REFUNDED_DEMO';order.save()
    audit(user,f'order:{order.pk}','demo_refund_recorded',amount_ngwee=order.total_ngwee)
    return {'message':'Simulated refund recorded. No money moved.'}

def refund_demo(order=None,rental=None,amount=None):
    target={'order':order} if order else {'rental':rental}
    for attempt in PaymentAttempt.objects.select_for_update().filter(state__in=['SUCCEEDED','PARTIALLY_REFUNDED'],**target):
        account=DemoBankAccount.objects.select_for_update().get(user=attempt.purchaser,bank_label=attempt.bank_label)
        credit=min(attempt.amount_ngwee-attempt.refunded_ngwee,amount if amount is not None else attempt.amount_ngwee)
        account.balance_ngwee+=credit;account.save(update_fields=['balance_ngwee'])
        attempt.refunded_ngwee+=credit
        attempt.state='REFUNDED' if attempt.refunded_ngwee==attempt.amount_ngwee else 'PARTIALLY_REFUNDED'
        attempt.save(update_fields=['state','refunded_ngwee'])
