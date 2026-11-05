import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';
import {Platform} from 'react-native';
export const API_URL=(process.env.EXPO_PUBLIC_API_URL||Constants.expoConfig?.extra?.apiUrl||'http://127.0.0.1:4000').replace(/\/$/,'');
let token:string|null=null;
export async function loadToken(){token=Platform.OS==='web'?sessionStorage.getItem('yebbo.token'):await SecureStore.getItemAsync('yebbo.token');return token;}
export async function saveToken(value:string|null){token=value;if(Platform.OS==='web'){if(value)sessionStorage.setItem('yebbo.token',value);else sessionStorage.removeItem('yebbo.token');}else if(value)await SecureStore.setItemAsync('yebbo.token',value);else await SecureStore.deleteItemAsync('yebbo.token');}
export async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{const res=await fetch(API_URL+'/api'+path,{method,headers:{'Content-Type':'application/json','X-Yebbo-Client':'1',...(token?{Authorization:'Bearer '+token}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});const data=await res.json();if(!res.ok)throw Error(data.error||'Please try again.');return data;}
