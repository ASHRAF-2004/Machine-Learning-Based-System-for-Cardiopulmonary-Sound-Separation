import {Link} from 'react-router-dom';
import {ArrowRight,ClipboardText,SpinnerGap} from '@phosphor-icons/react';
import type {LiveAssignment} from '../data/liveTypes';
import {AssignmentRows,assignmentPriority} from './AssignmentRows';
import {Button,GlassPanel,Notice,SectionHeading} from './primitives';
import {useResource} from './data';

export function AnalystOverview(){
  const data=useResource<{items:LiveAssignment[]}>('/assignments');
  const items=data.value?[...data.value.items].sort(assignmentPriority):null;
  const pending=items?.filter(item=>item.review_decision==='pending');
  const unknown=items?.some(item=>!item.review_decision);
  const week=Date.now()/1000-7*86400;
  const savedThisWeek=items?.filter(item=>item.review_updated_at!=null&&item.review_updated_at>=week&&item.review_decision&&item.review_decision!=='pending').length;
  return <>
    {data.error?<div role="alert"><Notice danger>{data.error}</Notice><Button variant="secondary" onClick={data.reload}>Retry assignments</Button></div>:data.loading&&!items?<div className="sf-loading" role="status"><SpinnerGap size={24}/>Loading assigned work…</div>:null}
    {items&&!data.error&&<div className="sf-overview-grid">
      <GlassPanel className="sf-assignment-panel sf-analyst-priority" label="Your assigned work"><SectionHeading title="Your assigned work" description="Unfinished reviews first. Only the exact resources owners assigned to you." action={<Link className="sf-text-link" to="/app/shared?view=assigned">View all<ArrowRight size={16}/></Link>}/>
        {items.length?<AssignmentRows items={items.slice(0,3)} compact/>:<div className="sf-empty"><ClipboardText size={32}/><h2>A quieter review queue</h2><p>Ask the recording owner to assign a review using your @handle. Shared audio and your own Library remain available.</p></div>}
        <div className="sf-recent-footer"><ClipboardText size={16}/><span>Review, save observations, and return feedback to the owner.</span></div>
      </GlassPanel>
      <GlassPanel className="sf-overview-rail" label="Review access and current activity"><section className="sf-attention-panel"><SectionHeading title="A focused second listen"/><div className="sf-shared-icon"><ClipboardText size={25}/></div><h3>Assigned, not unrestricted.</h3><p>Your role lets you save technical observations on assigned work. Private audio still needs its own current permission.</p><Link className="sf-text-link" to="/app/shared">Shared with you<ArrowRight size={17}/></Link></section><section className="sf-week-summary"><h2>Your review activity.</h2><div><span><strong>{unknown?'—':pending!.length}</strong> awaiting review</span><span><strong>{unknown?'—':savedThisWeek}</strong> outcomes saved this week</span></div><p>{unknown?'Some review statuses are unavailable.':'Among your current active assignments. Closed assignments are not included.'}</p></section></GlassPanel>
    </div>}
  </>;
}
