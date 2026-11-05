import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { randomBytes, scryptSync, timingSafeEqual, randomUUID, createHash } from 'node:crypto';
import { merchants, products, zones } from './seed.ts';
import type { User } from '../../../packages/shared/types.ts';
export const now=()=>new Date().toISOString();
export const id=()=>randomUUID();
export const hashToken=(value:string)=>createHash('sha256').update(value).digest('hex');
export function hashPassword(value:string){const salt=randomBytes(16).toString('hex');return salt+':'+scryptSync(value,salt,64).toString('hex');}
export function checkPassword(value:string,stored:string){const [salt,hash]=stored.split(':');return timingSafeEqual(Buffer.from(hash,'hex'),scryptSync(value,salt,64));}
export class Store {
 db:DatabaseSync;
 constructor(path:string,seed=true){
  if(path!==':memory:') mkdirSync(dirname(path),{recursive:true});
  this.db=new DatabaseSync(path);this.db.exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
  this.db.exec(`
   CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS merchants(id TEXT PRIMARY KEY,data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS zones(id TEXT PRIMARY KEY,data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),idem TEXT NOT NULL,request_hash TEXT NOT NULL,data TEXT NOT NULL,UNIQUE(user_id,idem));
   CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
   CREATE INDEX IF NOT EXISTS orders_merchant ON orders(json_extract(data,'$.merchantId'));
   CREATE INDEX IF NOT EXISTS orders_rider ON orders(json_extract(data,'$.riderId'));
   CREATE TABLE IF NOT EXISTS addresses(user_id TEXT PRIMARY KEY REFERENCES users(id),data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS favourites(user_id TEXT NOT NULL REFERENCES users(id),merchant_id TEXT NOT NULL REFERENCES merchants(id),PRIMARY KEY(user_id,merchant_id));
   CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,data TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,data TEXT NOT NULL);
  `);
  if(seed&&!this.db.prepare('SELECT id FROM merchants LIMIT 1').get())this.seed();
 }
 get<T>(table:string,id:string):T|undefined{const row=this.db.prepare(`SELECT data FROM ${this.table(table)} WHERE id=?`).get(id);return row?JSON.parse(row.data as string):undefined;}
 all<T>(table:string):T[]{return this.db.prepare(`SELECT data FROM ${this.table(table)}`).all().map(r=>JSON.parse(r.data as string));}
 put<T extends {id:string}>(table:string,value:T){if(table==='orders'){const result=this.db.prepare('UPDATE orders SET data=? WHERE id=?').run(JSON.stringify(value),value.id);if(result.changes!==1)throw Error('Order not found for update');return;}this.db.prepare(`INSERT INTO ${this.table(table)}(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data`).run(value.id,JSON.stringify(value));}
 table(table:string){if(!['users','merchants','products','zones','orders','tickets','audit'].includes(table))throw Error('Invalid table');return table;}
 transaction<T>(fn:()=>T):T{this.db.exec('BEGIN IMMEDIATE');try{const v=fn();this.db.exec('COMMIT');return v;}catch(e){this.db.exec('ROLLBACK');throw e;}}
 addUser(user:User,password:string){this.db.prepare('INSERT INTO users(id,email,password,data) VALUES(?,?,?,?)').run(user.id,user.email,hashPassword(password),JSON.stringify(user));}
 saveUser(user:User){this.db.prepare('UPDATE users SET email=?,data=? WHERE id=?').run(user.email,JSON.stringify(user),user.id);}
 audit(actor:User,action:string,target:string,note=''){this.put('audit',{id:id(),actor:actor.name,actorId:actor.id,action,target,note,createdAt:now()} as {id:string});}
 seed(){this.transaction(()=>{
   merchants.forEach(m=>this.put('merchants',m));products.forEach(p=>this.put('products',p));zones.forEach(z=>this.put('zones',z));
   const password=process.env.DEMO_PASSWORD||'YebboDemo2026!';
   const people=[['customer','Chanda Mwila','customer'],['merchant','Tendai · The Burger Yard','merchant'],['rider','Mwamba Phiri','rider'],['admin','Yebbo Operations','admin']] as const;
   for(const [key,name,role] of people)this.addUser({id:key,name,email:`${key}@yebbo.test`,role,phone:'',active:1,merchantId:role==='merchant'?'m1':null,createdAt:now()},password);
  });}
 close(){this.db.close();}
}
