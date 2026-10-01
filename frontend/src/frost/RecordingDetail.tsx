import {useRef,useState,type ReactNode} from 'react';
import {Link,Navigate} from 'react-router-dom';
import {ArrowLeft,LockSimple,ShareNetwork,SpinnerGap} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import type {LiveJob,LiveRecording,LiveResult} from '../data/liveTypes';
import {AudioWorkspace} from './AudioWorkspace';
import {Button,CopyId,GlassPanel,Notice,StatusChip} from './primitives';
import {dateLabel,errorMessage,useLibrary,useResource} from './data';
import {Progress,RequestState} from './WorkspaceViews';
import {TechnicalDetails} from './TechnicalDetails';
import {OwnerReviewFeedback} from './OwnerReviewFeedback';
export function RecordingDetail({id,ownerTools}:{id:string;ownerTools?:(record:LiveRecording)=>ReactNode}){
  const {api,session}=useLive(),record=useResource<LiveRecording>(`/recordings/${id}`),library=useLibrary();
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[requesting,setRequesting]=useState(false),[submitted,setSubmitted]=useState<LiveJob|null>(null),[editTitle,setEditTitle]=useState('');
  const tools=useRef<HTMLDetailsElement>(null);
  const listed=library.items.find(i=>i.recording.id===id);
  const jobData=useResource<LiveJob>(submitted?`/jobs/${submitted.id}`:listed?.job?`/jobs/${listed.job.id}`:null,j=>['queued','processing'].includes(j.status));
  const job=jobData.error?undefined:jobData.value||submitted||listed?.job;
  const resultData=useResource<LiveResult>(job?.result_id?`/results/${job.result_id}`:listed?.result?`/results/${listed.result.id}`:null);
  const result=resultData.error?undefined:resultData.value||listed?.result;
  const status=result||job?.status==='succeeded'?'ready':job?.status==='failed'?'failed':job?'processing':library.collection&&record.value?.is_owner?'recorded':null;
  const resources=record.value?[...record.value.resources.filter(r=>['original_audio','heart_audio','lung_audio'].includes(r.kind)),...(result?.resources||[])].filter((r,i,array)=>array.findIndex(v=>v.id===r.id)===i):[];
  const active=job?.status==='queued'||job?.status==='processing';
  async function separate(){if(requesting||active)return;setRequesting(true);setError('');try{const value=await api.json<LiveJob>(`/recordings/${id}/jobs`,{method:'POST',body:'{}'});setSubmitted(value);library.reload();}catch(failure){setError(errorMessage(failure));}finally{setRequesting(false);}}
  function refresh(){record.reload();library.reload();jobData.reload();resultData.reload();window.dispatchEvent(new Event('sf-recheck-media'));}
  function openSharing(){if(tools.current){tools.current.open=true;tools.current.scrollIntoView({block:'center'});(tools.current.querySelector<HTMLElement>('.sf-sharing input')||tools.current.querySelector<HTMLElement>('summary'))?.focus({preventScroll:true});}}
  return <><Link to="/app/library" className="sf-text-link"><ArrowLeft size={16}/>Library</Link><header className="sf-page-heading sf-detail-heading"><div><h1>{record.value?.title||'Recording'}</h1>{record.value&&<div className="sf-detail-meta">{status&&<StatusChip status={status}/>}<span>{dateLabel(record.value.created_at)}</span>{record.value.public_id&&<CopyId value={record.value.public_id}/>}<span><LockSimple size={14}/>{record.value.is_owner?'Private · Owner':'Explicit shared access'}</span></div>}</div><div className="sf-heading-actions"><Button variant="secondary" onClick={refresh}>Refresh access</Button>{record.value?.is_owner&&(status==='ready'?<Button variant="secondary" onClick={openSharing}><ShareNetwork size={19}/>Share</Button>:<Button disabled={busy||requesting||active||status==='failed'||!session?.capabilities.separation} onClick={()=>void separate()}>{requesting||active?<><SpinnerGap className="sf-working-spinner" size={18}/>{requesting?'Starting…':job?.status==='queued'?'Queued…':'Separating…'}</>:'Separate'}</Button>)}</div></header>
  <RequestState {...record}/>{error&&<Notice danger>{error}</Notice>}
  {record.value&&<>
    {requesting?<Progress status="requesting" title={record.value.title}/>:job&&job.status!=='succeeded'&&<Progress status={job.status} title={record.value.title}/>}
    {job?.status==='failed'&&<Notice danger>Separation did not complete. Your original is unchanged. Contact the project owner with the processing identifier in Technical details. This model/version does not support creating a new retry job.</Notice>}
    {record.value.is_owner&&!session?.capabilities.separation&&<Notice>Separation is temporarily unavailable. Your original is saved.</Notice>}
    {library.error&&<Notice danger>Processing status unavailable. {library.error}</Notice>}
    {jobData.error&&<Notice danger>{jobData.error}</Notice>}{resultData.error&&<Notice danger>{resultData.error}</Notice>}
    <AudioWorkspace key={`${id}:${session!.user.uid}:${resources.map(r=>r.id).join(':')}`} resources={resources} provider={api} filenames={{original:record.value.original_filename||'original.wav',heart:'heart.wav',lung:'lung.wav'}}/>
    <TechnicalDetails record={record.value} result={result} job={job}/>
    {record.value.is_owner&&<OwnerReviewFeedback key={`${id}:${session!.user.uid}`} id={id} onRequest={openSharing}/>}
    {record.value.is_owner&&<details ref={tools} className="sf-owner-tools"><summary>Recording title & sharing</summary><GlassPanel><form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await api.json(`/recordings/${id}`,{method:'PATCH',body:JSON.stringify({title:editTitle.trim()})});record.reload();library.reload();}catch(failure){setError(errorMessage(failure));}finally{setBusy(false);}}}><label className="sf-field"><span>Recording title</span><input required maxLength={200} value={editTitle} placeholder={record.value.title} onChange={e=>setEditTitle(e.target.value)}/></label><Button type="submit" variant="secondary" disabled={busy||!editTitle.trim()}>Save title</Button></form></GlassPanel>{ownerTools?.(record.value)}</details>}
  </>}
  </>;
}
export function ResultDetail({id,embedded=false}:{id:string;embedded?:boolean}){
  const {api}=useLive(),data=useResource<LiveResult>(`/results/${id}`);
  const Heading=embedded?'h2':'h1';
  return <><header className="sf-page-heading sf-detail-heading"><div><Heading>Separation result</Heading><p>{data.value?dateLabel(data.value.created_at):'Shared results are authorized independently.'}</p>{data.value?.public_id&&<CopyId value={data.value.public_id}/>}</div><Button variant="secondary" onClick={()=>{data.reload();window.dispatchEvent(new Event('sf-recheck-media'));}}>Refresh access</Button></header><RequestState {...data}/>{data.value&&<><AudioWorkspace key={`${id}:${data.value.resources.map(r=>r.id).join(':')}`} resources={data.value.resources} provider={api}/><TechnicalDetails result={data.value}/></>}</>;
}
export function MediaDetail({id,kind,embedded=false}:{id:string;kind?:string;embedded?:boolean}){
  const {api}=useLive(),data=useResource<{items:LiveRecording[]}>(kind?null:'/recordings');
  const resource=kind?{id,kind,media_type:'audio/wav',url:null}:data.value?.items.flatMap(r=>r.resources).find(r=>r.id===id);
  const Heading=embedded?'h2':'h1';
  return <><header className="sf-page-heading"><div><Heading>Shared audio</Heading><p>Only this exact shared resource is opened.</p></div></header>{!kind&&<RequestState {...data}/>}{resource?<AudioWorkspace key={id} provider={api} resources={[resource]}/>:!data.loading&&!data.error?<Notice>This audio is not included in your current access.</Notice>:null}<details className="sf-technical"><summary>Technical details</summary><CopyId value={id}/></details></>;
}
export function LegacyJob({id}:{id:string}){const data=useResource<LiveJob>(`/jobs/${id}`);return data.value?<Navigate replace to={`/app/recordings/${data.value.recording_id}`}/>:<RequestState {...data}/>;}
