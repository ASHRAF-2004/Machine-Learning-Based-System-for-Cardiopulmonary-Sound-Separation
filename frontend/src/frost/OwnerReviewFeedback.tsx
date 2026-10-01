import {useCallback,useEffect,useId,useRef,useState} from 'react';
import {CaretDown,CaretUp,ClipboardText,SpinnerGap} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import type {OwnerReviewPage} from '../data/liveTypes';
import {Button,CopyId,GlassPanel,Notice,ProfileIdentity,SectionHeading} from './primitives';
import {ReviewStatus} from './AssignmentRows';
import {dateLabel,errorMessage} from './data';

/** Owner-only response, bounded three-row pages. Refresh discards previous pages. */
function useOwnerReviews(id:string){
  const {api}=useLive();
  const [response,setResponse]=useState<{client:typeof api;id:string;page:OwnerReviewPage}|null>(null);
  const [error,setError]=useState(''),[loading,setLoading]=useState(true),[more,setMore]=useState(false),[revision,setRevision]=useState(0);
  const nextRequest=useRef<AbortController|null>(null);
  const reload=useCallback(()=>setRevision(value=>value+1),[]);
  const value=response?.client===api&&response.id===id?response.page:null;
  useEffect(()=>{
    const controller=new AbortController();nextRequest.current?.abort();setMore(false);setResponse(null);setLoading(true);setError('');
    void api.json<OwnerReviewPage>(`/recordings/${id}/reviews`,{signal:controller.signal},{limit:3}).then(page=>{
      if(!controller.signal.aborted)setResponse({client:api,id,page});
    }).catch(failure=>{if(!controller.signal.aborted)setError(errorMessage(failure));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    const refresh=()=>{if(!document.hidden)reload();};
    window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);window.addEventListener('sf-review-updated',refresh);
    return()=>{controller.abort();nextRequest.current?.abort();window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);window.removeEventListener('sf-review-updated',refresh);};
  },[api,id,revision,reload]);
  async function loadMore(){
    if(!value||loading||more)return;
    const controller=new AbortController();nextRequest.current=controller;setMore(true);setError('');
    try{
      const page=await api.json<OwnerReviewPage>(`/recordings/${id}/reviews`,{signal:controller.signal},{limit:3,offset:value.items.length});
      if(!controller.signal.aborted)setResponse({client:api,id,page:{...page,items:[...value.items,...page.items].filter((item,index,items)=>items.findIndex(other=>other.assignment_id===item.assignment_id)===index)}});
    }catch(failure){if(!controller.signal.aborted){setResponse(null);setError(errorMessage(failure));}}
    finally{if(!controller.signal.aborted)setMore(false);}
  }
  function collapse(){nextRequest.current?.abort();setMore(false);if(value)setResponse({client:api,id,page:{...value,items:value.items.slice(0,3)}});}
  return {value,error,loading,more,reload,loadMore,collapse};
}
function FeedbackNotes({notes,saved}:{notes:string;saved:boolean}){
  const [expanded,setExpanded]=useState(false),id=useId();
  if(!notes)return <p className="sf-subtle">{saved?'No notes were added.':'Waiting for the analyst’s saved observations.'}</p>;
  return <div><p className="sf-feedback-notes" id={id}>{notes.length>300&&!expanded?notes.slice(0,300)+'…':notes}</p>{notes.length>300&&<Button variant="ghost" aria-controls={id} aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Read less':'Read more notes'}</Button>}</div>;
}
const states={active:'Current assignment',revoked:'Access revoked',expired:'Assignment expired',reviewer_unavailable:'Reviewer unavailable'};
export function OwnerReviewFeedback({id,onRequest}:{id:string;onRequest:()=>void}){
  const data=useOwnerReviews(id),listId=useId();
  return <GlassPanel className="sf-owner-feedback" label="Analyst feedback">
    <SectionHeading title="Analyst feedback" description="A second pair of ears, with observations saved for you." action={<Button variant="secondary" onClick={onRequest}><ClipboardText size={18}/>Request review</Button>}/>
    {data.error?<div role="alert"><Notice danger>{data.error}</Notice><Button variant="ghost" onClick={data.reload}>Retry feedback</Button></div>:data.loading?<p className="sf-feedback-loading" role="status"><SpinnerGap size={18}/>Loading feedback…</p>:data.value&&<>
      {data.value.items.length?<ul className="sf-feedback-list" id={listId}>{data.value.items.map(item=><li key={item.assignment_id} data-feedback-id={item.assignment_id}>
        <div className="sf-feedback-heading"><ProfileIdentity compact name={item.reviewer_display_name||'Reviewer name unavailable'} handle={item.reviewer_handle}/><ReviewStatus value={item.updated_at===null?'pending':item.decision}/></div>
        <div className="sf-feedback-context"><span>{item.resource_kind==='original_audio'?'Original audio review':'Result details review'}</span><span>{item.updated_at===null?`Assigned ${dateLabel(item.assigned_at)}`:`Saved ${dateLabel(item.updated_at)}`}</span><span>{states[item.assignment_state]}</span></div>
        <FeedbackNotes notes={item.notes} saved={item.updated_at!==null}/>
        {item.assignment_public_id&&<div className="sf-feedback-reference"><CopyId value={item.assignment_public_id}/></div>}
      </li>)}</ul>:<div className="sf-feedback-empty"><ClipboardText size={24}/><h3>No analyst feedback yet</h3><p>Request a review through sharing: find their @handle, choose Analyst review, then an exact original or result.</p></div>}
      <div className="sf-assignment-footer"><span role="status">{data.value.items.length} of {data.value.total} reviews & current assignments</span><div>{data.value.items.length<data.value.total&&<Button variant="ghost" disabled={data.more} aria-controls={listId} aria-expanded={data.value.items.length>3} onClick={()=>void data.loadMore()}><CaretDown size={16}/>{data.more?'Loading…':'See more'}</Button>}{data.value.items.length>3&&<Button variant="ghost" disabled={data.more} aria-controls={listId} aria-expanded onClick={data.collapse}><CaretUp size={16}/>See less</Button>}<Button variant="ghost" disabled={data.more} onClick={data.reload}>Refresh feedback</Button></div></div>
    </>}
    <p className="sf-sharing-footnote">Saved observations stay in your recording history after access is revoked. They are technical reviews, not diagnoses.</p>
  </GlassPanel>;
}
