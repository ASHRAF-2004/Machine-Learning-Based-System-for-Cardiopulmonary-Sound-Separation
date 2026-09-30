import {useMemo,useRef,useState,type FormEvent} from 'react';
import {Link,useNavigate} from 'react-router-dom';
import {ArrowRight,LockSimple,UploadSimple} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import type {LiveRecording} from '../data/liveTypes';
import {Button,GlassPanel,Notice,SectionHeading} from './primitives';
import {AudioWorkspace} from './AudioWorkspace';
import {errorMessage} from './data';
import {UnsavedGuard} from '../components/ui';
import recordingLock from './assets/recording-locked-v1.png';

function RecordingLock(){return <div className="sf-recording-lock" aria-label="Microphone recording coming soon"><img src={recordingLock} alt="" width={160} height={160}/><span className="sf-soon-badge"><LockSimple size={14}/>Coming soon</span></div>;}
export function NewRecording(){return <><header className="sf-page-heading"><div><h1>Start with a sound.</h1><p>Bring your WAV. We’ll make room for the heart and lung sounds within it.</p></div></header><div className="sf-create-grid"><GlassPanel className="sf-create-upload"><span className="sf-create-symbol"><UploadSimple size={29}/></span><h2>Bring a recording.</h2><p>Upload, listen, then separate. Your original is saved privately and stays unchanged.</p><Link className="sf-button sf-button--primary" to="/app/recordings/new/upload">Upload WAV<ArrowRight size={18}/></Link><span className="sf-create-format">PCM WAV · up to 25 MiB · up to two minutes</span></GlassPanel><GlassPanel className="sf-create-locked"><RecordingLock/><h2>Record audio</h2><p>A little more time for live sound.</p><span className="sf-subtle">Microphone recording is coming soon. Upload an existing WAV for now.</span></GlassPanel></div><Notice>Use only audio you are authorized to upload. Sound separation is not a diagnosis.</Notice></>;}
export function RecordingComingSoon(){return <><header className="sf-page-heading"><div><h1>Live sound, a little later.</h1><p>Microphone recording is coming soon.</p></div></header><GlassPanel className="sf-recording-soon"><RecordingLock/><h2>Your next sound can start with a file.</h2><p>Upload an existing WAV to use separation and review today. No microphone is activated here.</p><Link className="sf-button sf-button--primary" to="/app/recordings/new/upload">Upload WAV<ArrowRight size={18}/></Link><Link className="sf-text-link" to="/app/library">Back to Library</Link></GlassPanel></>;}
export function Upload(){
  const {api}=useLive(),navigate=useNavigate();
  const [file,setFile]=useState<File|null>(null),[title,setTitle]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const submitting=useRef(false);
  const provider=useMemo(()=>({media:async(_id:string,signal?:AbortSignal)=>{if(signal?.aborted)throw new DOMException('Aborted','AbortError');if(!file)throw new Error('Choose a WAV to review.');return file;}}),[file]);
  async function submit(e:FormEvent){
    e.preventDefault();if(submitting.current)return;setError('');
    if(!file){setError('Choose a WAV file.');return;}
    if(file.size>25*1024*1024||!file.name.toLowerCase().endsWith('.wav')){setError('Choose a WAV file no larger than 25 MiB.');return;}
    submitting.current=true;setBusy(true);
    try{const body=new FormData();body.set('file',file);if(title.trim())body.set('title',title.trim());const record=await api.json<LiveRecording>('/recordings',{method:'POST',body});navigate(`/app/recordings/${record.id}`);}
    catch(failure){setError(errorMessage(failure));}finally{submitting.current=false;setBusy(false);}
  }
  return <><header className="sf-page-heading"><div><h1>Bring a recording.</h1><p>Review your file, then save it to your private Library.</p></div></header><GlassPanel className="sf-upload-panel"><form onSubmit={submit}><label className="sf-upload-drop"><UploadSimple size={32}/><strong>Choose a WAV recording</strong><span>Mono or stereo PCM WAV · up to 25 MiB · up to two minutes</span><input type="file" accept=".wav,audio/wav" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]||null);setError('');}}/></label><label className="sf-field"><span>Recording title</span><input maxLength={200} value={title} onChange={e=>setTitle(e.target.value)} placeholder="A neutral name for your recording" disabled={busy}/></label>{file&&<p className="sf-subtle">{file.name} · {(file.size/1024).toFixed(1)} KiB · not uploaded yet</p>}{error&&<div role="alert"><Notice danger>{error}</Notice></div>}<div className="sf-toolbar"><Button type="submit" disabled={busy}>{busy?'Uploading…':'Upload recording'}</Button><Link className="sf-button sf-button--secondary" to="/app/library">Cancel</Link></div><Notice>Only you and people you explicitly share with can access the saved recording. Separation starts after you review it.</Notice></form></GlassPanel>{file&&<div className="sf-upload-review"><AudioWorkspace key={`${file.name}:${file.lastModified}:${file.size}`} resources={[{id:'selected-file',kind:'original_audio',media_type:'audio/wav',url:null}]} provider={provider} filenames={{original:file.name}}/></div>}<UnsavedGuard when={!!file&&!busy}/></>;
}
