import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import type {Theme} from './contracts';

function read(key:string,fallback:string){try{return localStorage.getItem(key)||fallback;}catch{return fallback;}}
function write(key:string,value:string){try{localStorage.setItem(key,value);}catch{/* Non-sensitive device preference can remain in memory. */}}
const Preferences=createContext<{
  theme:Theme;resolved:'frost'|'midnight';setTheme:(value:Theme)=>void;
  gain:number;setGain:(value:number)=>void;
}|null>(null);
export function FrostPreferences({uid,children}:{uid:string;children:ReactNode}){
  const prefix=`sf-device-${uid}-`;
  const [theme,setTheme]=useState<Theme>(()=>{const t=read(prefix+'theme','system');return ['system','frost','midnight'].includes(t)?t as Theme:'system';});
  const [gain,setGain]=useState(()=>{const n=Number(read(prefix+'gain','100'));return Number.isFinite(n)&&n>=0&&n<=200?n:100;});
  const [systemDark,setSystemDark]=useState(()=>matchMedia('(prefers-color-scheme: dark)').matches);
  const resolved=theme==='system'?systemDark?'midnight':'frost':theme;
  useEffect(()=>{const q=matchMedia('(prefers-color-scheme: dark)');const change=()=>setSystemDark(q.matches);q.addEventListener('change',change);return()=>q.removeEventListener('change',change);},[]);
  useEffect(()=>{write(prefix+'theme',theme);window.dispatchEvent(new Event('sf-theme-change'));},[prefix,theme,resolved]);
  useEffect(()=>write(prefix+'gain',String(gain)),[prefix,gain]);
  return <Preferences.Provider value={{theme,resolved,setTheme,gain,setGain}}>{children}</Preferences.Provider>;
}
export function useFrostPreferences(){const value=useContext(Preferences);if(!value)throw new Error('Frost preferences require the authenticated shell.');return value;}
