import express from 'express';
import type {Request,Response,NextFunction} from 'express';
import {z} from 'zod';
import {randomBytes} from 'node:crypto';
import {resolve} from 'node:path';
import {existsSync} from 'node:fs';
import {Store,checkPassword,hashPassword,hashToken,id,now} from './db.ts';
import {AppError,requireThat,placeOrder,quote,cartSchema,addressSchema,orderFor,updateOrder,canRead} from './domain.ts';
import type {User,Merchant,Product,Order,Ticket,Zone,Address} from '../../../packages/shared/types.ts';
type AuthRequest=Request&{user:User;sessionToken:string};
export function createApp(store:Store){
 const app=express();app.disable('x-powered-by');
 const origins=new Set((process.env.WEB_ORIGIN||'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4000,http://127.0.0.1:4000').split(','));
 app.use((req,res,next)=>{
  res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');res.setHeader('X-Frame-Options','DENY');
  if(req.path.startsWith('/api'))res.setHeader('Cache-Control','no-store');
  const origin=req.headers.origin;
  if(origin&&!origins.has(origin)){res.status(403).json({error:'This origin is not allowed.'});return;}
  if(origin){res.setHeader('Access-Control-Allow-Origin',origin);res.setHeader('Vary','Origin');res.setHeader('Access-Control-Allow-Credentials','true');res.setHeader('Access-Control-Allow-Headers','Content-Type, Authorization, X-Yebbo-Client');res.setHeader('Access-Control-Allow-Methods','GET,POST,PATCH,DELETE,OPTIONS');}
  if(req.method==='OPTIONS'){res.sendStatus(204);return;}
  if(req.path.startsWith('/api')&&['POST','PATCH','DELETE'].includes(req.method)&&req.headers['x-yebbo-client']!=='1'){res.status(403).json({error:'Missing application request header.'});return;}
  next();
 });
 app.use(express.json({limit:'100kb'}));
 const auth=(req:Request,res:Response,next:NextFunction)=>{
  const cookie=req.headers.cookie?.split(';').map(x=>x.trim()).find(x=>x.startsWith('yebbo_session='))?.slice(14);
  const token=req.headers.authorization?.startsWith('Bearer ')?req.headers.authorization.slice(7):cookie;
  const row=token?store.db.prepare('SELECT user_id FROM sessions WHERE token=? AND expires>?').get(hashToken(token),now()):null;
  const user=row?store.get<User>('users',row.user_id as string):null;
  if(!user?.active){res.status(401).json({error:'Please sign in to continue.'});return;}
  (req as AuthRequest).user=user;(req as AuthRequest).sessionToken=token!;next();
 };
 const admin=(req:Request,_res:Response,next:NextFunction)=>{requireThat((req as AuthRequest).user.role==='admin','Administrator access required.',403);next();};
 const session=(res:Response,user:User)=>{
  const token=randomBytes(32).toString('hex');store.db.prepare('DELETE FROM sessions WHERE expires<?').run(now());store.db.prepare('INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)').run(hashToken(token),user.id,new Date(Date.now()+7*86400000).toISOString());
  res.cookie('yebbo_session',token,{httpOnly:true,sameSite:'strict',secure:process.env.NODE_ENV==='production',maxAge:7*86400000,path:'/'});
  return {user,token};
 };
 const attempts=new Map<string,{count:number;expires:number}>();
 const limit=(req:Request,_res:Response,next:NextFunction)=>{const key=req.ip||'local';const entry=attempts.get(key);const v=entry&&entry.expires>Date.now()?entry:{count:0,expires:Date.now()+60000};v.count++;attempts.set(key,v);if(attempts.size>10000)for(const[k,e]of attempts)if(e.expires<Date.now())attempts.delete(k);requireThat(v.count<=25,'Too many attempts. Please wait a minute.',429);next();};
 app.get('/api/health',(_req,res)=>res.json({ok:true,service:'Yebbo',payments:'simulation',database:'sqlite'}));
 app.get('/api/catalog',(_req,res)=>{const merchants=store.all<Merchant>('merchants').filter(m=>m.approved);res.json({merchants,products:store.all<Product>('products').filter(p=>merchants.some(m=>m.id===p.merchantId)),zones:store.all<Zone>('zones'),categories:[...new Set(merchants.map(m=>m.category))],demo:true});});
 app.post('/api/auth/register',limit,(req,res)=>{
  const b=z.object({name:z.string().trim().min(2).max(80),email:z.email().max(200).transform(x=>x.toLowerCase()),password:z.string().min(10).max(128)}).parse(req.body);
  requireThat(!store.db.prepare('SELECT id FROM users WHERE email=?').get(b.email),'An account with that email already exists.',409);
  const user:User={id:id(),name:b.name,email:b.email,role:'customer',phone:'',active:1,merchantId:null,createdAt:now()};store.addUser(user,b.password);res.status(201).json(session(res,user));
 });
 app.post('/api/auth/login',limit,(req,res)=>{
  const b=z.object({email:z.email().transform(x=>x.toLowerCase()),password:z.string().min(1).max(128)}).parse(req.body);
  const row=store.db.prepare('SELECT password,data FROM users WHERE email=?').get(b.email);
  const user=row?JSON.parse(row.data as string) as User:null;
  requireThat(row&&checkPassword(b.password,row.password as string)&&user?.active,'Email or password is incorrect.',401);res.json(session(res,user));
 });
 app.post('/api/auth/logout',auth,(req,res)=>{store.db.prepare('DELETE FROM sessions WHERE token=?').run(hashToken((req as AuthRequest).sessionToken));res.clearCookie('yebbo_session',{path:'/'});res.json({ok:true});});
 app.get('/api/me',auth,(req,res)=>{
  const user=(req as AuthRequest).user;const address=store.db.prepare('SELECT data FROM addresses WHERE user_id=?').get(user.id);
  res.json({user,address:address?JSON.parse(address.data as string):null,favourites:store.db.prepare('SELECT merchant_id FROM favourites WHERE user_id=?').all(user.id).map(r=>r.merchant_id)});
 });
 app.patch('/api/me',auth,(req,res)=>{const b=z.object({name:z.string().trim().min(2).max(80),phone:z.string().max(20)}).parse(req.body);const u={...(req as AuthRequest).user,...b};store.saveUser(u);res.json(u);});
 app.post('/api/me/password',auth,(req,res)=>{const b=z.object({currentPassword:z.string().max(128),newPassword:z.string().min(10).max(128)}).parse(req.body);const u=(req as AuthRequest).user;const row=store.db.prepare('SELECT password FROM users WHERE id=?').get(u.id)!;requireThat(checkPassword(b.currentPassword,row.password as string),'Current password is incorrect.',403);store.transaction(()=>{store.db.prepare('UPDATE users SET password=? WHERE id=?').run(hashPassword(b.newPassword),u.id);store.db.prepare('DELETE FROM sessions WHERE user_id=?').run(u.id);});res.clearCookie('yebbo_session',{path:'/'});res.json({ok:true});});
 app.delete('/api/me',auth,(req,res)=>{const u=(req as AuthRequest).user;requireThat(u.role==='customer','Contact the administrator to close a staff account.');const b=z.object({password:z.string().max(128)}).parse(req.body);const row=store.db.prepare('SELECT password FROM users WHERE id=?').get(u.id)!;requireThat(checkPassword(b.password,row.password as string),'Password is incorrect.',403);requireThat(!store.all<Order>('orders').some(o=>o.userId===u.id&&!['DELIVERED','CANCELLED','REJECTED'].includes(o.status)),'Complete or cancel your active orders before closing your account.');store.transaction(()=>{store.saveUser({...u,active:0,name:'Deleted customer',email:`deleted-${u.id}@invalid.local`,phone:''});store.db.prepare('DELETE FROM sessions WHERE user_id=?').run(u.id);store.db.prepare('DELETE FROM addresses WHERE user_id=?').run(u.id);store.db.prepare('DELETE FROM favourites WHERE user_id=?').run(u.id);for(const o of store.all<Order>('orders').filter(o=>o.userId===u.id)){o.customerName='Deleted customer';o.address={label:'Removed',zone:o.address.zone,street:'Removed',landmark:'',phone:'',notes:''};o.events=o.events.map(e=>e.actor===u.name?{...e,actor:'Deleted customer'}:e);store.put('orders',o);}for(const t of store.all<Ticket>('tickets').filter(t=>t.userId===u.id))store.put('tickets',{...t,userName:'Deleted customer',message:'Removed with account',reply:''});});res.clearCookie('yebbo_session',{path:'/'});res.json({ok:true});});
 app.post('/api/me/address',auth,(req,res)=>{const a=addressSchema.parse(req.body);requireThat(store.get<Zone>('zones',a.zone)?.active,'Choose an available delivery zone.');store.db.prepare('INSERT INTO addresses(user_id,data) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data').run((req as AuthRequest).user.id,JSON.stringify(a));res.json(a);});
 app.post('/api/favourites/:id',auth,(req,res)=>{const mid=String(req.params.id);requireThat(store.get('merchants',mid),'Shop not found.',404);const uid=(req as AuthRequest).user.id;const found=store.db.prepare('SELECT 1 FROM favourites WHERE user_id=? AND merchant_id=?').get(uid,mid);if(found)store.db.prepare('DELETE FROM favourites WHERE user_id=? AND merchant_id=?').run(uid,mid);else store.db.prepare('INSERT INTO favourites(user_id,merchant_id) VALUES(?,?)').run(uid,mid);res.json({favourite:!found});});
 app.post('/api/quote',auth,(req,res)=>{const b=z.object({items:cartSchema,zone:z.string(),promo:z.string().max(30).default('')}).parse(req.body);res.json(quote(store,(req as AuthRequest).user,b.items,b.zone,b.promo));});
 app.post('/api/orders',auth,(req,res)=>res.status(201).json(placeOrder(store,(req as AuthRequest).user,req.body)));
 app.get('/api/orders',auth,(req,res)=>{const u=(req as AuthRequest).user;res.json(store.all<Order>('orders').filter(o=>canRead(u,o)).sort((a,b)=>b.createdAt.localeCompare(a.createdAt)));});
 app.get('/api/orders/:id',auth,(req,res)=>res.json(orderFor(store,(req as AuthRequest).user,String(req.params.id))));
 app.patch('/api/orders/:id',auth,(req,res)=>res.json(updateOrder(store,(req as AuthRequest).user,String(req.params.id),req.body)));
 app.post('/api/orders/:id/review',auth,(req,res)=>{const u=(req as AuthRequest).user;const o=orderFor(store,u,String(req.params.id));requireThat(u.role==='customer'&&o.userId===u.id&&o.status==='DELIVERED','Only completed orders can be reviewed.',403);const b=z.object({rating:z.number().int().min(1).max(5),review:z.string().trim().max(500).default('')}).parse(req.body);store.put('orders',{...o,...b});res.json({...o,...b});});
 app.get('/api/tickets',auth,(req,res)=>{const u=(req as AuthRequest).user;res.json(store.all<Ticket>('tickets').filter(t=>u.role==='admin'||t.userId===u.id).sort((a,b)=>b.createdAt.localeCompare(a.createdAt)));});
 app.post('/api/tickets',auth,(req,res)=>{const u=(req as AuthRequest).user;const b=z.object({orderId:z.string().nullable().default(null),subject:z.string().trim().min(3).max(100),message:z.string().trim().min(5).max(2000)}).parse(req.body);if(b.orderId)orderFor(store,u,b.orderId);const t:Ticket={id:id(),userId:u.id,userName:u.name,...b,status:'OPEN',reply:'',createdAt:now()};store.put('tickets',t);res.status(201).json(t);});
 app.patch('/api/tickets/:id',auth,admin,(req,res)=>{const t=store.get<Ticket>('tickets',String(req.params.id));requireThat(t,'Ticket not found.',404);const b=z.object({status:z.enum(['OPEN','RESOLVED']),reply:z.string().trim().min(3).max(2000)}).parse(req.body);const out={...t,...b};store.put('tickets',out);store.audit((req as AuthRequest).user,'SUPPORT_REPLY',t.id);res.json(out);});
 app.patch('/api/products/:id',auth,(req,res)=>{const u=(req as AuthRequest).user;const p=store.get<Product>('products',String(req.params.id));requireThat(p,'Product not found.',404);requireThat(u.role==='admin'||(u.role==='merchant'&&u.merchantId===p.merchantId),'This is not your catalogue.',403);const b=z.object({name:z.string().trim().min(2).max(100).optional(),description:z.string().max(500).optional(),price:z.number().int().min(100).max(1000000).optional(),stock:z.number().int().min(0).max(10000).optional(),available:z.number().int().min(0).max(1).optional(),category:z.string().min(2).max(60).optional()}).parse(req.body);const out={...p,...b};store.put('products',out);store.audit(u,'PRODUCT_UPDATED',p.id);res.json(out);});
 app.post('/api/products',auth,(req,res)=>{const u=(req as AuthRequest).user;requireThat(u.role==='admin'||u.role==='merchant','Staff access required.',403);const b=z.object({merchantId:z.string(),name:z.string().trim().min(2).max(100),description:z.string().max(500),price:z.number().int().min(100).max(1000000),stock:z.number().int().min(0).max(10000),category:z.string().min(2).max(60)}).parse(req.body);requireThat(store.get('merchants',b.merchantId),'Merchant not found.');requireThat(u.role==='admin'||u.merchantId===b.merchantId,'This is not your shop.',403);const p:Product={...b,id:id(),image:store.get<Merchant>('merchants',b.merchantId)!.image,available:1,popular:0};store.put('products',p);store.audit(u,'PRODUCT_CREATED',p.id);res.status(201).json(p);});
 app.patch('/api/merchants/:id',auth,(req,res)=>{const u=(req as AuthRequest).user;const m=store.get<Merchant>('merchants',String(req.params.id));requireThat(m,'Shop not found.',404);requireThat(u.role==='admin'||(u.role==='merchant'&&u.merchantId===m.id),'This is not your shop.',403);const b=(u.role==='admin'?z.object({name:z.string().min(2).max(100).optional(),category:z.string().min(2).max(60).optional(),open:z.number().int().min(0).max(1).optional(),approved:z.number().int().min(0).max(1).optional(),fee:z.number().int().min(0).max(10000).optional(),minimum:z.number().int().min(0).max(100000).optional()}):z.object({open:z.number().int().min(0).max(1)})).parse(req.body);const out={...m,...b};store.put('merchants',out);store.audit(u,'SHOP_UPDATED',m.id);res.json(out);});
 app.get('/api/admin/users',auth,admin,(_req,res)=>res.json(store.all<User>('users')));
 app.get('/api/admin/merchants',auth,admin,(_req,res)=>res.json(store.all<Merchant>('merchants')));
 app.get('/api/admin/audit',auth,admin,(_req,res)=>res.json(store.all<any>('audit').sort((a,b)=>b.createdAt.localeCompare(a.createdAt)).slice(0,200)));
 app.patch('/api/admin/users/:id',auth,admin,(req,res)=>{const u=store.get<User>('users',String(req.params.id));requireThat(u,'Account not found.',404);requireThat(u.id!==(req as AuthRequest).user.id,'You cannot change your own administrator access.');const b=z.object({active:z.number().int().min(0).max(1).optional(),role:z.enum(['customer','merchant','rider']).optional(),merchantId:z.string().nullable().optional()}).parse(req.body);const out={...u,...b};if(out.role==='merchant')requireThat(out.merchantId&&store.get('merchants',out.merchantId),'A merchant account must be assigned a shop.');else out.merchantId=null;const hasActive=store.all<Order>('orders').some(o=>!['DELIVERED','CANCELLED','REJECTED'].includes(o.status)&&(o.riderId===u.id||o.userId===u.id||(u.role==='merchant'&&o.merchantId===u.merchantId)));requireThat(!hasActive,'Finish this account’s active orders before changing access.');store.saveUser(out);store.db.prepare('DELETE FROM sessions WHERE user_id=?').run(u.id);store.audit((req as AuthRequest).user,'ACCOUNT_UPDATED',u.id);res.json(out);});
 app.patch('/api/admin/zones/:id',auth,admin,(req,res)=>{const zone=store.get<Zone>('zones',String(req.params.id));requireThat(zone,'Zone not found.',404);const b=z.object({fee:z.number().int().min(0).max(10000).optional(),active:z.number().int().min(0).max(1).optional()}).parse(req.body);store.put('zones',{...zone,...b});store.audit((req as AuthRequest).user,'ZONE_UPDATED',zone.id);res.json({...zone,...b});});
 app.get('/api/admin/analytics',auth,admin,(req,res)=>{
  const b=z.object({from:z.string().regex(/^\d{4}-\d{2}-\d{2}$/).default('2000-01-01'),to:z.string().regex(/^\d{4}-\d{2}-\d{2}$/).default('2100-12-31')}).parse(req.query);requireThat(b.from<=b.to,'Start date must be before the end date.');
  const start=new Date(b.from+'T00:00:00+02:00').getTime(),end=new Date(b.to+'T23:59:59.999+02:00').getTime();
  const inPeriod=(date:string)=>{const v=new Date(date).getTime();return v>=start&&v<=end;};const all=store.all<Order>('orders');const placed=all.filter(o=>inPeriod(o.createdAt));const delivered=all.filter(o=>o.status==='DELIVERED'&&o.deliveredAt&&inPeriod(o.deliveredAt));const cohortDelivered=placed.filter(o=>o.status==='DELIVERED');
  const sum=(arr:Order[],fn:(o:Order)=>number)=>arr.reduce((a,o)=>a+fn(o),0);
  const byDay=new Map<string,{date:string;orders:number;revenue:number}>();for(const o of placed){const date=new Date(new Date(o.createdAt).getTime()+7200000).toISOString().slice(0,10);const row=byDay.get(date)||{date,orders:0,revenue:0};row.orders++;byDay.set(date,row);}for(const o of delivered){const date=new Date(new Date(o.deliveredAt!).getTime()+7200000).toISOString().slice(0,10);const row=byDay.get(date)||{date,orders:0,revenue:0};row.revenue+=o.commission+o.fee-o.discount;byDay.set(date,row);}
  res.json({period:b,timezone:'Africa/Lusaka',orders:placed.length,delivered:delivered.length,merchandiseValue:sum(delivered,o=>o.subtotal),revenue:sum(delivered,o=>o.commission+o.fee-o.discount),discounts:sum(delivered,o=>o.discount),merchantPayable:sum(delivered,o=>o.subtotal-o.commission),completionRate:placed.length?cohortDelivered.length/placed.length*100:0,cancellationRate:placed.length?placed.filter(o=>o.status==='CANCELLED').length/placed.length*100:0,rejections:placed.filter(o=>o.status==='REJECTED').length,averageMinutes:delivered.length?sum(delivered,o=>(new Date(o.deliveredAt!).getTime()-new Date(o.createdAt).getTime())/60000)/delivered.length:0,active:all.filter(o=>!['DELIVERED','CANCELLED','REJECTED'].includes(o.status)).length,daily:[...byDay.values()].sort((a,b)=>a.date.localeCompare(b.date)),merchants:store.all<Merchant>('merchants').map(m=>({name:m.name,orders:delivered.filter(o=>o.merchantId===m.id).length,value:sum(delivered.filter(o=>o.merchantId===m.id),o=>o.subtotal),rejections:placed.filter(o=>o.merchantId===m.id&&o.status==='REJECTED').length})),cancellations:placed.filter(o=>['CANCELLED','REJECTED'].includes(o.status)).map(o=>({id:o.id,status:o.status,reason:o.reason}))});
 });
 app.use('/api',(_req,res)=>res.status(404).json({error:'Endpoint not found.'}));
 const dist=resolve('dist');if(existsSync(dist)){app.use(express.static(dist));app.get('/{*path}',(_req,res)=>res.sendFile(resolve(dist,'index.html')));}
 app.use((err:unknown,_req:Request,res:Response,_next:NextFunction)=>{if(err instanceof z.ZodError){res.status(400).json({error:err.issues.map(i=>i.message).join(' ')});return;}if(err instanceof AppError){res.status(err.status).json({error:err.message});return;}console.error('Request failed:',err instanceof Error?err.message:'Unknown error');res.status(500).json({error:'Something went wrong. Please try again.'});});
 return app;
}
