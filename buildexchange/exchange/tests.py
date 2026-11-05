import io
import json
import uuid
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from django.test import TestCase, override_settings, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import Profile, Listing, Order, Quote, Rental, Receipt, Photo, Event, CartItem
from . import services as s

class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(DEBUG=True):
            call_command('seed_demo', verbosity=0)
    def setUp(self):
        self.client = APIClient()
        self.users = {u.username:u for u in User.objects.all()}
        self.cement = Listing.objects.get(name='Cement 50 kg')
        self.sheets = Listing.objects.get(name='Roofing sheets')
        self.generator = Listing.objects.get(name='5 kVA generator')
    def post(self, who, action, data, status=200, format='json'):
        self.client.force_authenticate(user=self.users[who])
        response = self.client.post(f'/api/action/{action}/', data, format=format)
        self.assertEqual(response.status_code, status, response.content[:1000])
        return response.json()
    def new_order(self, qty=10, key='test-checkout-key-1'):
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':qty})
        ids=self.post('buyer','checkout',{'key':key,'site':'Demo site, Lusaka landmark A',
                                         'supervisor':self.users['supervisor'].pk})['order_ids']
        self.pay_demo('buyer','order',ids[0])
        return Order.objects.get(pk=ids[0])
    def pay_demo(self, who, target, pk, decision='approve'):
        self.post(who,'terms',{'accept':True})
        attempt=self.post(who,'payment-start',{'id':pk,'target':target,'bank':'absa-demo','key':uuid.uuid4().hex})
        return self.post(who,'payment-decide',{'id':attempt['attempt_id'],'decision':decision})
    def ready(self, order):
        self.post('supplier','supplier-order',{'id':order.pk,'operation':'ACCEPTED'})
        self.post('supplier','supplier-order',{'id':order.pk,'operation':'READY'})
        order.refresh_from_db()
        return order.delivery
    def arrive(self, order):
        job=self.ready(order)
        self.post('driver','accept-job',{'id':job.pk})
        for state in ['PICKED_UP','IN_TRANSIT','ARRIVED']:
            self.post('driver','delivery',{'id':job.pk,'state':state,'notes':'Verified demo checkpoint','source':'status-only'})
        order.refresh_from_db()
        self.assertEqual(order.state,'ARRIVED')
        self.assertFalse(Receipt.objects.filter(order=order).exists())
        return job
    def receipt_data(self, order, quantity=None):
        return {'id':order.pk,'attest':True,'notes':'Site inspection completed',
                'lines':[{'line':line.pk,'received':line.quantity if quantity is None else quantity,
                          'condition':'good','notes':'Two missing bags' if quantity is not None else ''} for line in order.lines.all()]}
    def rental_data(self, qty=1, start=None, end=None):
        start=start or timezone.now()+timedelta(hours=1)
        end=end or start+timedelta(days=1)
        return {'listing':self.generator.pk,'quantity':qty,'starts_at':start.isoformat(),'ends_at':end.isoformat()}

    def test_multi_vendor_checkout_and_replay(self):
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':10})
        self.post('buyer','cart',{'listing':self.sheets.pk,'quantity':4})
        data={'key':'multi-vendor-checkout','site':'Lusaka test site','supervisor':self.users['supervisor'].pk}
        result=self.post('buyer','checkout',data)
        self.assertEqual(len(result['order_ids']),2)
        self.assertEqual(self.post('buyer','checkout',data)['order_ids'],result['order_ids'])
        self.assertEqual(Order.objects.count(),2)
        self.cement.refresh_from_db();self.assertEqual(self.cement.stock,190)
        self.assertFalse(CartItem.objects.exists())
        self.post('buyer','checkout',{**data,'site':'Different site'},400)

    def test_full_procurement_delivery_and_discrepancy_receipt(self):
        o=self.new_order()
        self.post('admin','payment',{'id':o.pk,'reference':'DEMO-MANUAL-001'},403)
        self.arrive(o)
        self.post('buyer','message',{'id':o.pk,'text':'Please inspect every bag.'})
        result=self.post('supervisor','receipt',self.receipt_data(o,8))
        self.assertEqual(result['state'],'DISPUTED')
        o.refresh_from_db();self.assertEqual(o.payment_status,'PAID_DEMO')
        self.assertEqual(o.receipt.lines.get().received,8)
        self.assertTrue(Event.objects.filter(target=f'order:{o.pk}',action='site_receipt_signed').exists())
        self.client.force_login(self.users['buyer'])
        self.assertContains(self.client.get(f'/receipt/{o.pk}/'),'Two missing bags')

    def test_good_receipt_and_duplicate_signature_blocked(self):
        o=self.new_order();self.arrive(o)
        self.assertEqual(self.post('supervisor','receipt',self.receipt_data(o))['state'],'RECEIVED')
        self.post('supervisor','receipt',self.receipt_data(o),400)
        self.assertEqual(Receipt.objects.count(),1)

    def test_supervisor_and_transporter_cannot_forge_receipt(self):
        o=self.new_order();self.arrive(o)
        self.post('driver','receipt',self.receipt_data(o),403)
        self.post('supervisor2','receipt',self.receipt_data(o),404)
        self.post('buyer','receipt',self.receipt_data(o),403)

    def test_receipt_must_cover_every_line_and_explain_shortage(self):
        o=self.new_order();self.arrive(o)
        data=self.receipt_data(o)
        self.post('supervisor','receipt',{**data,'lines':[]},400)
        self.post('supervisor','receipt',{**data,'lines':data['lines']*2},400)
        data['lines'][0]['received']=9
        self.post('supervisor','receipt',data,400)
        self.assertFalse(Receipt.objects.exists())

    def test_stock_failure_rolls_back_entire_checkout(self):
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':10})
        self.post('buyer','cart',{'listing':self.sheets.pk,'quantity':5})
        Listing.objects.filter(pk=self.sheets.pk).update(stock=0)
        self.post('buyer','checkout',{'key':'out-of-stock-test','site':'Test site','supervisor':self.users['supervisor'].pk},400)
        self.assertFalse(Order.objects.exists())
        self.cement.refresh_from_db();self.assertEqual(self.cement.stock,200)
        self.assertEqual(CartItem.objects.count(),2)

    def test_unauthorized_reads_and_writes_are_denied(self):
        o=self.new_order()
        self.post('supplier2','supplier-order',{'id':o.pk,'operation':'ACCEPTED'},404)
        self.post('buyer','listing',{'id':self.cement.pk},403)
        self.post('supplier2','listing',{'id':self.cement.pk,'name':'Hijacked','unit':'bag','price_ngwee':1,'stock':1},404)
        self.post('buyer','payment',{'id':o.pk,'reference':'fake'},403)
        self.client.force_authenticate(user=self.users['driver'])
        self.assertEqual(self.client.get('/api/state/').json()['orders'],[])

    def test_job_acceptance_cannot_be_stolen(self):
        o=self.new_order();job=self.ready(o)
        self.post('driver','accept-job',{'id':job.pk})
        self.post('driver2','accept-job',{'id':job.pk},400)
        self.post('driver2','delivery',{'id':job.pk,'state':'PICKED_UP','notes':'fake'},404)
        self.post('driver','delivery',{'id':job.pk,'state':'ARRIVED','notes':'Skip pickup'},400)

    def test_coordinate_consent_and_demo_source(self):
        o=self.new_order();job=self.ready(o);self.post('driver','accept-job',{'id':job.pk})
        data={'id':job.pk,'state':'PICKED_UP','notes':'Demo pin','source':'demo','latitude':-15.4,'longitude':28.3}
        self.post('driver','delivery',data,400)
        self.post('driver','delivery',{**data,'consent':True,'latitude':'NaN'},400)
        self.post('driver','delivery',{**data,'consent':True})
        self.assertEqual(job.checkpoints.order_by('-pk').first().source,'demo')

    def test_quote_request_reply_accept_with_negotiated_price(self):
        qid=self.post('buyer','quote-request',{'listing':self.cement.pk,'quantity':12,'notes':'Bulk rate please'})['quote_id']
        self.post('supplier2','quote',{'id':qid,'operation':'reply','price_ngwee':15000},400)
        self.post('supplier','quote',{'id':qid,'operation':'reply','price_ngwee':15000,'notes':'Bulk offer'})
        data={'id':qid,'operation':'accept','site':'Test construction site','supervisor':self.users['supervisor'].pk}
        ids=self.post('buyer','quote',data)['order_ids']
        self.assertEqual(Order.objects.get(pk=ids[0]).subtotal_ngwee,180000)
        self.assertEqual(self.post('buyer','quote',data)['order_ids'],ids)
        self.assertEqual(Order.objects.count(),1)

    def test_rejection_releases_stock_once_and_payment_needs_manual_refund(self):
        o=self.new_order();self.post('admin','payment',{'id':o.pk,'reference':'Manual test'},403)
        self.post('supplier','supplier-order',{'id':o.pk,'operation':'REJECTED','notes':'Cannot supply today'})
        self.post('supplier','supplier-order',{'id':o.pk,'operation':'REJECTED','notes':'Again'},400)
        self.cement.refresh_from_db();self.assertEqual(self.cement.stock,200)
        o.refresh_from_db();self.assertEqual(o.payment_status,'REFUND_PENDING')
        self.post('supplier','supplier-refund',{'id':o.pk})
        o.refresh_from_db();self.assertEqual(o.payment_status,'REFUNDED_DEMO')

    def test_rental_overlap_boundary_and_availability(self):
        data=self.rental_data(qty=2)
        self.post('buyer','rental-book',data)
        self.post('buyer','rental-book',data,400)
        self.assertEqual(self.post('buyer','rental-availability',data)['available'],0)
        end=timezone.datetime.fromisoformat(data['ends_at'])
        self.post('buyer','rental-book',self.rental_data(qty=2,start=end,end=end+timedelta(days=1)))
        self.assertEqual(Rental.objects.count(),2)

    def test_peak_capacity_does_not_sum_disjoint_bookings(self):
        start=timezone.now()+timedelta(hours=1)
        self.post('buyer','rental-book',self.rental_data(1,start,start+timedelta(hours=1)))
        self.post('buyer','rental-book',self.rental_data(1,start+timedelta(hours=1),start+timedelta(hours=2)))
        result=self.post('buyer','rental-availability',self.rental_data(1,start,start+timedelta(hours=2)))
        self.assertEqual(result['available'],1)

    def test_rental_deposit_collection_return_and_refund(self):
        data=self.rental_data();rid=self.post('buyer','rental-book',data)['rental_id']
        self.post('supplier2','rental',{'id':rid,'operation':'collect'},400)
        self.pay_demo('buyer','rental',rid)
        rental=Rental.objects.get(pk=rid)
        with patch('exchange.services.timezone.now',return_value=rental.starts_at+timedelta(minutes=1)):
            self.post('supplier2','rental',{'id':rid,'operation':'collect'})
        self.post('supplier2','rental',{'id':rid,'operation':'return','notes':'Inspected: working, clean, full accessories'})
        rental.refresh_from_db();self.assertEqual(rental.deposit_status,'REFUNDED_DEMO')
        self.post('admin','rental',{'id':rid,'operation':'refund','reference':'DEMO-REFUND'},403)
        rental.refresh_from_db();self.assertEqual(rental.deposit_status,'REFUNDED_DEMO')
        self.assertIsNotNone(rental.returned_at)

    def test_rental_cancellation_releases_capacity(self):
        data=self.rental_data(qty=2);rid=self.post('buyer','rental-book',data)['rental_id']
        self.post('buyer','rental',{'id':rid,'operation':'cancel'})
        self.assertEqual(self.post('buyer','rental-availability',data)['available'],2)

    def test_overdue_collected_equipment_blocks_future_availability_until_return(self):
        data=self.rental_data(qty=2)
        rid=self.post('buyer','rental-book',data)['rental_id']
        Rental.objects.filter(pk=rid).update(state='COLLECTED', starts_at=timezone.now()-timedelta(days=2),
                                             ends_at=timezone.now()-timedelta(days=1))
        self.assertEqual(self.post('buyer','rental-availability',data)['available'],0)
        self.post('supplier2','rental',{'id':rid,'operation':'return','notes':'Overdue equipment inspected and returned'})
        self.assertEqual(self.post('buyer','rental-availability',data)['available'],2)

    def test_invalid_ranges_and_input(self):
        data=self.rental_data()
        self.post('buyer','rental-book',{**data,'ends_at':data['starts_at']},400)
        self.post('buyer','rental-book',{**data,'quantity':-1},400)
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':1.5},400)
        self.post('buyer','checkout',{'key':'bad','site':'x','supervisor':self.users['buyer'].pk},400)

    def test_photo_reencoding_private_access_and_printable_receipt(self):
        o=self.new_order();self.arrive(o)
        raw=io.BytesIO();Image.new('RGB',(50,50),'green').save(raw,format='PNG')
        data=self.receipt_data(o);data['lines']=json.dumps(data['lines']);data['attest']='true'
        data['photos']=SimpleUploadedFile('inspection.png',raw.getvalue(),content_type='image/png')
        with override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}}):
            self.post('supervisor','receipt',data,format='multipart')
            photo=Photo.objects.get();self.assertTrue(photo.image.name.endswith('.jpg'));self.assertEqual(len(photo.sha256),64)
            self.client.force_authenticate(user=None);self.client.force_login(self.users['buyer'])
            response=self.client.get(f'/evidence/{photo.pk}/');self.assertEqual(response.status_code,200);response.close()
            self.client.force_login(self.users['supervisor2'])
            self.assertEqual(self.client.get(f'/evidence/{photo.pk}/').status_code,404)
            self.assertEqual(self.client.get(f'/receipt/{o.pk}/').status_code,404)

    def test_invalid_photo_does_not_create_partial_receipt(self):
        o=self.new_order();self.arrive(o)
        data=self.receipt_data(o);data['lines']=json.dumps(data['lines']);data['attest']='true'
        data['photos']=SimpleUploadedFile('fake.jpg',b'not an image',content_type='image/jpeg')
        self.post('supervisor','receipt',data,400,format='multipart')
        self.assertFalse(Receipt.objects.exists());o.refresh_from_db();self.assertEqual(o.state,'ARRIVED')

    def test_support_cannot_provision_verify_or_manage_payments(self):
        self.post('buyer','account',{},403)
        self.post('admin','account',{'username':'pilot_supplier','password':'StrongDemo2026!','role':'supplier'},403)
        self.post('admin','verify',{'id':self.users['supplier'].pk,'verified':True},403)
        self.assertFalse(User.objects.get(username='admin').is_staff)
        self.assertFalse(User.objects.get(username='admin').is_superuser)

    def test_csrf_and_anonymous_access(self):
        client=APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.get('/api/state/').status_code,403)
        client.force_login(self.users['buyer'])
        self.assertEqual(client.post('/api/action/cart/',{'listing':self.cement.pk,'quantity':1}).status_code,403)
        response=client.get('/');self.assertEqual(response.status_code,200)
        self.assertEqual(client.post('/api/action/cart/',{'listing':self.cement.pk,'quantity':1},HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)

    def test_open_job_board_does_not_leak_site_or_customer(self):
        o=self.new_order();self.ready(o)
        self.client.force_authenticate(user=self.users['driver'])
        data=self.client.get('/api/state/').json()
        self.assertEqual(data['orders'],[])
        self.assertNotIn('site',data['jobs'][0]);self.assertNotIn('purchaser',data['jobs'][0])

    def test_read_only_audit_and_no_generic_delete_endpoint(self):
        o=self.new_order()
        self.client.force_authenticate(user=self.users['admin'])
        self.assertEqual(self.client.delete('/api/action/payment/',{'id':o.pk}).status_code,405)
        self.assertEqual(self.client.post('/api/action/delete-event/',{}).status_code,400)
        self.assertTrue(Event.objects.filter(target=f'order:{o.pk}').exists())

    def test_all_role_workspaces_render(self):
        for who in ['buyer','supplier','supplier2','driver','supervisor','admin']:
            self.client.force_authenticate(user=self.users[who])
            response=self.client.get('/api/state/');self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['me']['username'],who)
        plain=Client();self.assertContains(plain.get('/login/'),'BuildExchange ZM')

    def test_bank_simulation_debits_once_and_ignores_client_amount(self):
        from .models import PaymentAttempt,DemoBankAccount
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':4})
        oid=self.post('buyer','checkout',{'key':'bank-checkout-demo','site':'Demo site','supervisor':self.users['supervisor'].pk})['order_ids'][0]
        self.post('buyer','terms',{'accept':True})
        data={'id':oid,'target':'order','bank':'absa-demo','key':'bank-idempotency-key','amount_ngwee':1}
        a=self.post('buyer','payment-start',data)
        self.assertEqual(self.post('buyer','payment-start',data)['attempt_id'],a['attempt_id'])
        order=Order.objects.get(pk=oid);attempt=PaymentAttempt.objects.get(pk=a['attempt_id'])
        self.assertEqual(attempt.amount_ngwee,order.total_ngwee)
        self.post('buyer','payment-decide',{'id':attempt.pk,'decision':'approve'})
        self.post('buyer','payment-decide',{'id':attempt.pk,'decision':'approve'})
        self.assertEqual(DemoBankAccount.objects.get(user=self.users['buyer']).balance_ngwee,10000000-order.total_ngwee)
        self.post('buyer','payment-start',{**data,'key':'second-charge-attempt'},400)

    def test_declined_bank_payment_can_be_retried_without_charging(self):
        from .models import DemoBankAccount
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':3})
        oid=self.post('buyer','checkout',{'key':'decline-checkout-demo','site':'Test site','supervisor':self.users['supervisor'].pk})['order_ids'][0]
        self.pay_demo('buyer','order',oid,'decline')
        self.assertEqual(Order.objects.get(pk=oid).payment_status,'PENDING')
        self.assertEqual(DemoBankAccount.objects.get().balance_ngwee,10000000)
        self.pay_demo('buyer','order',oid)
        self.assertEqual(Order.objects.get(pk=oid).payment_status,'PAID_DEMO')

    def test_unpaid_orders_cannot_start_supplier_preparation(self):
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':2})
        oid=self.post('buyer','checkout',{'key':'unpaid-checkout-demo','site':'Test site','supervisor':self.users['supervisor'].pk})['order_ids'][0]
        self.post('supplier','supplier-order',{'id':oid,'operation':'ACCEPTED'},400)

    def test_terms_and_payment_ownership_are_required(self):
        from .models import TermsAcceptance,PaymentAttempt
        o=self.new_order();TermsAcceptance.objects.filter(user=self.users['buyer']).delete()
        self.post('buyer','payment-start',{'id':o.pk,'target':'order','bank':'absa-demo','key':'terms-required-attempt'},400)
        attempt=PaymentAttempt.objects.get(order=o)
        self.post('supplier','payment-decide',{'id':attempt.pk,'decision':'approve'},403)
        self.client.force_authenticate(user=None);self.client.force_login(self.users['supplier'])
        self.assertEqual(self.client.get(f'/bank-sandbox/{attempt.pk}/').status_code,403)

    def test_expired_or_insufficient_demo_account_never_marks_paid(self):
        from .models import DemoBankAccount,PaymentAttempt
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':5})
        oid=self.post('buyer','checkout',{'key':'expired-bank-checkout','site':'Test site','supervisor':self.users['supervisor'].pk})['order_ids'][0]
        self.post('buyer','terms',{'accept':True})
        attempt=self.post('buyer','payment-start',{'id':oid,'target':'order','bank':'absa-demo','key':'expired-bank-attempt'})['attempt_id']
        DemoBankAccount.objects.update(balance_ngwee=0)
        self.post('buyer','payment-decide',{'id':attempt,'decision':'approve'},400)
        DemoBankAccount.objects.update(balance_ngwee=10000000)
        PaymentAttempt.objects.filter(pk=attempt).update(created_at=timezone.now()-timedelta(minutes=16))
        self.post('buyer','payment-decide',{'id':attempt,'decision':'approve'},400)
        self.assertEqual(Order.objects.get(pk=oid).payment_status,'PENDING')

    def test_rental_bank_total_and_return_refunds_only_deposit(self):
        from .models import DemoBankAccount,PaymentAttempt
        rid=self.post('buyer','rental-book',self.rental_data())['rental_id'];rental=Rental.objects.get(pk=rid)
        self.pay_demo('buyer','rental',rid)
        self.assertEqual(PaymentAttempt.objects.get(rental_id=rid).amount_ngwee,rental.total_ngwee+rental.deposit_ngwee)
        with patch('exchange.services.timezone.now',return_value=rental.starts_at+timedelta(minutes=1)):
            self.post('supplier2','rental',{'id':rid,'operation':'collect'})
        self.post('supplier2','rental',{'id':rid,'operation':'return','notes':'Working equipment returned'})
        self.assertEqual(DemoBankAccount.objects.get().balance_ngwee,10000000-rental.total_ngwee)
        self.assertEqual(PaymentAttempt.objects.get(rental_id=rid).refunded_ngwee,rental.deposit_ngwee)
        self.post('supplier2','rental',{'id':rid,'operation':'return','notes':'Duplicate'},400)

    def test_bank_paid_rental_cancellation_returns_full_simulated_amount(self):
        from .models import DemoBankAccount
        rid=self.post('buyer','rental-book',self.rental_data())['rental_id']
        self.pay_demo('buyer','rental',rid)
        self.post('buyer','rental',{'id':rid,'operation':'cancel'})
        self.assertEqual(DemoBankAccount.objects.get().balance_ngwee,10000000)

    def test_support_only_sees_submitted_cases_and_no_bank_data(self):
        o=self.new_order();self.client.force_authenticate(user=self.users['admin'])
        before=self.client.get('/api/state/').json();self.assertEqual(before['orders'],[])
        self.assertEqual(before['stores'],[]);self.assertEqual(before['payments'],[])
        self.post('buyer','support-open',{'id':o.pk,'subject':'Missing bags','description':'Please help reconcile this demo order'})
        self.client.force_authenticate(user=self.users['admin']);after=self.client.get('/api/state/').json()
        self.assertEqual(len(after['tickets']),1);self.assertEqual(len(after['orders']),1)
        self.assertNotIn('payment_reference',after['orders'][0]);self.assertNotIn('total_ngwee',after['orders'][0])
        self.assertNotIn('audit',after);self.assertNotIn('accounts',after)
        self.post('admin','support-reply',{'id':after['tickets'][0]['id'],'state':'IN_REVIEW','response':'We will help the supplier review the count.'})
        self.post('admin','cart',{'listing':self.cement.pk,'quantity':1},403)
        self.post('admin','accept-job',{'id':1},403)

    def test_driver_location_requires_active_assignment_and_explicit_consent(self):
        o=self.new_order();job=self.ready(o);self.post('driver','accept-job',{'id':job.pk})
        data={'id':job.pk,'source':'demo','latitude':-15.4,'longitude':28.3,'purpose':'route-rehearsal'}
        self.post('driver','location',data,400)
        self.post('driver2','location',{**data,'consent':True},404)
        self.post('driver','location',{**data,'consent':True,'latitude':0},400)
        self.post('driver','location',{**data,'consent':True})
        self.client.force_authenticate(user=self.users['buyer'])
        tracked=self.client.get(f'/api/tracking/{o.pk}/').json()
        self.assertEqual(tracked['delivery']['checkpoints'][-1]['source'],'demo')
        self.assertNotIn('events',tracked)

    def test_fees_are_server_calculated_and_destination_is_idempotent(self):
        self.post('buyer','cart',{'listing':self.cement.pk,'quantity':10})
        data={'latitude':-15.43,'longitude':28.31}
        quoted=self.post('buyer','estimate',data)
        order_data={**data,'key':'location-checkout-key','site':'Site A','supervisor':self.users['supervisor'].pk,'total_ngwee':1}
        oid=self.post('buyer','checkout',order_data)['order_ids'][0];order=Order.objects.get(pk=oid)
        self.assertEqual(order.total_ngwee,quoted['total_ngwee']);self.assertGreater(order.commission_ngwee,0)
        self.post('buyer','checkout',{**order_data,'longitude':28.4},400)

    def test_researched_storefront_seed_is_additive_and_has_sources(self):
        from .models import Storefront
        with override_settings(DEBUG=True):call_command('seed_marketplace',verbosity=0)
        self.assertEqual(Storefront.objects.count(),6)
        self.assertEqual(Listing.objects.filter(catalogue_key__isnull=False).count(),37)
        l=Listing.objects.filter(catalogue_key__isnull=False).first();Listing.objects.filter(pk=l.pk).update(stock=7)
        with override_settings(DEBUG=True):call_command('seed_marketplace',verbosity=0)
        self.assertEqual(Listing.objects.get(pk=l.pk).stock,7)
        self.assertTrue(all(x.source_url.startswith('https://') for x in Storefront.objects.all()))

    def test_customer_payload_hides_audit_and_invalid_body_is_rejected(self):
        o=self.new_order();self.client.force_authenticate(user=self.users['buyer'])
        data=self.client.get('/api/state/').json()
        self.assertNotIn('audit',data);self.assertNotIn('events',data['orders'][0])
        response=self.client.post('/api/action/cart/',[],format='json')
        self.assertEqual(response.status_code,400)
