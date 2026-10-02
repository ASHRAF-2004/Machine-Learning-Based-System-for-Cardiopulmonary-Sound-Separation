import {Link} from 'react-router-dom';
import {ArrowRight,CheckCircle,ClipboardText,Clock,WarningCircle} from '@phosphor-icons/react';
import type {LiveAssignment} from '../data/liveTypes';
import {CopyId} from './primitives';
import {dateLabel} from './data';

const labels={pending:'To review',accepted:'Reviewed',needs_attention:'Needs attention'};
export function ReviewStatus({value}:{value:LiveAssignment['review_decision']}){
  const Icon=value==='accepted'?CheckCircle:value==='needs_attention'?WarningCircle:Clock;
  return <span className={`sf-review-status sf-review-status--${value||'unknown'}`}><Icon size={16}/>{value?labels[value]:'Status unavailable'}</span>;
}
export const assignmentPriority=(a:LiveAssignment,b:LiveAssignment)=>Number(b.review_decision==='pending')-Number(a.review_decision==='pending')||a.created_at-b.created_at||a.id.localeCompare(b.id);
export function AssignmentRows({items,id,compact=false}:{items:LiveAssignment[];id?:string;compact?:boolean}){
  return <ul className={`sf-assignment-list ${compact?'sf-assignment-list--compact':''}`} id={id} aria-label="Assigned reviews">{items.map(item=><li key={item.id} data-assignment-id={item.id}>
    <div className="sf-assignment-title"><span className="sf-recording-symbol"><ClipboardText size={22}/></span><div><strong>{item.recording_title||'Recording title unavailable'}</strong>{item.recording_public_id&&<CopyId value={item.recording_public_id}/>}<small>{item.resource_kind==='original_audio'?'Original audio only':item.resource_kind==='result'?'Result details only':'Exact assigned resource'}</small></div></div>
    {!compact&&<div className="sf-assignment-date"><span>Assigned {dateLabel(item.created_at)}</span>{item.expires_at!=null&&<small>Expires {dateLabel(item.expires_at)}</small>}</div>}
    <ReviewStatus value={item.review_decision}/>
    <Link to={`/app/reviews/${item.id}`} className="sf-row-action" aria-label={`Open review for ${item.recording_title||'assigned recording'}`}>{item.review_decision==='pending'?'Review':'Open review'}<ArrowRight size={17}/></Link>
  </li>)}</ul>;
}
