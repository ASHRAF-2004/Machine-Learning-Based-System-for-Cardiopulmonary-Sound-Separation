import {useId,useState,type ReactNode} from 'react';
import {CaretDown,CaretUp} from '@phosphor-icons/react';
import type {LiveJob,LiveRecording,LiveResult} from '../data/liveTypes';
import {Button,CopyId} from './primitives';
import {dateLabel} from './data';

function Fact({label,children}:{label:string;children:ReactNode}){
  return <div><dt>{label}</dt><dd>{children}</dd></div>;
}

export function TechnicalDetails({record,result,job}:{record?:LiveRecording;result?:LiveResult;job?:LiveJob}){
  const [expanded,setExpanded]=useState(false),receiptId=useId();
  const receipt:Record<string,unknown>=result?.provenance||{};
  const runtime=receipt.runtime_seconds;
  const completed=job?.completed_at||result?.created_at;
  const status=job?.status==='succeeded'||result?'Ready':job?.status==='failed'?'Failed':job?.status==='processing'?'Processing':job?.status==='queued'?'Queued':record?'Recorded':null;
  return <details className="sf-technical sf-core-technical">
    <summary>Technical details & processing history</summary>
    <dl className="sf-technical-facts">
      {record&&<Fact label="Original format">{record.sample_rate_hz.toLocaleString()} Hz · {record.channels===1?'Mono':`${record.channels} channels`} · {record.duration_sec.toFixed(1)} seconds</Fact>}
      {status&&<Fact label="Status">{status}</Fact>}
      {completed&&<Fact label="Completed">{dateLabel(completed)}</Fact>}
      {typeof runtime==='number'&&Number.isFinite(runtime)&&<Fact label="Processing time">{runtime.toFixed(3)} seconds</Fact>}
      {typeof receipt.model_name==='string'&&<Fact label="Separator">{receipt.model_name}</Fact>}
      {result?.public_id&&<Fact label="Result reference"><CopyId value={result.public_id}/></Fact>}
      {job?.error_code&&<Fact label="Failure category">{job.error_code}</Fact>}
    </dl>
    <div className="sf-details-disclosure">
      <Button variant="ghost" aria-expanded={expanded} aria-controls={receiptId} onClick={()=>setExpanded(value=>!value)}>
        {expanded?<CaretUp size={16}/>:<CaretDown size={16}/>} {expanded?'See less':'See more'}
      </Button>
      <span>Full processing receipt & references</span>
    </div>
    <div id={receiptId} hidden={!expanded}>
      {expanded&&<dl className="sf-technical-receipt">
        {record&&<>
          {record.public_id&&<Fact label="Recording reference"><CopyId value={record.public_id}/></Fact>}
          <Fact label="Internal recording identifier"><CopyId value={record.id}/></Fact>
        </>}
        {job&&<>
          {job.public_id&&<Fact label="Processing reference"><CopyId value={job.public_id}/></Fact>}
          <Fact label="Internal processing identifier"><CopyId value={job.id}/></Fact>
          <Fact label="Created / completed">{dateLabel(job.created_at)} / {dateLabel(job.completed_at)}</Fact>
        </>}
        {result&&<Fact label="Internal result identifier"><CopyId value={result.id}/></Fact>}
        {Object.entries(receipt).map(([key,value])=><Fact key={key} label={key.replaceAll('_',' ')}>{typeof value==='object'?JSON.stringify(value):String(value)}</Fact>)}
      </dl>}
    </div>
  </details>;
}
