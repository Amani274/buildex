export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const response=await fetch('/api'+path,{...options,credentials:'include',headers:{'Content-Type':'application/json','X-Yebbo-Client':'1',...options.headers}});
 const data=await response.json().catch(()=>({error:'The server could not be reached.'}));
 if(!response.ok)throw new Error(data.error||'Something went wrong. Please try again.');return data as T;
}
export const post=<T=any>(path:string,body:unknown)=>api<T>(path,{method:'POST',body:JSON.stringify(body)});
export const patch=<T=any>(path:string,body:unknown)=>api<T>(path,{method:'PATCH',body:JSON.stringify(body)});
