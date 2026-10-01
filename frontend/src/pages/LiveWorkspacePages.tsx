import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react';
import {Link,Navigate,useLocation,useNavigate,useSearchParams} from 'react-router-dom';
import {ArrowRight,Plus,UploadSimple} from '@phosphor-icons/react';
import Shell from '../frost/Shell';
import {Overview as FrostOverview,Library as FrostLibrary} from '../frost/WorkspaceViews';
import {NewRecording as FrostNewRecording,Upload as FrostUpload,RecordingComingSoon} from '../frost/Upload';
import {RecordingDetail as FrostRecordingDetail,ResultDetail as FrostResultDetail,MediaDetail,LegacyJob} from '../frost/RecordingDetail';
import FrostAccount from '../frost/Account';
import {Sharing} from '../frost/Sharing';
import {Badge,Button,CopyId,Empty,ErrorState,Field,Notice,PageHeading,Panel,Skeleton,StatStrip,Status,Table,UnsavedGuard} from '../components/ui';
import {useLive} from '../data/live';
import {useApp} from '../data/store';
import {liveRoleLabel,type LiveAudit,type LiveGrant,type LiveJob,type LivePreferences,type LiveRecording,type LiveResult,type LiveReview,type LiveRole,type LiveStatus,type LiveUser,type MediaResource} from '../data/liveTypes';
import {ApiError} from '../data/api';
import './workspace-pages.css';
import './account-pages.css';

const date=(seconds:number|null)=>seconds?new Date(seconds*1000).toLocaleString():'Not saved';
const message=(error:unknown)=>error instanceof Error?error.message:'The operation could not be completed.';
function useRemote<T>(path:string,poll=false){
 const {api}=useLive();const [response,setResponse]=useState<{data:T;path:string;client:typeof api}|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[version,setVersion]=useState(0);
 const value=response?.path===path&&response.client===api?response.data:null;
 useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');
  if(!poll)setResponse(null);
  void api.json<T>(path,{signal:controller.signal}).then(data=>{if(!controller.signal.aborted)setResponse({data,path,client:api});}).catch(failure=>{if(!controller.signal.aborted){setResponse(null);setError(message(failure));}}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[api,path,version]);
 useEffect(()=>{if(!poll)return;const timer=setInterval(()=>setVersion(v=>v+1),2000);return()=>clearInterval(timer);},[poll]);
 return {value,error,loading,reload:()=>setVersion(v=>v+1)};
}
function RequestState({loading,error,reload}:{loading:boolean;error:string;reload:()=>void}){return loading?<Skeleton/>:error?<ErrorState message={error} onRetry={reload}/>:null;}
function Unavailable({title,detail}:{title:string;detail:string}){return <><PageHeading title={title} description="Live workspace"/><Notice title="Not connected in this milestone"><p>{detail}</p><p>No fictional values or simulated completion are substituted.</p></Notice><Button to="/app/dashboard" variant="secondary">Back to workspace</Button></>;}

function Assignments(){
 const data=useRemote<{items:LiveGrant[]}>('/assignments');
 return <><PageHeading title="Review queue" description="Your active exact-resource analyst assignments." actions={<Button variant="secondary" onClick={data.reload}>Refresh access</Button>}/><RequestState {...data}/>{!data.loading&&!data.error&&(data.value?.items.length?<Table headers={['Assignment','Recording','Resource','Created','']} caption="Analyst assignments">{data.value.items.map(grant=><tr key={grant.id}><td><CopyId value={grant.id}/></td><td>{grant.recording_id}</td><td>{grant.resource_id}</td><td>{date(grant.created_at)}</td><td><Link className="inline-link" to={`/app/reviews/${grant.id}`}>Review <ArrowRight size={16}/></Link></td></tr>)}</Table>:<Empty title="No active assignments" description="Give the owner your @handle from Profile & settings. They can assign one exact original-audio or result resource for review."/>)}</>;
}
function Review({id}:{id:string}){
 const {api}=useLive();const data=useRemote<LiveReview>(`/assignments/${id}/review`);const [notes,setNotes]=useState(''),[decision,setDecision]=useState<LiveReview['decision']>('pending'),[error,setError]=useState(''),[busy,setBusy]=useState(false),[saved,setSaved]=useState(false);
 useEffect(()=>{if(data.value){setNotes(data.value.notes);setDecision(data.value.decision);}},[data.value]);
 const dirty=!!data.value&&(notes!==data.value.notes||decision!==data.value.decision);
 async function save(e:FormEvent){e.preventDefault();setBusy(true);setError('');setSaved(false);try{await api.json(`/assignments/${id}/review`,{method:'PUT',body:JSON.stringify({decision,notes})});setSaved(true);data.reload();}catch(failure){setError(message(failure));}finally{setBusy(false);}}
 return <><PageHeading title="Assigned review" description="A non-diagnostic review of the exact assigned resource."/><RequestState {...data}/>{data.value&&<>{data.value.resource_kind==='result'?<FrostResultDetail id={data.value.resource_id} embedded/>:<MediaDetail id={data.value.resource_id} kind={data.value.resource_kind||'assigned_resource'} embedded/>}<Panel title="Review notes"><form onSubmit={save}><Field label="Review decision"><select value={decision} onChange={e=>setDecision(e.target.value as LiveReview['decision'])}><option value="pending">Pending</option><option value="accepted">Reviewed</option><option value="needs_attention">Needs attention / re-record</option></select></Field><Field label="Non-diagnostic notes" hint="Do not include patient identifiers. Maximum 10,000 characters."><textarea rows={7} maxLength={10000} value={notes} onChange={e=>setNotes(e.target.value)}/></Field>{error&&<ErrorState message={error}/>} {saved&&<p role="status">Review saved by the server.</p>}<Button type="submit" disabled={busy||!dirty}>{busy?'Saving…':'Save review'}</Button></form></Panel><UnsavedGuard when={dirty&&!busy}/></>}</>;
}

