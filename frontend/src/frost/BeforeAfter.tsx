import {Info,WarningCircle} from '@phosphor-icons/react';
import {sourceLabels,type SourceKind} from './contracts';
import type {AudioSignal,SignalMetrics} from './signal';
import {GlassPanel,SectionHeading} from './primitives';

type Measurements=Partial<Record<SourceKind,SignalMetrics>>;
type Signals=Partial<Record<SourceKind,AudioSignal>>;
const rows=[
  {label:'RMS level',key:'rmsDb',unit:'dBFS'},
  {label:'Peak level',key:'peakDb',unit:'dBFS'},
  {label:'Crest factor',key:'crestDb',unit:'dB'},
  {label:'Clipped samples',key:'clipped',unit:''},
  {label:'Near-silence',key:'nearSilence',unit:'%'},
] as const;

function value(metrics:SignalMetrics|undefined,key:typeof rows[number]['key'],unit:string){
  if(!metrics)return <span className="sf-comparison-unavailable">Unavailable</span>;
  const number=metrics[key];
  if(number===null)return <span className="sf-comparison-unavailable">Silent</span>;
  return <>{key==='clipped'?number:(key==='nearSilence'?number*100:number).toFixed(1)}{unit&&<small> {unit}</small>}</>;
}

export function BeforeAfter({kinds,signals,measurements}:{kinds:SourceKind[];signals:Signals;measurements:Measurements}){
  const hasOriginal=kinds.includes('original');
  return <GlassPanel className="sf-comparison-panel" label="Before and after signal comparison">
    <SectionHeading title={hasOriginal?'Before & after':'Your separated signals'}
      description={hasOriginal?'Original and separated audio · measured before playback boost':'Only sounds included in your access are compared.'}
      action={<span className="sf-comparison-label"><Info size={15}/>Measured audio</span>}/>
    <table className="sf-comparison-table">
      <caption className="sf-sr">Measured signal properties. A higher or lower value is not a separation-accuracy score.</caption>
      <thead><tr><th scope="col">Signal property</th>{kinds.map(kind=><th scope="col" key={kind} data-source={kind}>
        {sourceLabels[kind]}<small>{kind==='original'?'Before separation':'After separation'}</small>
      </th>)}</tr></thead>
      <tbody>{rows.map(row=><tr key={row.key}><th scope="row">{row.label}</th>{kinds.map(kind=><td key={kind} data-source={kind}>{value(measurements[kind],row.key,row.unit)}</td>)}</tr>)}
        <tr><th scope="row">Duration</th>{kinds.map(kind=><td key={kind}>{signals[kind]?`${signals[kind]!.duration.toFixed(1)} s`: <span className="sf-comparison-unavailable">Unavailable</span>}</td>)}</tr>
        <tr className="sf-comparison-flags"><th scope="row">Level / clipping</th>{kinds.map(kind=>{
          const metrics=measurements[kind];
          const flags=metrics?[metrics.crestDb===null?'Silent':metrics.lowLevel?'Low level':null,metrics.clipped?'Clipping':null].filter(Boolean):null;
          return <td key={kind}>{!flags?<span className="sf-comparison-unavailable">Not checked</span>:flags.length?<span className="sf-comparison-warning"><WarningCircle size={14}/>{flags.join(' · ')}</span>:<span>No flags</span>}</td>;
        })}</tr>
      </tbody>
    </table>
    <div className="sf-comparison-guidance"><Info size={20}/><div>
      <h3>Is the separation good enough?</h3>
      <p>These checks reveal signal issues, not separation accuracy. Listen to Heart and Lung separately{hasOriginal?' and compare them with Original':''}. Matching clean reference recordings are needed to measure separation quality.</p>
      <details><summary>What a changed crest factor means</summary><p>Crest factor is peak level minus RMS level. A change shows a different balance of peaks and average energy; lower is not automatically better. Low level means RMS below −35 dBFS. Clipping flags samples at |amplitude| ≥ 0.999. Near-silence counts 250 ms windows below −50 dBFS. None of these checks detects source leakage or certifies a correct separation.</p></details>
    </div></div>
  </GlassPanel>;
}
