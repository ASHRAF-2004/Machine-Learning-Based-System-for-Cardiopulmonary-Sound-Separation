import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {liveAuth} from '../auth/firebase';
import {firebaseConfigurationError} from '../config/runtime';
import {Context,type AppContextValue} from './store';
import {ApiError,createApiClient,type ApiClient} from './api';
import {validateSession,type SessionEnvelope,type LivePreferences} from './liveTypes';
import type {DemoState,User,UserPreferences} from './types';

type AuthStatus='loading'|'signed-out'|'unverified'|'ready'|'disabled'|'expired'|'error';
interface LiveContextValue {
  status:AuthStatus;error:string;session:SessionEnvelope|null;api:ApiClient;
  preferences:LivePreferences;refreshAccount:()=>Promise<void>;refreshIdentity:()=>Promise<void>;
  savePreferences:(value:LivePreferences)=>Promise<void>;logout:()=>Promise<void>;
}
const LiveContext=createContext<LiveContextValue|null>(null);
export function useLive(){const value=useContext(LiveContext);if(!value)throw new Error('Live context required.');return value;}
const preferences:UserPreferences={timezone:'Asia/Kuala_Lumpur',dateFormat:'day-first',reducedMotion:false,snow:true,highContrast:false,emailNotifications:false,jobNotifications:true,reviewNotifications:true,defaultSite:'Anterior chest',defaultPosition:'Seated',sampleRate:16000,retentionDays:90,preferredInput:'Ask each time',playbackRate:1};
const emptyState=():DemoState=>({users:[],recordings:[],jobs:[],results:[],assignments:[],reviews:[],notifications:[],audit:[],preferences:{},drafts:{},system:{maxUploadMB:25,retentionDays:0,maintenance:false,fusion:'Not connected'}});
function unavailable():never{throw new Error('This demonstration action is not available in the live workspace.');}
function toPresentationUser(value:SessionEnvelope):User {
  const u=value.user;
  return {id:u.id,name:u.display_name||u.email,email:u.email,role:({healthcare_staff:'staff',audio_analyst:'analyst',admin:'admin'} as const)[u.role],status:u.status==='active'?'active':'disabled',verified:u.email_verified,identities:[],createdAt:'',lastActive:''};
}
export function LiveAppProvider({children}:{children:ReactNode}) {
  const [status,setStatus]=useState<AuthStatus>(firebaseConfigurationError?'error':'loading');
  const [error,setError]=useState(firebaseConfigurationError),[session,setSession]=useState<SessionEnvelope|null>(null);
  const [uid,setUid]=useState<string|null>(null),[prefs,setPrefs]=useState<LivePreferences>({}),[toast,setToast]=useState('');
  const epoch=useRef(0),currentUid=useRef<string|null>(null),expired=useRef(false);
  const clear=useCallback(()=>{setSession(null);setPrefs({});setToast('');},[]);
  const logout=useCallback(async()=>{epoch.current++;currentUid.current=null;setUid(null);clear();setStatus('signed-out');expired.current=false;await liveAuth.logout();},[clear]);
  const expire=useCallback(()=>{epoch.current++;expired.current=true;currentUid.current=null;setUid(null);clear();setStatus('expired');void liveAuth.logout().catch(()=>{});},[clear]);
  const api=useMemo(()=>createApiClient(async force=>{
    const user=await liveAuth.current();
    if (!user || user.uid!==uid || currentUid.current!==uid) throw new DOMException('Account changed.','AbortError');
    return user.getIdToken(force);
  },()=>{if(currentUid.current===uid)expire();}),[uid,expire]);

  const accept=useCallback(async(value:SessionEnvelope,client:ApiClient,version:number)=>{
    const checked=validateSession(value);
    if(epoch.current!==version||checked.user.uid!==currentUid.current)return;
    if(checked.user.status!=='active'){clear();setStatus('disabled');return;}
    if(!checked.user.email_verified){clear();setStatus('unverified');return;}
    setSession(checked);setStatus('ready');setError('');
    const settings=await client.json<{preferences:LivePreferences}>('/preferences').catch(()=>null);
    if(epoch.current===version&&settings)setPrefs(settings.preferences||{});
  },[clear]);
  const fail=useCallback((failure:unknown,version:number)=>{
    if(epoch.current!==version)return;
    clear();
    if(failure instanceof ApiError&&failure.code==='email_verification_required')setStatus('unverified');
    else if(failure instanceof ApiError&&failure.code==='account_disabled')setStatus('disabled');
    else if(failure instanceof ApiError&&failure.status===401)expire();
    else {setStatus('error');setError(failure instanceof ApiError?failure.message:'Account services could not be loaded. Please retry.');}
  },[clear,expire]);
  const syncIdentity=useCallback(async()=>{
    const version=++epoch.current;
    setStatus('loading');clear();
    try {
      const user=await liveAuth.current();
      if(epoch.current!==version)return;
      currentUid.current=user?.uid||null;setUid(user?.uid||null);
      if(!user){setStatus(expired.current?'expired':'signed-out');return;}
      expired.current=false;
      if(!user.emailVerified){setStatus('unverified');return;}
      const client=createApiClient(async force=>{
        if(epoch.current!==version)throw new DOMException('Account changed.','AbortError');
        return user.getIdToken(force);
      },()=>{if(epoch.current===version)expire();});
      const value=await client.json<SessionEnvelope>('/auth/session',{method:'POST',body:'{}'});
      await accept(value,client,version);
    }catch(failure){fail(failure,version);}
  },[accept,clear,expire,fail]);
  useEffect(()=>{
    if(firebaseConfigurationError)return;
    let stop=()=>{};
    try {stop=liveAuth.observe(()=>{void syncIdentity();},()=>{clear();setStatus('error');setError('The identity session could not be restored. Sign in again.');});}
    catch {setStatus('error');setError('Authentication configuration could not be initialized.');}
    return()=>{stop();epoch.current++;};
  },[syncIdentity,clear]);
  const refreshAccount=useCallback(async()=>{
    if(!currentUid.current){await syncIdentity();return;}
    const version=epoch.current;
    try {await accept(await api.json<SessionEnvelope>('/auth/me'),api,version);}catch(failure){fail(failure,version);}
  },[accept,api,fail,syncIdentity]);
  // Roles are refreshed from the server, never from localStorage/custom claims.
  useEffect(()=>{
    if(status!=='ready')return;
    const refresh=()=>{if(document.visibilityState==='visible')void refreshAccount();};
    window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);
    const timer=setInterval(refresh,60000);
    return()=>{window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);clearInterval(timer);};
  },[status,refreshAccount]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),5500);return()=>clearTimeout(timer);},[toast]);
  const value:LiveContextValue={status,error,session,api,preferences:prefs,refreshAccount,
    refreshIdentity:async()=>{await liveAuth.reload();await syncIdentity();},logout,
    savePreferences:async patch=>{const version=epoch.current;const response=await api.json<{preferences:LivePreferences}>('/preferences',{method:'PATCH',body:JSON.stringify({preferences:patch})});if(version===epoch.current)setPrefs(response.preferences);},
  };
  const user=session?toPresentationUser(session):null;
  const appearance=prefs.appearance||{};
  const displayPreferences={...preferences,reducedMotion:appearance.reducedMotion===true,snow:appearance.snow!==false,highContrast:appearance.highContrast===true};
  // Compatibility for existing presentation components only. This empty object
  // never reads fixture storage and is never used as a live data adapter.
  const state=emptyState();if(user)state.users=[user];
  const presentation:AppContextValue={state,user,personas:[],preferences:displayPreferences,toast,notify:setToast,logout,
    loginPersona:unavailable,resetDemo:unavailable,saveProfile:unavailable,savePreferences:unavailable,
    saveDraft:unavailable,getDraft:()=>({}),createRecording:unavailable,updateRecording:unavailable,
    deleteRecording:unavailable,startJob:unavailable,cancelJob:unavailable,assign:unavailable,
    revoke:unavailable,reassign:unavailable,saveReview:unavailable,updateUser:unavailable,
    markNotification:unavailable,markAllRead:unavailable,saveSystem:unavailable,recordEvent:unavailable};
  return <LiveContext.Provider value={value}><Context.Provider value={presentation}>{children}</Context.Provider></LiveContext.Provider>;
}
