import {useCallback,useMemo,useState} from 'react';
import {CheckCircle,Clock,Info,ShieldCheck,SpeakerHigh,WarningCircle,Waveform} from '@phosphor-icons/react';
import type {MediaResource} from '../data/liveTypes';
import {AudioPlayer} from './AudioPlayer';
import {sourceLabels,type MediaProvider,type SourceKind} from './contracts';
import {measureSignal,type AudioSignal} from './signal';
import {usePlayback} from './usePlayback';
import {useFrostPreferences} from './preferences';
import {SignalChart} from './SignalChart';
import {GlassPanel,MetricCard,Notice,SectionHeading,Segments} from './primitives';

function sourceKind(resource:MediaResource):SourceKind|null{
  return resource.kind==='heart_audio'?'heart':resource.kind==='lung_audio'?'lung':['original_audio','assigned_resource'].includes(resource.kind)?'original':null;
}
export function AudioWorkspace({resources,provider,filenames,analysis=true}:{resources:MediaResource[];provider:MediaProvider;filenames?:Partial<Record<SourceKind,string>>;analysis?:boolean}){
  const {gain,setGain}=useFrostPreferences(),playback=usePlayback(gain);
  const [selected,setSelected]=useState<SourceKind>('original'),[mode,setMode]=useState<'spectrogram'|'waveform'>('spectrogram');
  const [signals,setSignals]=useState<Partial<Record<SourceKind,AudioSignal>>>({});
  const sources=resources.map(resource=>({resource,kind:sourceKind(resource)})).filter((entry):entry is {resource:MediaResource;kind:SourceKind}=>entry.kind!==null);
  const source=sources.some(entry=>entry.kind===selected)?selected:sources[0]?.kind;
  const signal=source?signals[source]:undefined;
  const metrics=useMemo(()=>signal?measureSignal(signal):null,[signal]);
  const onLoaded=useCallback((kind:SourceKind,value:AudioSignal|null)=>setSignals(current=>{const next={...current};if(value)next[kind]=value;else delete next[kind];return next;}),[]);
  const select=(kind:SourceKind)=>{playback.pause();setSelected(kind);};
  const items=sources.map(entry=>({id:entry.kind,label:sourceLabels[entry.kind]}));
  if(!sources.length)return <GlassPanel><SectionHeading title="Audio access"/><Notice>No audio is included in your current access. A result or review grant does not automatically share its audio files.</Notice></GlassPanel>;
  return <div className="sf-detail-grid"><div className="sf-detail-main">
    <GlassPanel className="sf-audio-panel" label="Audio workspace"><SectionHeading title={sources.length>1?'Listen to the difference':'Listen closer'} description="Your available sounds, each with its own access." action={signal?<span className="sf-format">{signal.duration.toFixed(1)}s · {signal.rate.toLocaleString()} Hz · {signal.channels===1?'mono':'stereo'}</span>:undefined}/>
      <div className="sf-mobile-source"><Segments<SourceKind> label="Audio source" value={source!} onChange={select} items={items}/></div>
      {sources.map(({resource,kind})=><div className="sf-audio-lane" key={`${kind}:${resource.id}`} data-selected={source===kind}><AudioPlayer source={kind} resourceId={resource.id} provider={provider} playback={playback} gain={gain} setGain={setGain} onLoaded={onLoaded} filename={filenames?.[kind]}/></div>)}
      <div className="sf-playback-note"><SpeakerHigh size={15}/><span id="sf-playback-help">Playback volume up to 200%. Saved files stay unchanged.</span></div>{playback.error&&<Notice danger>{playback.error}</Notice>}
    </GlassPanel>
    {analysis&&<GlassPanel className="sf-analysis-panel" label="Technical signal analysis"><div className="sf-analysis-heading" id="analysis"><h2>Look closer</h2><Segments label="Analysis view" value={mode} onChange={setMode} items={[{id:'waveform',label:'Waveform'},{id:'spectrogram',label:'Spectrogram'}]}/></div><div className="sf-analysis-subhead"><Segments<SourceKind> label="Analysis source" value={source!} onChange={select} items={items}/><span><Info size={14}/>Technical measurements, not diagnosis</span></div>{signal?<><SignalChart signal={signal} source={source!} mode={mode}/><p className="sf-subtle">{sourceLabels[source!]} · {signal.rate.toLocaleString()} Hz stored WAV · {signal.channels===1?'unboosted mono samples':'unboosted stereo mean-mix samples for playback and analysis'}</p></>:<div className="sf-chart-loading" role="status"><Waveform size={24}/>Analysis unavailable until this audio is authorized and loaded.</div>}</GlassPanel>}
  </div>
  {analysis&&<aside className="sf-detail-rail"><GlassPanel className="sf-quality-panel"><SectionHeading title="Signal checks" description={source?`${sourceLabels[source]} audio`:'Audio unavailable'}/>{metrics&&signal?<>
    <ul className="sf-quality-list"><li>{metrics.lowLevel?<WarningCircle className="sf-check-warning" size={21} weight="fill"/>:<CheckCircle size={21} weight="fill"/>}<div><strong>{metrics.lowLevel?'Low signal level':'Usable signal level'}</strong><span>{metrics.lowLevel?'Consider playback boost':'Above the −35 dBFS review threshold'}</span></div></li><li>{metrics.clipped?<WarningCircle className="sf-check-warning" size={21} weight="fill"/>:<CheckCircle size={21} weight="fill"/>}<div><strong>{metrics.clipped?'Clipping to review':'No clipping detected'}</strong><span>{metrics.clipped} samples at |amplitude| ≥ 0.999</span></div></li><li><Clock size={21}/><div><strong>{signal.duration.toFixed(1)} seconds</strong><span>{signal.rate.toLocaleString()} Hz · {signal.channels===1?'Mono':'Stereo mean mix'}</span></div></li></ul>
    <dl className="sf-measurements"><MetricCard label="RMS level" value={`${metrics.rmsDb.toFixed(1)} dBFS`}/><MetricCard label="Peak level" value={`${metrics.peakDb.toFixed(1)} dBFS`}/><MetricCard label="Crest factor" value={metrics.crestDb===null?'Unavailable (silence)':`${metrics.crestDb.toFixed(1)} dB`}/></dl>
    <details className="sf-check-rules"><summary>How checks are measured</summary><p>Low level: RMS below −35 dBFS. Clipping: |sample| ≥ 0.999. Near-silence: 250 ms windows below −50 dBFS. These are technical checks, not clinical judgments.</p><p>Near-silence {(metrics.nearSilence*100).toFixed(1)}% · DC offset {metrics.dc.toFixed(5)}. Silence is shown at the −160 dBFS display floor.</p></details>
    </>:<p className="sf-subtle">Measurements are unavailable. No check is marked passed.</p>}</GlassPanel><GlassPanel className="sf-share-panel"><ShieldCheck size={27}/><h2>Private, by default.</h2><p>Access to one sound does not unlock the others.</p><p>Revocation blocks later requests. It cannot recall bytes already downloaded.</p></GlassPanel></aside>}
  </div>;
}
