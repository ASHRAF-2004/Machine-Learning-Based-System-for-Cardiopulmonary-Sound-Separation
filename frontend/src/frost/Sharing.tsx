import {useEffect,useId,useRef,useState,type FormEvent} from 'react';
import {CaretDown,CaretUp,Check,MagnifyingGlass,ShareNetwork,SpinnerGap} from '@phosphor-icons/react';
import {useLive} from '../data/live';
import type {LiveGrant,LiveRecording,SharingRecipient} from '../data/liveTypes';
import {Button,GlassPanel,Notice,ProfileIdentity,SectionHeading} from './primitives';
import {errorMessage,useResource} from './data';

const sourceLabel:Record<string,string>={original_audio:'Original audio only',heart_audio:'Heart audio only',lung_audio:'Lung audio only',result:'Result details only',waveform:'Waveform only',spectrogram:'Spectrogram only',context:'Recording context only'};
function scopeLabel(record:LiveRecording,id:string|null){return id?(sourceLabel[record.resources.find(item=>item.id===id)?.kind||'']||'Exact shared resource'):'Recording & all audio';}
function grantStatus(grant:LiveGrant){return grant.status==='revoked'?'Revoked':grant.expires_at!==null&&grant.expires_at<=Date.now()/1000?'Expired':'Active';}

export function Sharing({record}:{record:LiveRecording}){
  const {api,session}=useLive(),data=useResource<{items:LiveGrant[]}>(`/recordings/${record.id}/grants`);
  const [query,setQuery]=useState(''),[recipient,setRecipient]=useState<SharingRecipient|null>(null);
  const [permission,setPermission]=useState<'read'|'review'>('read'),[resource,setResource]=useState('');
  const [pending,setPending]=useState<'finding'|'saving'|'revoking'|null>(null),[error,setError]=useState(''),[saved,setSaved]=useState('');
  const request=useRef<AbortController|null>(null);
  const handleId=useId(),handleHelpId=useId();
  useEffect(()=>()=>request.current?.abort(),[api,record.id]);
  const selectable=record.resources.filter(item=>permission==='read'||['original_audio','result'].includes(item.kind));
  const available=Boolean(session?.user.handle);

  function editQuery(value:string){request.current?.abort();setPending(null);setQuery(value);setRecipient(null);setError('');setSaved('');}
  async function find(event:FormEvent){
    event.preventDefault();if(pending||!query.trim())return;
    const controller=new AbortController();request.current=controller;setPending('finding');setError('');setSaved('');setRecipient(null);
    try{
      const value=await api.json<SharingRecipient>(`/recordings/${record.id}/sharing-recipient`,{method:'POST',body:JSON.stringify({handle:query.trim()}),signal:controller.signal});
      if(!controller.signal.aborted){setRecipient(value);setPermission('read');setResource(record.resources.find(item=>item.kind==='heart_audio')?.id||record.original_resource_id||'');}
    }catch(failure){if(!controller.signal.aborted)setError(errorMessage(failure));}
    finally{if(!controller.signal.aborted)setPending(null);}
  }
  async function mutate(action:(signal:AbortSignal)=>Promise<unknown>,kind:'saving'|'revoking',success:string){
    if(pending)return;const controller=new AbortController();request.current=controller;setPending(kind);setError('');setSaved('');
    try{await action(controller.signal);if(!controller.signal.aborted){setSaved(success);data.reload();window.dispatchEvent(new Event('sf-review-updated'));if(kind==='saving')setRecipient(null);}}
    catch(failure){if(!controller.signal.aborted){setError(errorMessage(failure));if(kind==='saving')setRecipient(null);}}
    finally{if(!controller.signal.aborted)setPending(null);}
  }
  return <GlassPanel className="sf-sharing" label="Recording sharing">
    <SectionHeading title="Share with someone" description="Find a person by their exact handle. Their email stays private."/>
    {available?<form onSubmit={find}>
      <div className="sf-field"><label htmlFor={handleId}>Share with @username</label><div className="sf-input-action">
        <input id={handleId} required value={query} onChange={event=>editQuery(event.target.value)} disabled={pending==='saving'||pending==='revoking'} autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={21} placeholder="@handle" aria-describedby={handleHelpId}/>
        <Button type="submit" variant="secondary" disabled={!!pending||!query.trim()}>{pending==='finding'?<SpinnerGap className="sf-working-spinner" size={18}/>:<MagnifyingGlass size={18}/>} {pending==='finding'?'Finding…':'Find person'}</Button>
      </div><small id={handleHelpId}>Ask them for their handle from Profile & settings. There is no public people directory.</small></div>
    </form>:<Notice>Handle sharing is not available on this server yet. Existing permissions remain unchanged.</Notice>}
    {recipient&&<div className="sf-share-match">
      <ProfileIdentity name={recipient.display_name||recipient.handle} handle={recipient.handle}/>
      <form onSubmit={event=>{event.preventDefault();void mutate(signal=>api.json(`/recordings/${record.id}/grants`,{method:'POST',signal,body:JSON.stringify({recipient_handle:recipient.handle,recipient_public_id:recipient.public_id,permission,...(resource?{resource_id:resource}:{})})}),'saving',`Shared with @${recipient.handle}.`);}}>
        <div className="sf-sharing-options">
          <label className="sf-field"><span>Permission</span><select value={permission} disabled={!!pending} onChange={event=>{setPermission(event.target.value as 'read'|'review');setResource('');}}><option value="read">Listen / read</option><option value="review">Analyst review</option></select></label>
          <label className="sf-field"><span>What can they access?</span><select value={resource} disabled={!!pending} onChange={event=>setResource(event.target.value)} required={permission==='review'}>
            {permission==='review'&&<option value="">Choose an exact original or result</option>}
            {selectable.map(item=><option key={item.id} value={item.id}>{sourceLabel[item.kind]||item.kind.replaceAll('_',' ')}</option>)}
            {permission==='read'&&<option value="">Recording & all audio</option>}
          </select></label>
        </div>
        <p className="sf-subtle">{permission==='review'?'Review requires a current Audio Analyst and an exact original or result. Audio outputs need their own permission.':resource?'Only this resource is shared. Other audio and result details remain private unless separately granted.':'This grants access to the recording, its original and separated audio, and result details.'}</p>
        <Button type="submit" disabled={!!pending||permission==='review'&&!resource}><ShareNetwork size={18}/>{pending==='saving'?'Sharing…':'Share access'}</Button>
      </form>
    </div>}
    {error&&<Notice danger>{error}</Notice>}{saved&&<p className="sf-sharing-success" role="status"><Check size={16}/>{saved}</p>}
    <section className="sf-sharing-existing" aria-label="Existing sharing" aria-busy={data.loading}>
      <div className="sf-sharing-list-heading"><h3>People with access</h3><Button variant="ghost" disabled={!!pending} onClick={data.reload}>Refresh access</Button></div>
      {data.loading&&!data.value&&<p role="status">Loading sharing…</p>}
      {data.error?<Notice danger>{data.error}</Notice>:data.value&&<GrantList record={record} grants={data.value.items} busy={!!pending} revoke={grant=>{
        if(window.confirm('Revoke this permission? Other active grants may still allow access.'))void mutate(signal=>api.json(`/grants/${grant.id}`,{method:'DELETE',signal}),'revoking','Permission revoked.');
      }} revokeAll={grant=>{
        if(window.confirm('Revoke all this person’s access to this recording? Already downloaded files cannot be recalled.'))void mutate(signal=>api.json(`/recordings/${record.id}/revoke-access`,{method:'POST',signal,body:JSON.stringify({recipient_id:grant.recipient_id,confirmed_recording_id:record.id})}),'revoking','All permissions on this recording revoked.');
      }}/>}
    </section>
  </GlassPanel>;
}

