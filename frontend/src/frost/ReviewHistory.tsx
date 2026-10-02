import {useId} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,CaretDown,CaretUp} from '@phosphor-icons/react';
import {Button,CopyId,GlassPanel,SectionHeading} from './primitives';
import {ReviewStatus} from './AssignmentRows';
import {FeedbackNotes} from './OwnerReviewFeedback';
import {dateLabel} from './data';
import {useReviewPage} from './useReviewPage';
import type {SavedReview} from '../data/liveTypes';
import {EmptyState,RequestState} from './WorkspaceViews';

export function ReviewHistory(){
  const data=useReviewPage<SavedReview>('/reviews/history'),id=useId();
  return <>
    <header className="sf-page-heading sf-workspace-summary-heading"><div><h1>A record of your observations.</h1><p>Saved reviews, available through your current assignments.</p></div><Link className="sf-button sf-button--primary" to="/app/shared?view=assigned">Open assigned reviews<ArrowRight size={18}/></Link></header>
    <GlassPanel className="sf-owner-feedback sf-review-history" label="Saved review history">
      <SectionHeading title="Saved reviews" description="The latest saved observation for each currently authorized assignment." action={<Button variant="ghost" disabled={data.more} onClick={data.reload}>Refresh access</Button>}/>
      <RequestState {...data}/>
      {data.value&&!data.error&&(data.value.items.length?<>
        <ul className="sf-feedback-list" id={id}>{data.value.items.map(item=><li key={item.assignment_id} data-saved-review-id={item.assignment_id}>
          <div className="sf-feedback-heading"><h3>{item.recording_title||'Recording title unavailable'}</h3><ReviewStatus value={item.decision}/></div>
          <div className="sf-feedback-context"><span>{item.resource_kind==='original_audio'?'Original audio review':'Result details review'}</span><span>Saved {dateLabel(item.updated_at)}</span>{item.recording_public_id&&<CopyId value={item.recording_public_id}/>}</div>
          <FeedbackNotes notes={item.notes} saved/>
          <div className="sf-history-row-footer">{item.assignment_public_id&&<CopyId value={item.assignment_public_id}/>}<Link className="sf-text-link" to={`/app/reviews/${item.assignment_id}`}>Open review<ArrowRight size={17}/></Link></div>
        </li>)}</ul>
        <div className="sf-assignment-footer"><span role="status">{data.value.items.length} of {data.value.total} saved authorized reviews</span><div>{data.value.items.length<data.value.total&&<Button variant="ghost" disabled={data.more} aria-expanded={data.value.items.length>3} aria-controls={id} onClick={()=>void data.loadMore()}><CaretDown size={16}/>{data.more?'Loading…':'See more'}</Button>}{data.value.items.length>3&&<Button variant="ghost" disabled={data.more} aria-expanded aria-controls={id} onClick={data.collapse}><CaretUp size={16}/>See less</Button>}</div></div>
      </>:<EmptyState title="No saved reviews available" description="Save an observation from your assigned reviews. Revoked, expired or unavailable assignments do not appear here."/>)}
      <p className="sf-sharing-footnote">Access is checked again on refresh and when you reopen a review. Older observations are retained for the recording owner, but revocation does not give you continued access. These are workflow observations, not diagnoses.</p>
    </GlassPanel>
  </>;
}
