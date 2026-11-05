import {z} from 'zod';
import {Store,id,now,hashToken} from './db.ts';
import type {Address,CartItem,Merchant,Order,Product,Quote,Status,User,Zone} from '../../../packages/shared/types.ts';
export class AppError extends Error {status:number;constructor(status:number,message:string){super(message);this.status=status;}}
export function requireThat(test:unknown,message:string,status=400):asserts test {if(!test)throw new AppError(status,message);}
export const addressSchema=z.object({label:z.string().trim().min(1).max(40),zone:z.string().min(1),street:z.string().trim().min(4).max(180),landmark:z.string().trim().max(160).default(''),phone:z.string().regex(/^(?:\+260|0)[79]\d{8}$/, 'Enter a Zambian mobile number, e.g. 0971234567.'),notes:z.string().trim().max(400).default(''),lat:z.number().min(-90).max(90).optional(),lng:z.number().min(-180).max(180).optional()}).refine(a=>(a.lat===undefined)===(a.lng===undefined),'Both map coordinates are required.');
export const cartSchema=z.array(z.object({productId:z.string().min(1),quantity:z.number().int().min(1).max(20)})).min(1).max(30);
export const orderSchema=z.object({items:cartSchema,address:addressSchema,paymentMethod:z.enum(['cash','airtel_demo','mtn_demo']),promo:z.string().max(30).default(''),simulateFailure:z.boolean().default(false),idempotencyKey:z.string().min(10).max(100)});
export function quote(store:Store,user:User,items:CartItem[],zoneId:string,promo=''):Quote{
 const zone=store.get<Zone>('zones',zoneId);requireThat(zone?.active,'Choose an available Lusaka delivery area.');
 requireThat(new Set(items.map(x=>x.productId)).size===items.length,'Duplicate products must be combined.');
 const selected=items.map(i=>{const p=store.get<Product>('products',i.productId);requireThat(p?.available&&p.stock>=i.quantity,'An item is unavailable or has insufficient stock.');return {...i,product:p};});
 const merchantId=selected[0].product.merchantId;requireThat(selected.every(i=>i.product.merchantId===merchantId),'Your basket can contain items from one shop at a time.');
 const merchant=store.get<Merchant>('merchants',merchantId);requireThat(merchant?.open&&merchant.approved,'This shop is currently unavailable.');
 const subtotal=selected.reduce((a,i)=>a+i.product.price*i.quantity,0);requireThat(subtotal>=merchant.minimum,`This shop has a minimum order of K${merchant.minimum/100}.`);
 let discount=0;
 if(promo.trim()){
  requireThat(promo.toUpperCase()==='WELCOME10','This promo code is not valid.');
  const used=store.all<Order>('orders').some(o=>o.userId===user.id&&o.discount>0&&!['CANCELLED','REJECTED'].includes(o.status));
  requireThat(!used,'Your welcome offer has already been used.');discount=Math.min(2500,Math.round(subtotal*.1));
 }
 const fee=merchant.fee+zone.fee;
 return {merchantId,subtotal,fee,discount,total:subtotal+fee-discount,commission:Math.round(subtotal*.1),items:selected.map(i=>({productId:i.productId,name:i.product.name,quantity:i.quantity,price:i.product.price,image:i.product.image}))};
}
export function placeOrder(store:Store,user:User,input:unknown){
 requireThat(user.role==='customer','Only customer accounts can place orders.',403);
 const body=orderSchema.parse(input);const requestHash=hashToken(JSON.stringify(body));
 return store.transaction(()=>{
  const existing=store.db.prepare('SELECT data,request_hash FROM orders WHERE user_id=? AND idem=?').get(user.id,body.idempotencyKey);
  if(existing){requireThat(existing.request_hash===requestHash,'This request key was used for a different order.',409);return JSON.parse(existing.data as string) as Order;}
  const q=quote(store,user,body.items,body.address.zone,body.promo);
  if(body.address.lat!==undefined&&body.address.lng!==undefined){const z=store.get<Zone>('zones',body.address.zone)!;const dy=(body.address.lat-z.lat)*111;const dx=(body.address.lng-z.lng)*111*Math.cos(z.lat*Math.PI/180);requireThat(Math.hypot(dx,dy)<=z.radius,'Your map pin is outside the selected delivery zone.');}
  requireThat(!(body.simulateFailure&&body.paymentMethod!=='cash'),'Simulated payment failed. No order was placed and no money was charged.',402);
  const merchant=store.get<Merchant>('merchants',q.merchantId)!;
  const order:Order={...q,id:'YB-'+id().slice(0,8).toUpperCase(),userId:user.id,customerName:user.name,merchantName:merchant.name,status:'PLACED',paymentMethod:body.paymentMethod,paymentStatus:body.paymentMethod==='cash'?'PENDING':'PAID',address:body.address,riderId:null,riderName:null,riderAccepted:0,createdAt:now(),updatedAt:now(),deliveredAt:null,reason:'',rating:null,review:'',events:[{id:id(),status:'PLACED',note:body.paymentMethod==='cash'?'Order placed · pay cash on delivery':'Order placed · simulated payment successful',actor:user.name,createdAt:now()}]};
  for(const item of q.items){const p=store.get<Product>('products',item.productId)!;store.put('products',{...p,stock:p.stock-item.quantity});}
  store.db.prepare('INSERT INTO orders(id,user_id,idem,request_hash,data) VALUES(?,?,?,?,?)').run(order.id,user.id,body.idempotencyKey,requestHash,JSON.stringify(order));
  store.db.prepare('INSERT INTO addresses(user_id,data) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data').run(user.id,JSON.stringify(body.address));
  return order;
 });
}
export function canRead(user:User,o:Order){return user.role==='admin'||(user.role==='customer'&&o.userId===user.id)||(user.role==='merchant'&&o.merchantId===user.merchantId)||(user.role==='rider'&&o.riderId===user.id);}
export function orderFor(store:Store,user:User,orderId:string){const o=store.get<Order>('orders',orderId);requireThat(o&&canRead(user,o),'Order not found.',404);return o;}
export function updateOrder(store:Store,user:User,orderId:string,input:unknown){
 const b=z.object({action:z.enum(['ACCEPTED','PREPARING','READY_FOR_PICKUP','ASSIGNED','PICKED_UP','DELIVERED','CANCELLED','REJECTED','accept_job','refund']),riderId:z.string().optional(),reason:z.string().trim().max(300).default(''),cashCollected:z.boolean().default(false)}).parse(input);
 return store.transaction(()=>{
  const o=orderFor(store,user,orderId);const from=o.status;
  if(b.action==='accept_job'){requireThat(user.role==='rider'&&o.riderId===user.id&&o.status==='ASSIGNED','This job cannot be accepted.',403);requireThat(!o.riderAccepted,'This job has already been accepted.',409);o.riderAccepted=1;}
  else if(b.action==='refund') {requireThat(user.role==='admin','Administrator access required.',403);requireThat(['CANCELLED','REJECTED'].includes(o.status)&&o.paymentStatus==='REFUND_PENDING','No pending refund exists for this order.');o.paymentStatus='REFUNDED';}
  else if(b.action==='CANCELLED'||b.action==='REJECTED'){
   requireThat(!['DELIVERED','PICKED_UP','CANCELLED','REJECTED'].includes(from),'This order cannot be cancelled.');
   if(b.action==='REJECTED')requireThat(user.role==='merchant'&&user.merchantId===o.merchantId&&from==='PLACED','Only the shop can reject a new order.',403);
   else requireThat(user.role==='admin'||(user.role==='customer'&&o.userId===user.id&&from==='PLACED'),'Contact support to cancel an accepted order.',403);
   requireThat(b.reason.length>=4,'Please provide a reason.');o.reason=b.reason;o.status=b.action;
   if(o.paymentStatus==='PAID')o.paymentStatus='REFUND_PENDING';
   for(const i of o.items){const p=store.get<Product>('products',i.productId);if(p)store.put('products',{...p,stock:p.stock+i.quantity});}
  }else{
   const next:Partial<Record<Status,string>>={PLACED:'ACCEPTED',ACCEPTED:'PREPARING',PREPARING:'READY_FOR_PICKUP',READY_FOR_PICKUP:'ASSIGNED',ASSIGNED:'PICKED_UP',PICKED_UP:'DELIVERED'};
   requireThat(next[from]===b.action,'The order has changed. Refresh and try again.',409);
   if(['ACCEPTED','PREPARING','READY_FOR_PICKUP'].includes(b.action))requireThat(user.role==='merchant'&&user.merchantId===o.merchantId,'Only the merchant can prepare an order.',403);
   if(b.action==='ASSIGNED'){
    requireThat(user.role==='admin','Only an administrator can dispatch riders.',403);const rider=store.get<User>('users',b.riderId||'');requireThat(rider?.role==='rider'&&rider.active,'Choose an active rider.');
    o.riderId=rider.id;o.riderName=rider.name;o.riderAccepted=0;
   }
   if(['PICKED_UP','DELIVERED'].includes(b.action)){requireThat(user.role==='rider'&&o.riderId===user.id&&o.riderAccepted,'Only the assigned rider who accepted this job can update delivery.',403);}
   if(b.action==='DELIVERED'){if(o.paymentMethod==='cash'){requireThat(b.cashCollected,'Confirm cash collection before completing delivery.');o.paymentStatus='PAID';}o.deliveredAt=now();}
   o.status=b.action;
  }
  o.updatedAt=now();o.events.push({id:id(),status:o.status,note:b.action==='accept_job'?'Rider accepted the delivery':b.action==='refund'?'Simulated refund completed':b.reason||b.action.replaceAll('_',' '),actor:user.name,createdAt:now()});
  store.put('orders',o);store.audit(user,b.action,o.id,b.reason);return o;
 });
}