function GrantList({record,grants,busy,revoke,revokeAll}:{record:LiveRecording;grants:LiveGrant[];busy:boolean;revoke:(grant:LiveGrant)=>void;revokeAll:(grant:LiveGrant)=>void}){
  const [expanded,setExpanded]=useState(false),listId=useId();
  const sorted=[...grants].sort((a,b)=>Number(grantStatus(b)==='Active')-Number(grantStatus(a)==='Active')||b.created_at-a.created_at);
  const active=sorted.filter(grant=>grantStatus(grant)==='Active');
  const visible=expanded?sorted:active.slice(0,3),hiddenCount=grants.length-active.slice(0,3).length;
  if(!grants.length)return <p className="sf-subtle">No one else has access. Your recording is private.</p>;
  return <>
    {!active.length&&!expanded&&<p className="sf-subtle">No one else has access. Your recording is private.</p>}
    <ul className="sf-grant-list" id={listId}>{visible.map(grant=><li key={grant.id} data-grant-id={grant.id}>
      <div><strong>{grant.recipient?.display_name||grant.recipient?.handle||'Recipient details unavailable'}</strong>{grant.recipient?.handle&&<span>@{grant.recipient.handle}</span>}<small>{scopeLabel(record,grant.resource_id)} · {grant.permission==='review'?'Analyst review':'Listen / read'}</small></div>
      <span className="sf-grant-status">{grantStatus(grant)}</span>
      <div className="sf-grant-actions"><Button variant="ghost" disabled={busy||grant.status==='revoked'} onClick={()=>revoke(grant)}>Revoke</Button><details><summary>More</summary><Button variant="danger" disabled={busy||grant.status==='revoked'} onClick={()=>revokeAll(grant)}>Revoke all access</Button></details></div>
    </li>)}</ul>
    {hiddenCount>0&&<Button variant="ghost" aria-expanded={expanded} aria-controls={listId} onClick={()=>setExpanded(value=>!value)}>{expanded?<CaretUp size={16}/>:<CaretDown size={16}/>} {expanded?'See less':`See more (${hiddenCount})`}</Button>}
    <p className="sf-sharing-footnote">Active permissions are shown first. Revoking one does not remove other grants. Already downloaded files cannot be recalled.</p>
  </>;
}
