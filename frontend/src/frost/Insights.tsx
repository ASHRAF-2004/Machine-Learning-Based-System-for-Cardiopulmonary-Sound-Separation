import {useId,useState} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,CaretDown,CaretUp,CheckCircle,Clock,FolderSimple,Plus} from '@phosphor-icons/react';
import type {WorkspaceInsights} from '../data/liveTypes';
import {Button,GlassPanel,SectionHeading} from './primitives';
import {dateLabel,useResource} from './data';
import {timeLabel} from './contracts';
import {EmptyState,RequestState} from './WorkspaceViews';

export function Insights(){
  const data=useResource<WorkspaceInsights>('/insights'),[expanded,setExpanded]=useState(false),id=useId();
  const value=data.value;
  return <>
    <header className="sf-page-heading sf-workspace-summary-heading"><div><h1>Your workspace, in perspective.</h1><p>Your own recording activity. No confidence scores or clinical judgments.</p></div><Link className="sf-button sf-button--primary" to="/app/recordings/new"><Plus size={20}/>New recording</Link></header>
    <RequestState {...data}/>
    {value&&!data.error&&<>
      <GlassPanel className="sf-insights-summary" label="Own Library summary"><SectionHeading title="Your Library at a glance" description={`Complete owned collection · updated ${dateLabel(value.as_of)}`} action={<Button variant="ghost" onClick={data.reload}>Refresh activity</Button>}/>
        <dl className="sf-insights-facts"><div><dt><FolderSimple size={20}/>Recordings saved</dt><dd>{value.counts.total}</dd><small>Shared recordings are excluded.</small></div><div><dt><CheckCircle size={20}/>Ready to review</dt><dd>{value.counts.ready}</dd><small>Completed separation jobs.</small></div><div><dt><Clock size={20}/>Recorded time</dt><dd>{timeLabel(value.recorded_seconds)}</dd><small>Stored durations, not listening time.</small></div></dl>
      </GlassPanel>
      {!value.counts.total?<GlassPanel className="sf-assignment-panel"><EmptyState title="Your next recording starts the story" description="Upload a WAV to begin. This view shows real activity only." action={<Link className="sf-text-link" to="/app/recordings/new">Add a recording<ArrowRight size={17}/></Link>}/></GlassPanel>:<div className="sf-insights-grid">
        <GlassPanel className="sf-assignment-panel" label="Recent recording activity"><SectionHeading title="The last seven days" description="Recordings saved and separations completed. UTC calendar dates."/>
          <div className="sf-insights-trend" role="img" aria-label={value.days.map(day=>`${day.date}: ${day.recordings} recordings saved and ${day.completed} separations completed`).join('; ')}>{value.days.map(day=>{
            const max=Math.max(1,...value.days.flatMap(item=>[item.recordings,item.completed]));
            return <div key={day.date}><div className="sf-trend-bars" aria-hidden="true"><span style={{height:`${day.recordings/max*100}%`}}/><span style={{height:`${day.completed/max*100}%`}}/></div><small>{new Date(day.date+'T00:00:00Z').toLocaleDateString(undefined,{weekday:'short',timeZone:'UTC'})}</small></div>;
          })}</div><p className="sf-trend-legend"><span>Recordings saved</span><span>Separations completed</span></p>
          <Button variant="ghost" aria-expanded={expanded} aria-controls={id} onClick={()=>setExpanded(value=>!value)}>{expanded?<CaretUp size={16}/>:<CaretDown size={16}/>} {expanded?'See less':'See daily counts'}</Button>
          {expanded&&<table className="sf-comparison-table" id={id}><caption className="sf-sr">Own activity by UTC date</caption><thead><tr><th scope="col">Date (UTC)</th><th scope="col">Saved</th><th scope="col">Completed</th></tr></thead><tbody>{value.days.map(day=><tr key={day.date}><th scope="row">{day.date}</th><td>{day.recordings}</td><td>{day.completed}</td></tr>)}</tbody></table>}
        </GlassPanel>
        <GlassPanel className="sf-assignment-panel" label="Current recording states"><SectionHeading title="Where things stand" description="Current states across your own Library."/><dl className="sf-insights-states">{([['recorded','Not separated'],['queued','Queued'],['processing','Processing'],['ready','Ready'],['failed','Failed']] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{value.counts[key]}</dd></div>)}</dl><Link className="sf-text-link" to="/app/library">Open Library<ArrowRight size={17}/></Link><p className="sf-sharing-footnote">Signal checks and before/after measurements belong to each authorized recording. These activity counts do not measure separation accuracy.</p></GlassPanel>
      </div>}
    </>}
  </>;
}
