import {createContext,useContext,useState,useEffect,useCallback,useRef} from 'react';
import type {ReactNode} from 'react';
import type {Address,CartItem,Catalog,Order,Product,User} from '../../../packages/shared/types';
import {api,post} from './api';
export const blankAddress:Address={label:'Home',zone:'rhodes',street:'',landmark:'',phone:'',notes:''};
type ContextValue={catalog:Catalog|null;user:User|null;orders:Order[];cart:CartItem[];address:Address;favourites:string[];loading:boolean;online:boolean;page:string;navigate:(page:string)=>void;setAddress:(a:Address)=>void;setCart:(c:CartItem[])=>void;add:(p:Product)=>void;change:(id:string,by:number)=>void;refresh:()=>Promise<void>;login:(u:User)=>Promise<void>;logout:()=>Promise<void>;toast:(m:string)=>void;toggleFavourite:(id:string)=>void;authOpen:boolean;setAuthOpen:(v:boolean)=>void;bagOpen:boolean;setBagOpen:(v:boolean)=>void;};
const Context=createContext<ContextValue>(null!);
function readCart(){try{return JSON.parse(localStorage.getItem('yebbo.cart')||'[]') as CartItem[];}catch{return [];}}
export function Provider({children}:{children:ReactNode}){
 const[catalog,setCatalog]=useState<Catalog|null>(null),[user,setUser]=useState<User|null>(null),[orders,setOrders]=useState<Order[]>([]),[cart,setCart]=useState<CartItem[]>(readCart),[address,setAddress]=useState<Address>(blankAddress),[favourites,setFavourites]=useState<string[]>([]),[loading,setLoading]=useState(true),[online,setOnline]=useState(true),[page,setPage]=useState(location.hash.slice(1)||'/'),[message,setMessage]=useState(''),[authOpen,setAuthOpen]=useState(false),[bagOpen,setBagOpen]=useState(false);
 const timer=useRef<ReturnType<typeof setTimeout>|null>(null);const currentUser=useRef<User|null>(null);
 const toast=useCallback((m:string)=>{setMessage(m);if(timer.current)clearTimeout(timer.current);timer.current=setTimeout(()=>setMessage(''),4500);},[]);
 const navigate=(p:string)=>{location.hash=p;setPage(p);window.scrollTo({top:0,behavior:'smooth'});};
 useEffect(()=>{const cb=()=>setPage(location.hash.slice(1)||'/');window.addEventListener('hashchange',cb);return()=>window.removeEventListener('hashchange',cb);},[]);
 const refresh=useCallback(async()=>{try{const c=await api<Catalog>('/catalog');setCatalog(c);setOnline(true);if(currentUser.current){const data=await api<Order[]>('/orders');setOrders(data);}}catch{setOnline(false);}},[]);
 useEffect(()=>{async function boot(){await refresh();try{const me=await api<{user:User;address:Address|null;favourites:string[]}>('/me');setUser(me.user);currentUser.current=me.user;setFavourites(me.favourites);if(me.address)setAddress(me.address);setOrders(await api('/orders'));}catch{/* Guests can browse without authentication. */}setLoading(false);}void boot();const poll=setInterval(()=>{if(!document.hidden)void refresh();},6000);return()=>clearInterval(poll);},[refresh]);
 useEffect(()=>{localStorage.setItem('yebbo.cart',JSON.stringify(cart));},[cart]);
 const login=async(u:User)=>{currentUser.current=u;setUser(u);const me=await api('/me');setFavourites(me.favourites);setAddress(me.address||blankAddress);setOrders(await api('/orders'));setAuthOpen(false);navigate(u.role==='customer'?'/':'/workspace');toast('Welcome, '+u.name.split(' ')[0]+'.');};
 const logout=async()=>{await post('/auth/logout',{});currentUser.current=null;setUser(null);setOrders([]);setFavourites([]);setAddress(blankAddress);setCart([]);navigate('/');};
 const add=(p:Product)=>{if(!p.available||p.stock<1)return;if(cart.length){const first=catalog?.products.find(x=>x.id===cart[0].productId);if(first&&first.merchantId!==p.merchantId){toast('Your bag is from another shop. Empty it before starting a new order.');setBagOpen(true);return;}}
  const old=cart.find(i=>i.productId===p.id);if((old?.quantity||0)>=Math.min(p.stock,20)){toast('You’ve reached the quantity available for this item.');return;}
  setCart(prev=>old?prev.map(i=>i.productId===p.id?{...i,quantity:i.quantity+1}:i):[...prev,{productId:p.id,quantity:1}]);toast(p.name+' added to your bag.');};
 const change=(id:string,by:number)=>setCart(prev=>prev.map(i=>i.productId===id?{...i,quantity:Math.min(20,catalog?.products.find(p=>p.id===id)?.stock||20,i.quantity+by)}:i).filter(i=>i.quantity>0));
 const toggleFavourite=async(id:string)=>{if(!user){setAuthOpen(true);return;}try{const result=await post('/favourites/'+id,{});setFavourites(prev=>result.favourite?[...prev,id]:prev.filter(x=>x!==id));}catch(e){toast((e as Error).message);}};
 return <Context.Provider value={{catalog,user,orders,cart,address,favourites,loading,online,page,navigate,setAddress,setCart,add,change,refresh,login,logout,toast,toggleFavourite,authOpen,setAuthOpen,bagOpen,setBagOpen}}>{children}{message&&<div className="toast" role="status"><span className="toast-dot"/>{message}</div>}</Context.Provider>;
}
export const useApp=()=>useContext(Context);
