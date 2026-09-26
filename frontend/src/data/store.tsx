import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import {DEMO_ENABLED} from '../brand';
import {LiveAppProvider} from './live';
import {createFixtures,defaultPreferences,personas} from './fixtures';
import type {DemoState,User,Recording,ProcessingJob,SeparationResult,Assignment,Review,UserPreferences,Role,UserStatus} from './types';
const KEY='stethofuse-demo-v1'; const SESSION='stethofuse-demo-persona';
let displayPreferences=defaultPreferences;
const now=()=>new Date().toISOString();
const id=(prefix:string)=>`${prefix}-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2,5).toUpperCase()}`;
function restore(raw:string|null):DemoState|null {if(!raw)return null;try{const parsed=JSON.parse(raw);if(!['users','recordings','jobs','results','assignments','reviews','notifications','audit'].every(key=>Array.isArray(parsed[key]))||!parsed.preferences||!parsed.system)return null;return {...parsed,drafts:parsed.drafts||{},preferences:Object.fromEntries(Object.entries(parsed.preferences).map(([uid,prefs])=>[uid,{...defaultPreferences,...(prefs as Partial<UserPreferences>)}]))};}catch{return null;}}
function load():DemoState {if(!DEMO_ENABLED)return createFixtures();try{return restore(localStorage.getItem(KEY))||createFixtures();}catch{return createFixtures();}}
export function canAccess(state:DemoState,user:User|null,recordingId:string){if(!user||user.status!=='active')return false;const r=state.recordings.find(r=>r.id===recordingId);return !!r&&(r.ownerId===user.id||state.assignments.some(a=>a.recordingId===recordingId&&a.analystId===user.id&&a.status!=='revoked'));}
function reviewNotifications(state:DemoState,userId:string,title:string,body:string,href:string):DemoState['notifications'] {return (state.preferences[userId]?.reviewNotifications??defaultPreferences.reviewNotifications)?[{id:id('NTF'),userId,title,body,href,read:false,createdAt:now()},...state.notifications]:state.notifications;}
export interface AppContextValue {
 state:DemoState;user:User|null;personas:User[];preferences:UserPreferences;toast:string;
 notify:(message:string)=>void;loginPersona:(id:string)=>void;logout:()=>void|Promise<void>;resetDemo:()=>void;
 saveProfile:(patch:Pick<User,'name'>)=>void;savePreferences:(patch:Partial<UserPreferences>)=>void;
 saveDraft:(key:string,values:Record<string,string>)=>void;getDraft:(key:string)=>Record<string,string>;
 createRecording:(values:Omit<Recording,'id'|'ownerId'|'createdAt'|'isDemo'|'archived'>)=>string;
 updateRecording:(id:string,patch:Partial<Pick<Recording,'title'|'archived'|'metadata'>>)=>void;deleteRecording:(id:string)=>void;
 startJob:(recordingId:string)=>string;cancelJob:(id:string)=>void;
 assign:(recordingId:string,analystId:string,permission?:'review'|'listen')=>string;revoke:(id:string)=>void;reassign:(id:string,analystId:string)=>void;
 saveReview:(assignmentId:string,notes:Review['notes'],summary:string,decision:Review['decision'])=>void;
 updateUser:(id:string,patch:{role?:Role;status?:UserStatus})=>void;
 markNotification:(id:string,read:boolean)=>void;markAllRead:()=>void;
 saveSystem:(patch:Partial<DemoState['system']>)=>void;recordEvent:(action:string,targetId:string,detail:string)=>void;
}
export const Context=createContext<AppContextValue|null>(null);
export function AppProvider({children}:{children:ReactNode}) {
 return DEMO_ENABLED?<DemoAppProvider>{children}</DemoAppProvider>:<LiveAppProvider>{children}</LiveAppProvider>;
}
function DemoAppProvider({children}:{children:ReactNode}) {
 const [state,setState]=useState(load); const [persona,setPersona]=useState(()=>DEMO_ENABLED?sessionStorage.getItem(SESSION):null);const [toast,setToast]=useState('');
 const user=state.users.find(u=>u.id===persona)||null;
 useEffect(()=>{if(!DEMO_ENABLED)return;const receive=(event:StorageEvent)=>{if(event.key!==KEY||event.storageArea!==localStorage)return;const next=restore(event.newValue);if(next)setState(current=>JSON.stringify(current)===JSON.stringify(next)?current:next);};window.addEventListener('storage',receive);return()=>window.removeEventListener('storage',receive);},[]);
 useEffect(()=>{if(DEMO_ENABLED){try{const serialized=JSON.stringify(state);if(localStorage.getItem(KEY)!==serialized)localStorage.setItem(KEY,serialized);}catch{setToast('Browser storage is full. Changes remain in this tab only.');}}},[state]);
 useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),5500);return()=>clearTimeout(timer);},[toast]);
 useEffect(()=>{if(!DEMO_ENABLED)return;const timer=setInterval(()=>setState(s=>{
   if(!s.jobs.some(j=>['queued','processing'].includes(j.status)))return s;
   const results=[...s.results];const notifications=[...s.notifications];
   const jobs=s.jobs.map(j=>{if(!['queued','processing'].includes(j.status))return j;const stage=Math.min(5,Math.floor((Date.now()-Date.parse(j.startedAt))/4500));if(stage===j.stage&&j.status==='processing')return j;
    if(stage===5){const resultId=id('RES');results.unshift({id:resultId,recordingId:j.recordingId,ownerId:j.ownerId,jobId:j.id,createdAt:now(),status:'completed',run:{id:id('RUN'),jobId:j.id,version:j.ensembleVersion,fusion:s.system.fusion,referenceAvailable:false,experts:[{name:'NeoSSNet',version:'candidate',status:'Simulated'},{name:'NMF / NMCF',version:'verification pending',status:'Simulated'},{name:'DAE-NMF-VMD',version:'verification pending',status:'Simulated'}]}});if(s.preferences[j.ownerId]?.jobNotifications??defaultPreferences.jobNotifications)notifications.unshift({id:id('NTF'),userId:j.ownerId,title:'Demo separation is ready',body:'Synthetic outputs are available. No model inference was run.',href:`/app/results/${resultId}`,read:false,createdAt:now()});return {...j,stage,status:'completed' as const,resultId,updatedAt:now()};}
    return {...j,stage,status:'processing' as const,updatedAt:now()};});return {...s,jobs,results,notifications};}),1500);return()=>clearInterval(timer);},[]);
 const notify=(message:string)=>setToast(message);
 function requireUser(){if(!DEMO_ENABLED||!user||user.status!=='active')throw new Error('An active demo account is required.');return user;}
 function requireAdmin(){const u=requireUser();if(u.role!=='admin')throw new Error('Administrator access required.');return u;}
 function requireOwner(recordingId:string){const u=requireUser();if(!state.recordings.some(r=>r.id===recordingId&&r.ownerId===u.id))throw new Error('This recording belongs to another account.');return u;}
 const event=(s:DemoState,action:string,targetId:string,detail:string,outcome:'success'|'blocked'='success')=>({...s,audit:[{id:id('EVT'),actorId:user?.id||'DEMO',action,targetId,detail,outcome,time:now()},...s.audit]});
 displayPreferences={...defaultPreferences,...state.preferences[user?.id||'']};
 const value:AppContextValue={state,user,personas,preferences:displayPreferences,toast,notify,
  loginPersona:(pid)=>{if(!DEMO_ENABLED)return;const p=state.users.find(u=>u.id===pid);if(!p)throw new Error('Unknown demo account.');sessionStorage.setItem(SESSION,pid);setPersona(pid);},
  logout:()=>{sessionStorage.removeItem(SESSION);setPersona(null);},
  resetDemo:()=>{if(DEMO_ENABLED){setState(createFixtures());notify('Fictional workspace reset.');}},
  saveProfile:patch=>{const u=requireUser();setState(s=>({...s,users:s.users.map(x=>x.id===u.id?{...x,name:patch.name.trim()}:x)}));notify('Profile saved in this browser.');},
  savePreferences:patch=>{const u=requireUser();setState(s=>({...s,preferences:{...s.preferences,[u.id]:{...defaultPreferences,...s.preferences[u.id],...patch}}}));notify('Preferences saved.');},
  saveDraft:(key,values)=>{const u=requireUser();setState(s=>({...s,drafts:{...s.drafts,[`${u.id}:${key}`]:values}}));},getDraft:key=>state.drafts[`${user?.id}:${key}`]||{},
  createRecording:values=>{const u=requireUser();const rid=id('REC');setState(s=>event({...s,recordings:[{...values,id:rid,ownerId:u.id,createdAt:now(),isDemo:true,archived:false},...s.recordings]},'Recording created',rid,'Demo metadata only; no audio uploaded or persisted.'));notify('Demo recording saved. No audio uploaded.');return rid;},
  updateRecording:(rid,patch)=>{requireOwner(rid);setState(s=>event({...s,recordings:s.recordings.map(r=>r.id===rid?{...r,...patch}:r)},'Recording updated',rid,'Owner changed metadata.'));notify('Recording updated.');},
  deleteRecording:rid=>{requireOwner(rid);setState(s=>event({...s,recordings:s.recordings.filter(r=>r.id!==rid),jobs:s.jobs.filter(j=>j.recordingId!==rid),results:s.results.filter(r=>r.recordingId!==rid),assignments:s.assignments.filter(a=>a.recordingId!==rid),reviews:s.reviews.filter(v=>!s.assignments.some(a=>a.recordingId===rid&&a.id===v.assignmentId))},'Recording deleted',rid,'Demo metadata and related runs removed.'));notify('Demo recording deleted.');},
  startJob:rid=>{const u=requireOwner(rid);if(state.jobs.some(j=>j.recordingId===rid&&['queued','processing'].includes(j.status)))throw new Error('This recording already has an active job.');const jid=id('JOB');const job:ProcessingJob={id:jid,recordingId:rid,ownerId:u.id,status:'queued',stage:0,startedAt:now(),updatedAt:now(),ensembleVersion:'research-preview.1'};setState(s=>event({...s,jobs:[job,...s.jobs]},'Ensemble requested',jid,'Simulated stages; no algorithm ran.'));return jid;},
  cancelJob:jid=>{const j=state.jobs.find(j=>j.id===jid);if(!j)throw new Error('Job not found.');requireOwner(j.recordingId);setState(s=>({...s,jobs:s.jobs.map(j=>j.id===jid&&['queued','processing'].includes(j.status)?{...j,status:'cancelled',updatedAt:now()}:j)}));notify('Demo job cancelled.');},
  assign:(rid,analystId,permission='review')=>{const u=requireOwner(rid);const recipient=state.users.find(x=>x.id===analystId&&x.status==='active');if(!recipient||recipient.id===u.id||(permission==='review'&&recipient.role!=='analyst'))throw new Error('Choose an active analyst for review, or another active account for listening.');if(state.assignments.some(a=>a.recordingId===rid&&a.analystId===analystId&&a.status!=='revoked'))throw new Error('This account already has access.');const aid=id('ASN');const assignment:Assignment={id:aid,recordingId:rid,ownerId:u.id,analystId,permission,status:'pending',createdAt:now(),updatedAt:now()};setState(s=>event({...s,assignments:[assignment,...s.assignments],notifications:reviewNotifications(s,analystId,'A recording was shared with you',`${u.name} granted ${permission} access.`,permission==='review'?`/app/reviews/${aid}`:`/app/recordings/${rid}`)},'Access granted',aid,`${permission} access to ${rid} for ${analystId}.`));notify('Demo access granted.');return aid;},
  revoke:aid=>{const u=requireUser();const a=state.assignments.find(a=>a.id===aid);if(!a||(a.ownerId!==u.id&&u.role!=='admin'))throw new Error('You cannot revoke this assignment.');setState(s=>event({...s,notifications:reviewNotifications(s,a.analystId,'Recording access was revoked','An owner or administrator removed this share. Private content is no longer available.','/app/shared'),assignments:s.assignments.map(a=>a.id===aid?{...a,status:'revoked',updatedAt:now()}:a)},'Access revoked',aid,'Content access removed immediately.'));notify('Access revoked.');},
  reassign:(aid,analystId)=>{
   requireAdmin();const assignment=state.assignments.find(a=>a.id===aid);
   if(!assignment)throw new Error('Assignment not found.');
   if(!state.users.some(u=>u.id===analystId&&u.role==='analyst'&&u.status==='active'))throw new Error('Choose an active analyst.');
   if(assignment.analystId===analystId)throw new Error('Choose a different analyst. The existing assignment and review have not changed.');
   if(assignment.ownerId===analystId)throw new Error('The recording owner already has access. Choose another analyst.');
   if(state.assignments.some(a=>a.recordingId===assignment.recordingId&&a.analystId===analystId&&a.status!=='revoked'))throw new Error('This analyst already has an active assignment for this recording.');
   const replacementId=id('ASN'),timestamp=now();
   const replacement:Assignment={id:replacementId,recordingId:assignment.recordingId,ownerId:assignment.ownerId,analystId,permission:assignment.permission,status:'pending',createdAt:timestamp,updatedAt:timestamp};
   setState(s=>{
    // An assignment is also the review's authorship boundary. Retire the old
    // grant instead of moving its saved review or recovery draft to a new user.
    let next:DemoState={...s,assignments:[replacement,...s.assignments.map(a=>a.id===aid?{...a,status:'revoked' as const,updatedAt:timestamp}:a)]};
    if(assignment.status!=='revoked'){
     next={...next,notifications:reviewNotifications(next,assignment.analystId,'Recording access was reassigned','An administrator removed this assignment. Your previous review remains in its history.','/app/shared')};
     next=event(next,'Access revoked',aid,`Reassigned through ${replacementId}; previous review authorship retained.`);
    }
    next={...next,notifications:reviewNotifications(next,analystId,'A recording was assigned to you',assignment.permission==='review'?'An administrator created a new assignment. Your review starts with an empty draft.':'An administrator created a new explicit listening grant.',assignment.permission==='review'?`/app/reviews/${replacementId}`:`/app/recordings/${assignment.recordingId}`)};
    return event(next,'Assignment changed',replacementId,`New ${assignment.permission} assignment for ${analystId}, replacing ${aid}.`);
   });
   notify('New assignment created. The previous review history is preserved.');
  },
  saveReview:(aid,notes,summary,decision)=>{const u=requireUser();const a=state.assignments.find(a=>a.id===aid);if(u.role!=='analyst'||!a||a.analystId!==u.id||a.permission!=='review'||a.status==='revoked')throw new Error('An active review assignment is required.');const review:Review={id:state.reviews.find(r=>r.assignmentId===aid)?.id||id('REV'),assignmentId:aid,authorId:u.id,notes,summary,decision,updatedAt:now()};setState(s=>event({...s,notifications:decision==='draft'?s.notifications:reviewNotifications(s,a.ownerId,decision==='reviewed'?'A recording review is complete':'A new recording was requested','An assigned analyst saved a non-diagnostic review. No email was sent.',`/app/recordings/${a.recordingId}`),reviews:[review,...s.reviews.filter(r=>r.assignmentId!==aid)],assignments:s.assignments.map(x=>x.id===aid?{...x,status:decision==='draft'?'in-review':decision,updatedAt:now()}:x)},decision==='draft'?'Review draft saved':'Review submitted',aid,'Non-diagnostic review.'));notify(decision==='draft'?'Review draft saved.':'Review decision submitted.');},
  updateUser:(uid,patch)=>{requireAdmin();const target=state.users.find(u=>u.id===uid);if(!target)throw new Error('Account not found.');if(target.role==='admin'&&target.status==='active'&&((patch.role&&patch.role!=='admin')||(patch.status&&patch.status!=='active'))&&state.users.filter(u=>u.role==='admin'&&u.status==='active').length===1){setState(s=>event(s,'Last administrator protected',uid,'Cannot remove or disable the last active administrator.','blocked'));throw new Error('The last active administrator cannot be disabled or demoted.');}setState(s=>event({...s,users:s.users.map(u=>u.id===uid?{...u,...patch}:u)},'Account updated',uid,JSON.stringify(patch)));notify('Demo account updated.');},
  markNotification:(nid,read)=>{const u=requireUser();setState(s=>({...s,notifications:s.notifications.map(n=>n.id===nid&&n.userId===u.id?{...n,read}:n)}));},markAllRead:()=>{const u=requireUser();setState(s=>({...s,notifications:s.notifications.map(n=>n.userId===u.id?{...n,read:true}:n)}));},
  saveSystem:patch=>{requireAdmin();setState(s=>event({...s,system:{...s.system,...patch}},'Demo configuration saved','SYSTEM','No backend or deployment configuration changed.'));notify('Demo configuration saved. No live settings changed.');},
  recordEvent:(action,targetId,detail)=>{requireUser();setState(s=>event(s,action,targetId,detail));notify('Demo request recorded. No external action taken.');}
 };
 return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useApp(){const context=useContext(Context);if(!context)throw new Error('AppProvider missing');return context;}
export function formatDate(value:string){const date=new Date(value);if(Number.isNaN(date.getTime()))return 'Unavailable';if(displayPreferences.dateFormat==='iso')return date.toISOString().slice(0,10);return new Intl.DateTimeFormat(displayPreferences.dateFormat==='month-first'?'en-US':'en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:value.length===10?'UTC':displayPreferences.timezone}).format(date);}
export function formatDuration(seconds:number){return `${Math.floor(seconds/60)}:${String(Math.round(seconds%60)).padStart(2,'0')}`;}
export const roleLabel=(role:Role)=>({staff:'Healthcare Staff',analyst:'Audio Analyst',admin:'Administrator'}[role]);
