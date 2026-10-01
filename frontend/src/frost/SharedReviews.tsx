import {useId,useMemo,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {ArrowRight,CaretDown,CaretUp,CheckCircle,ClipboardText,Clock,MagnifyingGlass,ShieldCheck,WarningCircle,X} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import type {LiveAssignment} from '../data/liveTypes';
import {Button,CopyId,GlassPanel,SectionHeading,Segments} from './primitives';
import {dateLabel,useResource} from './data';
import {EmptyState,Library,RequestState} from './WorkspaceViews';

type View='shared'|'assigned';
const labels={pending:'To review',accepted:'Reviewed',needs_attention:'Needs attention'};
function ReviewStatus({value}:{value:LiveAssignment['review_decision']}){
  const Icon=value==='accepted'?CheckCircle:value==='needs_attention'?WarningCircle:Clock;
  return <span className={`sf-review-status sf-review-status--${value||'unknown'}`}><Icon size={16}/>{value?labels[value]:'Status unavailable'}</span>;
}

export function SharedWorkspace(){
  const {session}=useLive(),[params,setParams]=useSearchParams();
  const analyst=session?.user.role==='audio_analyst';
  const view:View=analyst&&params.get('view')==='assigned'?'assigned':'shared';
  function change(value:View){const next=new URLSearchParams();next.set('view',value);setParams(next);}
  return <>
    <header className="sf-page-heading"><div><h1>Shared & assigned</h1><p>A second pair of ears. Only the resources shared with you.</p></div><span className="sf-settings-private"><ShieldCheck size={17}/>Explicit access</span></header>
    {analyst&&<div className="sf-shared-tabs"><Segments<View> label="Shared workspace" value={view} onChange={change} items={[{id:'shared',label:'Shared with you'},{id:'assigned',label:'Assigned reviews'}]}/></div>}
    {view==='assigned'?<AssignedQueue/>:<Library sharedOnly embedded/>}
  </>;
}

function AssignedQueue(){
  const data=useResource<{items:LiveAssignment[]}>('/assignments'),[params,setParams]=useSearchParams();
  const listId=useId(),[expanded,setExpanded]=useState(false),search=params.get('q')||'',all=params.get('reviews')==='all';
  const rows=useMemo(()=>[...(data.value?.items||[])].filter(item=>(all||!item.review_decision||item.review_decision==='pending')&&`${item.recording_title||''} ${item.recording_public_id||''} ${item.assignment_public_id||''}`.toLowerCase().includes(search.trim().toLowerCase())).sort((a,b)=>Number(b.review_decision==='pending')-Number(a.review_decision==='pending')||a.created_at-b.created_at||a.id.localeCompare(b.id)),[data.value,search,all]);
  function change(key:string,value:string){const next=new URLSearchParams(params);next.set(key,value);setParams(next,{replace:true});setExpanded(false);}
  const visible=expanded?rows:rows.slice(0,3);
  return <GlassPanel className="sf-assignment-panel" label="Assigned reviews">
    <SectionHeading title="Your review queue" description="Unfinished reviews first. Each assignment covers one original or result." action={<Button variant="ghost" onClick={data.reload}>Refresh access</Button>}/>
    <div className="sf-assignment-tools"><label className="sf-search-field"><MagnifyingGlass size={20}/><span className="sf-sr">Search assigned reviews by title or public reference</span><input type="search" value={search} placeholder="Search title, REC or ASN reference" onChange={event=>change('q',event.target.value)}/>{search&&<Button variant="icon" aria-label="Clear review search" onClick={()=>change('q','')}><X size={18}/></Button>}</label><Segments<'pending'|'all'> label="Review filters" value={all?'all':'pending'} onChange={value=>change('reviews',value)} items={[{id:'pending',label:'To review'},{id:'all',label:'All assignments'}]}/></div>
    <RequestState {...data}/>
    {data.value&&!data.error&&(rows.length?<>
      <ul className="sf-assignment-list" id={listId} aria-label="Assigned reviews">{visible.map(item=><li key={item.id} data-assignment-id={item.id}>
        <div className="sf-assignment-title"><span className="sf-recording-symbol"><ClipboardText size={22}/></span><div><strong>{item.recording_title||'Recording title unavailable'}</strong>{item.recording_public_id&&<CopyId value={item.recording_public_id}/>}<small>{item.resource_kind==='original_audio'?'Original audio only':item.resource_kind==='result'?'Result details only':'Exact assigned resource'}</small></div></div>
        <div className="sf-assignment-date"><span>Assigned {dateLabel(item.created_at)}</span>{item.expires_at!=null&&<small>Expires {dateLabel(item.expires_at)}</small>}</div>
        <ReviewStatus value={item.review_decision}/>
        <Link to={`/app/reviews/${item.id}`} className="sf-row-action" aria-label={`Open review for ${item.recording_title||'assigned recording'}`}>{item.review_decision==='pending'?'Review':'Open review'}<ArrowRight size={17}/></Link>
      </li>)}</ul>
      <div className="sf-assignment-footer"><span role="status">{visible.length} of {rows.length} matching active assignments</span>{rows.length>3&&<Button variant="ghost" aria-expanded={expanded} aria-controls={listId} onClick={()=>setExpanded(value=>!value)}>{expanded?<CaretUp size={16}/>:<CaretDown size={16}/>} {expanded?'See less':`See more (${rows.length-3})`}</Button>}</div>
    </>:<EmptyState title={search?'No matching reviews':all?'No active assignments':'No unfinished reviews'} description={search?'Try a recording title or public reference.':all?'The owner can assign an exact original or result using your @handle. Revoked and expired assignments are not included.':'Choose All assignments to revisit a saved review. Shared audio remains available only through its current permissions.'}/>)}
    <p className="sf-sharing-footnote">A result review does not unlock Heart or Lung audio. Owners must share those sounds separately. These are workflow reviews, not diagnoses.</p>
  </GlassPanel>;
}
