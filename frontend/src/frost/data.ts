import {useEffect,useRef,useState} from 'react';
import {useLive} from '../data/live';
import type {LiveJob,LiveRecording,LiveResult} from '../data/liveTypes';
import type {RecordingStatus} from './contracts';

export const dateLabel = (seconds: number | null | undefined) => seconds == null ? 'Unavailable' : new Date(seconds * 1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'The service could not complete this request.';
const activeJob = (job: LiveJob) => ['queued','processing'].includes(job.status);

/** Current client/path own the value. Abort and discard obsolete account/route responses. */
export function useResource<T>(path: string | null, pending?: (data: T) => boolean) {
  const {api} = useLive();
  const [response,setResponse] = useState<{client: typeof api;path: string;value: T} | null>(null);
  const [error,setError] = useState(''), [loading,setLoading] = useState(true), [revision,setRevision] = useState(0);
  const pendingRef = useRef(pending); pendingRef.current = pending;
  const value = response?.client === api && response.path === path ? response.value : null;
  useEffect(() => {
    if (!path) {setLoading(false);setError('');return;}
    const resourcePath = path;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true); setError('');
    async function load() {
      try {
        const result = await api.json<T>(resourcePath,{signal:controller.signal});
        if (controller.signal.aborted) return;
        setResponse({client:api,path:resourcePath,value:result}); setError('');
        if (pendingRef.current?.(result)) timer = setTimeout(load,2000);
      } catch (failure) {
        if (!controller.signal.aborted) { setResponse(null);setError(errorMessage(failure)); }
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    const refresh = () => { if (!document.hidden) setRevision(v=>v+1); };
    window.addEventListener('focus',refresh); document.addEventListener('visibilitychange',refresh);
    return () => { controller.abort();clearTimeout(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh); };
  },[api,path,revision]);
  return {value,error,loading,reload:()=>setRevision(v=>v+1)};
}

export interface LibraryItem {
  recording: LiveRecording;
  job?: LiveJob;
  result?: LiveResult;
  status: RecordingStatus | null;
}
interface Collection {recordings: LiveRecording[];jobs: LiveJob[];results: LiveResult[]}
/** Three complete authorized sets, never one request per row or invented demo fallbacks. */
export function useLibrary() {
  const {api} = useLive();
  const [response,setResponse] = useState<{client:typeof api;value:Collection}|null>(null);
  const [error,setError] = useState(''),[loading,setLoading] = useState(true),[revision,setRevision] = useState(0);
  useEffect(()=>{
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true);setError('');
    async function load(){
      try {
        const [records,jobs,results] = await Promise.all([
          api.json<{items:LiveRecording[]}>('/recordings',{signal:controller.signal}),
          api.json<{items:LiveJob[]}>('/jobs',{signal:controller.signal}),
          api.json<{items:LiveResult[]}>('/results',{signal:controller.signal}),
        ]);
        if(controller.signal.aborted)return;
        setResponse({client:api,value:{recordings:records.items,jobs:jobs.items,results:results.items}});setError('');
        if(jobs.items.some(activeJob))timer=setTimeout(load,2000);
      }catch(failure){if(!controller.signal.aborted){setResponse(null);setError(errorMessage(failure));}}
      finally{if(!controller.signal.aborted)setLoading(false);}
    }
    void load();const refresh=()=>{if(!document.hidden)setRevision(v=>v+1);};
    window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);
    return()=>{controller.abort();clearTimeout(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);};
  },[api,revision]);
  const collection=response?.client===api?response.value:null;
  const jobs=new Map(collection?.jobs.map(job=>[job.recording_id,job]));
  const results=new Map(collection?.results.map(result=>[result.recording_id,result]));
  const items:LibraryItem[]=collection?.recordings.map(recording=>{
    const job=jobs.get(recording.id),result=results.get(recording.id);
    // An exact-audio recipient has no right to owner-only job state.
    const status:RecordingStatus|null=result?'ready':job?job.status==='succeeded'?'ready':job.status==='failed'?'failed':'processing':recording.is_owner?'recorded':null;
    return {recording,job,result,status};
  })||[];
  return {items,collection,error,loading,reload:()=>setRevision(v=>v+1)};
}
