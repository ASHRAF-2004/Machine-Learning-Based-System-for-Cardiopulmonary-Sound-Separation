import {useEffect,useId,useRef,useState,type FormEvent} from 'react';
import {Link} from 'react-router-dom';
import {ArrowLeft,CheckCircle,ShieldCheck} from '@phosphor-icons/react';
import {UnsavedGuard} from '../components/ui';
import {useLive} from '../data/live';
import {ApiError} from '../data/api';
import type {LiveReview} from '../data/liveTypes';
import {MediaDetail,ResultDetail} from './RecordingDetail';
import {Button,CopyId,GlassPanel,Notice,SectionHeading} from './primitives';
import {dateLabel,errorMessage,useResource} from './data';
import {RequestState} from './WorkspaceViews';

export function AssignedReview({id}:{id:string}){
  const data=useResource<LiveReview>(`/assignments/${id}/review`),[lost,setLost]=useState(false);
  function refresh(){data.reload();window.dispatchEvent(new Event('sf-recheck-media'));}
  return <>
    <Link to="/app/shared?view=assigned" className="sf-text-link"><ArrowLeft size={16}/>Assigned reviews</Link>
    <header className="sf-page-heading sf-detail-heading"><div><h1>{!lost&&data.value?.recording_title||'Assigned review'}</h1><p>Review the exact resource, without changing the recording.</p>{!lost&&data.value&&<div className="sf-detail-meta"><span><ShieldCheck size={15}/>{data.value.resource_kind==='result'?'Result details only':'Original audio only'}</span>{data.value.recording_public_id&&<CopyId value={data.value.recording_public_id}/>} {data.value.assignment_public_id&&<CopyId value={data.value.assignment_public_id}/>}</div>}</div><Button variant="secondary" onClick={refresh}>Refresh access</Button></header>
    <RequestState {...data}/>
    {lost&&<Notice danger>Review access is no longer available. The protected resource and notes have been cleared. Return to Assigned reviews to check current access.</Notice>}
    {data.value&&!data.error&&!lost&&<>
      {data.value.resource_kind==='result'?<ResultDetail id={data.value.resource_id} embedded/>:<MediaDetail id={data.value.resource_id} kind={data.value.resource_kind||'assigned_resource'} embedded/>}
      <ReviewEditor key={id} review={data.value} onRefresh={data.reload} onLost={()=>{setLost(true);data.reload();}}/>
    </>}
  </>;
}

type Draft=Pick<LiveReview,'decision'|'notes'>;
function fields(review:LiveReview):Draft{return {decision:review.decision,notes:review.notes};}
function ReviewEditor({review,onRefresh,onLost}:{review:LiveReview;onRefresh:()=>void;onLost:()=>void}){
  const {api}=useLive(),[draft,setDraft]=useState<Draft>(()=>fields(review)),[baseline,setBaseline]=useState<Draft>(()=>fields(review));
  const outcomeId=useId(),notesId=useId(),notesHelpId=useId();
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false);
  const request=useRef<AbortController|null>(null),dirty=draft.notes!==baseline.notes||draft.decision!==baseline.decision,dirtyRef=useRef(dirty);dirtyRef.current=dirty;
  useEffect(()=>{if(!dirtyRef.current){setDraft(fields(review));setBaseline(fields(review));}},[review]);
  useEffect(()=>()=>request.current?.abort(),[api]);
  async function save(event:FormEvent){
    event.preventDefault();if(busy||!dirty)return;
    const controller=new AbortController();request.current=controller;setBusy(true);setError('');setSaved(false);
    try{
      const value=await api.json<LiveReview>(`/assignments/${review.assignment_id}/review`,{method:'PUT',signal:controller.signal,body:JSON.stringify(draft)});
      if(!controller.signal.aborted){setBaseline(fields(value));setDraft(fields(value));setSaved(true);onRefresh();}
    }catch(failure){if(!controller.signal.aborted){if(failure instanceof ApiError&&[401,403,404].includes(failure.status)){setDraft({decision:'pending',notes:''});onLost();}else setError(errorMessage(failure));}}
    finally{if(!controller.signal.aborted)setBusy(false);}
  }
  return <GlassPanel className="sf-review-editor" label="Your review">
    <SectionHeading title="Your review" description="Useful observations for the owner. Not a clinical diagnosis."/>
    <form onSubmit={save}>
      <div className="sf-field"><label htmlFor={outcomeId}>Review outcome</label><select id={outcomeId} value={draft.decision} disabled={busy} onChange={event=>{setDraft({...draft,decision:event.target.value as LiveReview['decision']});setSaved(false);}}><option value="pending">Not reviewed</option><option value="accepted">Reviewed</option><option value="needs_attention">Needs attention</option></select></div>
      <div className="sf-field"><label htmlFor={notesId}>Review notes</label><textarea id={notesId} aria-describedby={notesHelpId} rows={5} maxLength={10000} value={draft.notes} disabled={busy} onChange={event=>{setDraft({...draft,notes:event.target.value});setSaved(false);}}/><small id={notesHelpId}>No patient identifiers. Up to 10,000 characters; notes are saved only after you press Save review.</small></div>
      {error&&<Notice danger>{error}</Notice>}{saved&&<p className="sf-account-saved" role="status"><CheckCircle size={17}/>Review saved.</p>}
      <div className="sf-review-save"><span>{review.updated_at==null?'No saved review yet':`Last saved ${dateLabel(review.updated_at)}`}</span><div>{dirty&&<Button variant="ghost" disabled={busy} onClick={()=>{setDraft(baseline);setError('');setSaved(false);}}>Discard changes</Button>}<Button type="submit" disabled={busy||!dirty}>{busy?'Saving…':'Save review'}</Button></div></div>
    </form>
    <UnsavedGuard when={dirty&&!busy}/>
  </GlassPanel>;
}