function AdminUsers(){
 const {api,refreshAccount,session}=useLive();const data=useRemote<{items:LiveUser[]}>('/admin/users');const [search,setSearch]=useState('');
 useEffect(()=>{void refreshAccount();},[refreshAccount]);
 const currentUid=session?.user.uid;
 return <><PageHeading title="Users" description="Backend-authorized account metadata; private recordings are not included."/><Field label="Search users"><input type="search" value={search} onChange={e=>setSearch(e.target.value)}/></Field><RequestState {...data}/>{data.value&&<Table headers={['User / application ID','Email','Role','Status','Action']} caption="Application users">{data.value.items.filter(u=>`${u.id} ${u.email} ${u.display_name}`.toLowerCase().includes(search.toLowerCase())).map(user=><AdminUserRow key={`${user.id}:${user.uid}:${user.role}:${user.status}`} user={user} isCurrent={user.uid===currentUid} save={async(role,status)=>{await api.json(`/admin/users/${user.id}`,{method:'PATCH',body:JSON.stringify({role,status,confirmed_target_id:user.id})});await refreshAccount();data.reload();}}/>)}</Table>}</>;
}
function AdminUserRow({user,isCurrent,save}:{user:LiveUser;isCurrent:boolean;save:(role:LiveRole,status:LiveStatus)=>Promise<void>}){
 const [role,setRole]=useState(user.role),[status,setStatus]=useState(user.status),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{setRole(user.role);setStatus(user.status);},[user.role,user.status]);
 if(isCurrent)return <tr><td><strong>{user.display_name||'Research user'} <span className="user-you">You</span></strong><p><CopyId value={user.id}/></p></td><td>{user.email}</td><td><span className="role-static">{liveRoleLabel(user.role)}</span></td><td><span className="status-static">{user.status[0].toUpperCase()+user.status.slice(1)}</span></td><td><span className="note-text" title="Another Administrator must perform this action.">You cannot change your own role or account status.</span></td></tr>;
 return <tr><td><strong>{user.display_name||'Research user'}</strong><p><CopyId value={user.id}/></p></td><td>{user.email}</td><td><select aria-label={`Role for ${user.id}`} value={role} onChange={e=>setRole(e.target.value as LiveRole)}><option value="healthcare_staff">Healthcare Staff</option><option value="audio_analyst">Audio Analyst</option><option value="admin">Administrator</option></select></td><td><select aria-label={`Status for ${user.id}`} value={status} onChange={e=>setStatus(e.target.value as LiveStatus)}><option value="active">Active</option><option value="suspended">Suspended</option><option value="disabled">Disabled</option></select></td><td><Button disabled={busy||(role===user.role&&status===user.status)} onClick={async()=>{if(!window.confirm(`Change ${user.id} to ${role} / ${status}? This changes server-enforced access.`))return;setBusy(true);setError('');try{await save(role,status);}catch(failure){setError(message(failure));}finally{setBusy(false);}}}>{busy?'Saving…':'Confirm changes'}</Button>{error&&<p role="alert">{error}</p>}</td></tr>;
}
function AdminAudit(){const data=useRemote<{items:LiveAudit[]}>('/admin/audit');return <><PageHeading title="Audit log" description="Safe operational event metadata, without tokens or private review content."/><RequestState {...data}/>{data.value&&<Table headers={['Time','Actor','Action','Target']} caption="Operational audit">{data.value.items.map(event=><tr key={event.id}><td>{date(event.created_at)}</td><td>{event.actor_id}</td><td>{event.action}</td><td>{event.target_id}</td></tr>)}</Table>}</>;}
function AdminOverview(){const data=useRemote<{items:LiveUser[]}>('/admin/users');return <><PageHeading title="Administration overview" description="Operational metadata is separate from private audio access."/><RequestState {...data}/>{data.value&&<StatStrip items={[{label:'Application accounts',value:data.value.items.length},{label:'Active accounts',value:data.value.items.filter(u=>u.status==='active').length},{label:'Administrators',value:data.value.items.filter(u=>u.role==='admin').length}]}/>}<Panel title="Account administration"><div className="toolbar"><Button to="/app/admin/users">Manage users</Button><Button to="/app/admin/audit" variant="secondary">Audit log</Button></div><Notice>Private media still requires ownership or an explicit grant. No email address or browser role picker can bootstrap an administrator.</Notice></Panel></>;}
function LiveRoute(){
 const {pathname}=useLocation();
 if(pathname==='/app/dashboard')return <Navigate replace to="/app/overview"/>;
 if(pathname==='/app/overview'||pathname==='/app')return <FrostOverview/>;
 if(pathname==='/app/recordings')return <Navigate replace to="/app/library"/>;
 if(pathname==='/app/library')return <FrostLibrary/>;
 if(pathname==='/app/shared')return <FrostLibrary sharedOnly/>;
 if(pathname==='/app/recordings/new')return <FrostNewRecording/>;
 if(pathname==='/app/recordings/new/upload')return <FrostUpload/>;
 if(pathname==='/app/recordings/new/record')return <RecordingComingSoon/>;
 if(/^\/app\/recordings\/[^/]+$/.test(pathname))return <FrostRecordingDetail id={pathname.split('/')[3]} ownerTools={record=><Sharing record={record}/>}/>;
 if(pathname==='/app/processing')return <Navigate replace to="/app/library?filter=processing"/>;
 if(pathname==='/app/history')return <Navigate replace to="/app/library"/>;
 if(/^\/app\/processing\/[^/]+$/.test(pathname))return <LegacyJob id={pathname.split('/')[3]}/>;
 if(pathname==='/app/results')return <Navigate replace to="/app/library?filter=ready"/>;
 if(/^\/app\/results\/[^/]+$/.test(pathname))return <FrostResultDetail id={pathname.split('/')[3]}/>;
 if(/^\/app\/audio\/[^/]+$/.test(pathname))return <MediaDetail id={pathname.split('/')[3]}/>;
 if(['/app/review-queue','/app/assigned'].includes(pathname))return <Assignments/>;
 if(pathname==='/app/review-history')return <Unavailable title="Review history" detail="The current API exposes active assignments. Historical review retrieval is not connected to this screen yet; old notes are retained by the backend."/>;
 if(/^\/app\/reviews\/[^/]+$/.test(pathname))return <Review id={pathname.split('/')[3]}/>;
 if(pathname==='/app/profile'||pathname==='/app/settings')return <FrostAccount/>;
 if(pathname==='/app/admin')return <AdminOverview/>;
 if(pathname==='/app/admin/users')return <AdminUsers/>;
 if(pathname==='/app/admin/audit')return <AdminAudit/>;
 if(pathname==='/app/help')return <><PageHeading title="Help & guidance" description="Live research workspace"/><Panel title="Recording access"><p>Upload a non-sensitive PCM WAV. Your backend account owns the recording. Give another existing account an explicit read or exact-resource review grant from the recording page.</p><p>Use Revoke grant to remove one permission, or Revoke all access to remove all this recipient’s grants on a recording. Already downloaded files cannot be recalled.</p><p>Press Separate on a saved recording, then return to its processing job or result. Share result metadata and each desired audio output explicitly; a review assignment alone does not grant audio. Contact the project owner with failed job IDs.</p></Panel></>;
 return <Unavailable title={pathname.startsWith('/app/admin')?'Administrative feature unavailable':'Workspace feature unavailable'} detail="This screen has no connected M1 API yet. It cannot mutate local demo data in live mode."/>;
}
export default function LiveWorkspacePages(){
 const {status,error,session,refreshAccount,logout}=useLive(),location=useLocation();
 if(status==='loading')return <div className="workspace"><Skeleton/></div>;
 if(status==='expired')return <Navigate replace to={`/session-expired?returnTo=${encodeURIComponent(location.pathname)}`}/>;
 if(status==='unverified')return <Navigate replace to="/verify-email"/>;
 if(status==='disabled')return <Navigate replace to="/account-disabled"/>;
 if(status==='signed-out')return <Navigate replace to={`/login?returnTo=${encodeURIComponent(location.pathname)}`}/>;
 if(status==='error'||!session)return <div className="utility-screen"><div className="utility-inner"><h1>Workspace unavailable.</h1><ErrorState message={error||'Account services are unavailable.'} onRetry={()=>void refreshAccount()}/><div className="toolbar"><Button to="/login" variant="secondary">Back to sign in</Button><Button variant="ghost" onClick={()=>void logout()}>Sign out</Button></div></div></div>;
 const path=location.pathname,role=session.user.role;
 if((path.startsWith('/app/admin')&&role!=='admin')||(/^\/app\/(review-queue|assigned|reviews|review-history)(\/|$)/.test(path)&&role!=='audio_analyst'))return <Navigate replace to="/403"/>;
 return <Shell key={session.user.id}><div className="workspace-page"><LiveRoute key={path}/></div></Shell>;
}
