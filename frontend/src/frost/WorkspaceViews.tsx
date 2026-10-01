import {useMemo,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {ArrowRight,CaretLeft,CaretRight,Check,Circle,Clock,LockSimple,MagnifyingGlass,Plus,ShareNetwork,SpinnerGap,Waveform,X} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import {Button,CopyId,GlassPanel,Notice,SectionHeading,Segments,StatusChip} from './primitives';
import {dateLabel,useLibrary,type LibraryItem} from './data';
import {timeLabel} from './contracts';
import {PerchedOwl} from './PerchedOwl';
import botanicalPerch from '../ux-preview/assets/botanical-perch.webp';

export function RequestState({loading,error,reload}:{loading:boolean;error:string;reload:()=>void}){
  if(error)return <div role="alert"><Notice danger>{error}</Notice><Button variant="secondary" onClick={reload}>Retry request</Button></div>;
  return loading?<div className="sf-loading" role="status"><SpinnerGap size={24}/>Loading your workspace…</div>:null;
}
export function EmptyState({title,description,action}:{title:string;description:string;action?:React.ReactNode}){return <div className="sf-empty"><Waveform size={36}/><h2>{title}</h2><p>{description}</p>{action}</div>;}
export function RecordingRows({items,compact=false}:{items:LibraryItem[];compact?:boolean}){
  return <div className={`sf-recordings ${compact?'sf-recordings--compact':''}`}>
    {!compact&&<div className="sf-list-head" aria-hidden="true"><span>Recording</span><span>Added</span><span>Duration</span><span>Status</span><span>Access</span><span/></div>}
    <ul aria-label="Recordings">{items.map(({recording:r,status})=><li key={r.id}>
      <div className="sf-recording-title"><span className="sf-recording-symbol"><Waveform size={22}/></span><div><strong>{r.title}</strong><div className="sf-recording-reference">{r.public_id?<CopyId value={r.public_id}/>:<span className="sf-subtle">{compact?dateLabel(r.created_at):r.is_owner?'Saved recording':'Shared recording'}</span>}</div></div></div>
      {!compact&&<span className="sf-recording-date">{dateLabel(r.created_at)}</span>}
      <span className="sf-recording-duration">{Number.isFinite(r.duration_sec)?timeLabel(r.duration_sec):'—'}</span>
      {status?<StatusChip status={status}/>:<span className="sf-status sf-status--recorded">Shared audio</span>}
      <span className="sf-recording-access">{r.is_owner?<LockSimple size={15}/>:<ShareNetwork size={15}/>}<span>{r.is_owner?'Private':'Shared'}</span></span>
      <Link to={`/app/recordings/${r.id}`} className="sf-row-action" aria-label={`Open ${r.title}`}>{compact?<ArrowRight size={21}/>:<>Open<ArrowRight size={17}/></>}</Link>
    </li>)}</ul>
  </div>;
}
export function Progress({status,title}:{status:string;title?:string}){
  const ready=status==='succeeded',failed=status==='failed',processing=status==='processing',queued=status==='queued',requesting=status==='requesting',working=processing||queued||requesting;
  return <div role="status" aria-live="polite"><GlassPanel className={`sf-progress-panel ${working?'sf-progress-panel--working':''}`} label="Recording progress"><div><div className="sf-progress-title"><span className="sf-progress-icon">{working?<span className="sf-working-wave" aria-hidden="true"><i/><i/><i/><i/><i/></span>:ready?<Check size={22}/>:<Circle size={22}/>}</span><div><h2>{requesting?'Starting separation':failed?'Separation needs attention':ready?'Ready to listen':queued?'Waiting to separate':'Separation in progress'}</h2><p>{processing?'Separating heart and lung audio':requesting?'Sending your separation request':title}</p></div></div><p className="sf-progress-copy">{requesting?'Creating your processing job. Your original stays unchanged.':ready?'Your separated sounds are saved privately.':failed?'Your original is unchanged. See the saved failure details below.':'You can leave this page. Progress is saved in your Library.'}</p></div><ol className="sf-progress-steps" aria-label="Recording progress"><li className="is-complete"><span><Check size={17}/></span><strong>Recorded</strong><small>Saved privately</small></li><li className={ready?'is-complete':working?'is-current':''} aria-current={working?'step':undefined}><span>{ready?<Check size={17}/>:<SpinnerGap className={working?'sf-working-spinner':''} size={18}/>}</span><strong>{requesting?'Starting':queued?'Queued':'Processing'}</strong><small>{requesting?'Requesting job':queued?'Waiting for worker':processing?'Separating sounds':failed?'Not completed':'Completed'}</small></li><li className={ready?'is-complete':''} aria-current={ready?'step':undefined}><span>{ready?<Check size={17}/>:<Circle size={17}/>}</span><strong>Ready</strong><small>Listen & review</small></li></ol></GlassPanel></div>;
}
export function Overview(){
  const {session,preferences}=useLive(),data=useLibrary();
  const own=data.items.filter(i=>i.recording.is_owner),shared=data.items.filter(i=>!i.recording.is_owner);
  const unfinished=own.filter(i=>i.job&&['queued','processing'].includes(i.job.status));
  const week=Date.now()/1000-7*86400,weekly=own.filter(i=>i.recording.created_at>=week);
  const recentReady=own.filter(i=>i.result&&i.result.created_at>=week).length;
  const hour=new Date().getHours(),greeting=hour<12?'Good morning':hour<18?'Good afternoon':'Good evening';
  return <><header className="sf-page-heading sf-greeting"><div><p className="sf-date">{new Date().toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long'})}</p><h1>{greeting}{session!.user.display_name?`, ${session!.user.display_name.split(' ')[0]}`:''}.</h1><p>{session!.user.handle&&<span className="sf-greeting-handle">@{session!.user.handle} · </span>}A clear place for every recording.</p><Link className="sf-button sf-button--primary" to="/app/recordings/new"><Plus size={20}/>New recording</Link></div><div className="sf-greeting-art" aria-hidden="true"><img className="sf-botanical-perch" src={botanicalPerch} alt="" width={1774} height={887}/><PerchedOwl reducedMotion={preferences.appearance?.reducedMotion===true}/></div></header>
  <RequestState {...data}/>
  {data.collection&&<>{unfinished.length>0&&<><Progress status={unfinished[0].job!.status} title={unfinished[0].recording.title}/><Link className="sf-text-link sf-progress-open" to={`/app/recordings/${unfinished[0].recording.id}`}>Open in-progress recording<ArrowRight size={17}/></Link></>}
  <div className="sf-overview-grid"><GlassPanel className="sf-recent-panel"><SectionHeading title="Recent recordings" description="From first capture to a closer listen." action={<Link className="sf-text-link" to="/app/library">View library<ArrowRight size={16}/></Link>}/>{own.length?<RecordingRows compact items={own.slice(0,4)}/>:<EmptyState title="Your next recording starts here" description="Upload a WAV to begin your private Library. Live recording is coming soon." action={<Link className="sf-text-link" to="/app/recordings/new">Add a recording<ArrowRight size={17}/></Link>}/>}<div className="sf-recent-footer"><Clock size={16}/><span>Your complete recording history stays in the Library.</span></div></GlassPanel>
  <GlassPanel className="sf-overview-rail" label="Shared work and weekly activity"><section className="sf-attention-panel"><SectionHeading title="Shared with you"/><div className="sf-shared-icon"><ShareNetwork size={25}/></div><h3>{shared.length?'A second pair of ears':'A quieter shared workspace'}</h3><p>{shared.length?'Recordings currently shared with your account.':'Nothing has been shared with you yet.'}</p>{shared[0]&&<><div className="sf-shared-recording"><strong>{shared[0].recording.title}</strong><span>{timeLabel(shared[0].recording.duration_sec)} · Explicit access</span>{shared[0].status&&<StatusChip status={shared[0].status}/>}</div><Link to={`/app/recordings/${shared[0].recording.id}`} className="sf-text-link">Open recording<ArrowRight size={17}/></Link></>}</section><section className="sf-week-summary"><h2>Your week, at a glance.</h2><div><span><strong>{weekly.length}</strong> recordings saved</span><span><strong>{recentReady}</strong> separations completed</span></div><p>Your own activity in the last seven days.</p></section></GlassPanel></div></>}
  </>;
}
type Filter='all'|'ready'|'processing'|'shared';
export function Library({sharedOnly=false,embedded=false}:{sharedOnly?:boolean;embedded?:boolean}){
  const data=useLibrary(),[params,setParams]=useSearchParams();
  const search=params.get('q')||'',f=params.get('filter'),filter:Filter=sharedOnly?'shared':['all','ready','processing','shared'].includes(f||'')?f as Filter:'all';
  const sort=params.get('sort')==='oldest'?'oldest':'newest';
  const [page,setPage]=useState(0);
  const rows=useMemo(()=>{
    const matching=data.items.filter(i=>(filter==='all'||filter==='shared'&&!i.recording.is_owner||i.status===filter)&&`${i.recording.title} ${i.recording.public_id||''}`.toLowerCase().includes(search.toLowerCase().trim()));
    return matching.sort((a,b)=>(sort==='oldest'?1:-1)*(a.recording.created_at-b.recording.created_at)||a.recording.id.localeCompare(b.recording.id));
  },[data.items,search,filter,sort]);
  const currentPage=Math.min(page,Math.max(0,Math.ceil(rows.length/6)-1));
  function change(key:string,value:string){const next=new URLSearchParams(params);next.set(key,value);setParams(next,{replace:true});setPage(0);}
  const count=(id:Filter)=>id==='all'?data.items.length:id==='shared'?data.items.filter(i=>!i.recording.is_owner).length:data.items.filter(i=>i.status===id).length;
  return <>{!embedded&&<header className="sf-page-heading"><div><h1>{sharedOnly?'Shared & assigned':'Your sound library'}</h1><p>One place for recordings, from capture to review.</p></div><Link className="sf-button sf-button--primary" to="/app/recordings/new"><Plus size={20}/>New recording</Link></header>}
  <GlassPanel className="sf-library-panel"><div className="sf-library-tools"><label className="sf-search-field"><MagnifyingGlass size={20}/><span className="sf-sr">Search recordings by title or public reference</span><input id="library-search" type="search" placeholder="Search by title or REC reference" value={search} onChange={e=>change('q',e.target.value)}/>{search&&<Button variant="icon" aria-label="Clear search" onClick={()=>change('q','')}><X size={18}/></Button>}</label><label className="sf-sort"><span className="sf-sr">Sort recordings</span><select value={sort} onChange={e=>change('sort',e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label></div><div className="sf-library-filters">{!sharedOnly&&<Segments<Filter> label="Library filters" value={filter} onChange={id=>change('filter',id)} items={(['all','ready','processing','shared'] as Filter[]).map(id=>({id,label:id[0].toUpperCase()+id.slice(1),count:data.collection?count(id):undefined}))}/>}<span>All recordings stay private by default.</span><Button variant="ghost" onClick={data.reload}>Refresh access</Button></div><RequestState {...data}/>{data.collection&&(rows.length?<RecordingRows items={rows.slice(currentPage*6,currentPage*6+6)}/>:<EmptyState title={search||filter!=='all'?'No matching recordings':'Your Library is ready'} description={search||filter!=='all'?'Try another title or filter. Only currently authorized recordings are included.':'Upload a WAV to start. No demonstration recordings are loaded.'}/>)}{data.collection&&<div className="sf-library-footer"><span role="status">{rows.length?`${currentPage*6+1}–${Math.min(currentPage*6+6,rows.length)} of ${rows.length}`:'0'} recordings · complete authorized collection</span>{rows.length>6&&<nav className="sf-pagination" aria-label="Library pages"><Button variant="icon" aria-label="Previous page" disabled={currentPage===0} onClick={()=>setPage(currentPage-1)}><CaretLeft size={18}/></Button><Button variant="icon" aria-label="Next page" disabled={(currentPage+1)*6>=rows.length} onClick={()=>setPage(currentPage+1)}><CaretRight size={18}/></Button></nav>}</div>}</GlassPanel><div className="sf-library-bottom"><span>PCM WAV · up to 25 MiB per upload</span><p>Only people you explicitly share with can access your recordings.</p></div></>;
}
