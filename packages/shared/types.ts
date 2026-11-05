export type Role = 'customer' | 'merchant' | 'rider' | 'admin';
export type Status = 'PLACED' | 'ACCEPTED' | 'PREPARING' | 'READY_FOR_PICKUP' | 'ASSIGNED' | 'PICKED_UP' | 'DELIVERED' | 'CANCELLED' | 'REJECTED';
export type PaymentMethod = 'cash' | 'airtel_demo' | 'mtn_demo';
export interface User {id:string; name:string; email:string; role:Role; phone:string; active:number; merchantId:string|null; createdAt:string;}
export interface Merchant {id:string;name:string;category:string;description:string;image:string;cover:string;rating:number;eta:string;fee:number;minimum:number;open:number;approved:number;tags:string[];address:string;lat:number;lng:number;featured:number;}
export interface Product {id:string;merchantId:string;name:string;description:string;price:number;image:string;category:string;stock:number;available:number;popular:number;}
export interface Address {label:string;zone:string;street:string;landmark:string;phone:string;notes:string;lat?:number;lng?:number;}
export interface Zone {id:string;name:string;fee:number;active:number;lat:number;lng:number;radius:number;}
export interface CartItem {productId:string;quantity:number;}
export interface OrderItem {productId:string;name:string;quantity:number;price:number;image:string;}
export interface OrderEvent {id:string;status:string;note:string;actor:string;createdAt:string;}
export interface Order {id:string;userId:string;merchantId:string;merchantName:string;customerName:string;status:Status;paymentMethod:PaymentMethod;paymentStatus:string;subtotal:number;fee:number;discount:number;total:number;commission:number;address:Address;items:OrderItem[];riderId:string|null;riderName:string|null;riderAccepted:number;createdAt:string;updatedAt:string;deliveredAt:string|null;reason:string;rating:number|null;review:string;events:OrderEvent[];}
export interface Ticket {id:string;userId:string;userName:string;orderId:string|null;subject:string;message:string;status:string;reply:string;createdAt:string;}
export interface Catalog {merchants:Merchant[];products:Product[];zones:Zone[];categories:string[];demo:boolean;}
export interface Quote {subtotal:number;fee:number;discount:number;total:number;commission:number;items:OrderItem[];merchantId:string;}
export const orderSteps:Status[]=['PLACED','ACCEPTED','PREPARING','READY_FOR_PICKUP','ASSIGNED','PICKED_UP','DELIVERED'];
export const statusLabels:Record<Status,string>={PLACED:'Order placed',ACCEPTED:'Accepted',PREPARING:'Being prepared',READY_FOR_PICKUP:'Ready for pickup',ASSIGNED:'Rider assigned',PICKED_UP:'On the way',DELIVERED:'Delivered',CANCELLED:'Cancelled',REJECTED:'Not accepted'};
export const money=(ngwee:number)=>'K'+(ngwee/100).toLocaleString('en-ZM',{minimumFractionDigits:2,maximumFractionDigits:2});
export const dateTime=(date:string)=>new Date(date).toLocaleString('en-GB',{timeZone:'Africa/Lusaka',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
export const terminal=(status:Status)=>['DELIVERED','CANCELLED','REJECTED'].includes(status);
