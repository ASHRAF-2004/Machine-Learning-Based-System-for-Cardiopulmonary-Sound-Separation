import {useEffect,useRef,useState,type FormEvent} from 'react';
import {useLocation,useNavigate,useSearchParams} from 'react-router-dom';
import {Bell,CheckCircle,Database,GearSix,LockSimple,Moon,Palette,ShieldCheck,SpeakerHigh,Sun,UserCircle} from '@phosphor-icons/react';
import {UnsavedGuard} from '../components/ui';
import {useLive} from '../data/live';
import {useApp} from '../data/store';
import {liveRoleLabel,type LivePreferences} from '../data/liveTypes';
import {authErrorMessage,liveAuth} from '../auth/firebase';
import {Button,CopyId,GlassPanel,Modal,Notice,ProfileIdentity,SectionHeading} from './primitives';
import {useFrostPreferences} from './preferences';
import {canonicalHandle,handleProblem} from './identity';
import {errorMessage} from './data';
import type {Theme} from './contracts';

type Section = 'profile'|'appearance'|'audio'|'notifications'|'privacy'|'security';
const sections = [
  {id:'profile',label:'Profile',Icon:UserCircle}, {id:'appearance',label:'Appearance',Icon:Palette},
  {id:'audio',label:'Audio',Icon:SpeakerHigh}, {id:'notifications',label:'Notifications',Icon:Bell},
  {id:'privacy',label:'Privacy & data',Icon:Database}, {id:'security',label:'Security',Icon:LockSimple},
] as const;
const aliases:Record<string,Section> = {general:'profile',recording:'audio',data:'privacy'};

export default function Account() {
  const {session}=useLive(),user=session!.user;
  const [params]=useSearchParams(),location=useLocation(),navigate=useNavigate();
  const requested=params.get('section')||'profile';
  const section:Section=location.pathname==='/app/profile'?'profile':aliases[requested]||
    (sections.some(item=>item.id===requested)?requested as Section:'profile');
  return <>
    <header className="sf-page-heading"><div><h1>Make it yours.</h1><p>Your identity, your workspace, your preferences.</p></div><span className="sf-settings-private"><ShieldCheck size={17}/>Personal settings</span></header>
    <div className="sf-settings-layout">
      <nav className="sf-settings-nav" aria-label="Settings sections">{sections.map(({id,label,Icon})=><button key={id} type="button" aria-pressed={section===id} onClick={()=>navigate(id==='profile'?'/app/profile':`/app/settings?section=${id}`)}><Icon size={20}/>{label}</button>)}<p><ShieldCheck size={17}/><span>Your recordings stay private. A handle or public ID never gives someone access.</span></p></nav>
      <GlassPanel className="sf-settings-content" label={sections.find(item=>item.id===section)!.label}>
        <AccountSection key={`${user.id}:${section}`} section={section}/>
      </GlassPanel>
    </div>
  </>;
}

function AccountSection({section}:{section:Section}) {
  switch(section) {
    case 'profile': return <Profile/>;
    case 'appearance': return <Appearance/>;
    case 'audio': return <AudioSettings/>;
    case 'security': return <Security/>;
    case 'notifications': return <>
      <SectionHeading title="Notifications" description="Stay in step with your workspace."/>
      <Notice>Email and workflow notifications are not connected yet. Processing status is saved in your Library; no notification delivery is simulated.</Notice>
    </>;
    case 'privacy': return <>
      <SectionHeading title="Your data, under your control" description="Your recordings remain private and available only through authorized access."/>
      <div className="sf-setting-row">
        <div><h3>Export my data</h3><p>Private account exports are planned, but are not available in this version.</p></div>
        <Button variant="secondary" disabled>Not available yet</Button>
      </div>
      <div className="sf-setting-row sf-danger-row">
        <div><h3>Delete account</h3><p>This will require a recent sign-in and explicit confirmation. The deletion service is not connected.</p></div>
        <Button variant="danger" disabled>Not available yet</Button>
      </div>
    </>;
  }
}

function Profile() {
  const {session,api,refreshAccount}=useLive(),user=session!.user;
  const [name,setName]=useState(user.display_name),[handle,setHandle]=useState(user.handle||'');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false),[confirm,setConfirm]=useState(false);
  const request=useRef<AbortController|null>(null);
  useEffect(()=>{setName(user.display_name);setHandle(user.handle||'');},[user.display_name,user.handle]);
  useEffect(()=>()=>request.current?.abort(),[api]);
  const available=!!user.handle&&user.handle_change_count!==undefined;
  const used=(user.handle_change_count||0)>=1;
  const normalized=canonicalHandle(handle),handleChanged=available&&normalized!==user.handle;
  const problem=available?handleProblem(handle):'';
  const dirty=name.trim()!==user.display_name||handleChanged;
  const valid=!!name.trim()&&!problem&&!busy&&dirty;
  async function save() {
    setConfirm(false);setBusy(true);setError('');setSaved(false);
    const controller=new AbortController();request.current?.abort();request.current=controller;
    try {
      await api.json('/auth/me',{method:'PATCH',signal:controller.signal,body:JSON.stringify({display_name:name.trim(),...(handleChanged?{handle:normalized}:{})})});
      if(!controller.signal.aborted){await refreshAccount();setSaved(true);}
    } catch(failure) {if(!controller.signal.aborted)setError(errorMessage(failure));}
    finally {if(!controller.signal.aborted)setBusy(false);}
  }
  function submit(event:FormEvent) {event.preventDefault();if(!valid)return;handleChanged?setConfirm(true):void save();}
  return <>
    <SectionHeading title="Your profile" description="A familiar name, a handle of your own."/>
    <div className="sf-profile-summary"><ProfileIdentity name={user.display_name||'Your account'} handle={user.handle}/><span className="sf-account-role">{liveRoleLabel(user.role)}</span></div>
    <form onSubmit={submit}>
      <div className="sf-profile-fields">
        <label className="sf-field"><span>Display name</span><input required aria-label="Display name" maxLength={200} autoComplete="name" value={name} disabled={busy} onChange={event=>{setName(event.target.value);setSaved(false);}}/><small>Your display name can be edited whenever you need.</small></label>
        <label className="sf-field"><span>Handle</span><div className="sf-handle-input"><span aria-hidden="true">@</span><input aria-label="Handle" value={handle} maxLength={20} autoComplete="off" spellCheck={false} readOnly={used||!available} disabled={busy} aria-describedby="handle-guidance handle-problem" aria-invalid={!!problem} onChange={event=>{setHandle(event.target.value);setSaved(false);}}/></div><small id="handle-guidance">{!available?'Handles are not available on this server yet. Your display name can still be edited.':used?'Your one self-service handle change has been used. Your display name remains editable.':'One self-service change is available. 3–20 characters, starting with a letter.'}</small><small id="handle-problem" className="sf-field-error" role={problem?'alert':undefined}>{problem}</small></label>
      </div>
      {error&&<Notice danger>{error}</Notice>}{saved&&<p className="sf-account-saved" role="status"><CheckCircle size={17}/>Profile saved.</p>}
      <div className="sf-profile-save"><div>{user.public_id&&<CopyId value={user.public_id}/>}<span className="sf-profile-reference-note">{user.public_id?'Your permanent account reference':'Public reference not available on this server'}</span></div><Button type="submit" disabled={!valid}>{busy?'Saving…':'Save changes'}</Button></div>
    </form>
    <details className="sf-technical sf-account-details"><summary>Account details</summary><dl><dt>Email</dt><dd>{user.email}</dd><dt>Account status</dt><dd>{user.status}</dd><dt>Legacy sharing ID</dt><dd><CopyId value={user.id}/></dd>{user.handle_changed_at&&<><dt>Handle changed</dt><dd>{new Date(user.handle_changed_at*1000).toLocaleString()}</dd></>}</dl><p>Existing sharing still uses this internal application ID. Sharing by handle is a separate, pending feature.</p></details>
    <UnsavedGuard when={dirty&&!busy} includeSearch/>
    {confirm&&<Modal title="Make this handle yours?" onClose={()=>setConfirm(false)}><p>Your handle will change to <strong>@{normalized}</strong>. This uses your one self-service change. Your account reference, recordings and access permissions stay unchanged.</p><div className="sf-dialog-actions"><Button variant="secondary" onClick={()=>setConfirm(false)}>Keep editing</Button><Button onClick={()=>void save()}>Confirm handle change</Button></div></Modal>}
  </>;
}

function Appearance() {
  const {theme,setTheme}=useFrostPreferences(),{preferences,savePreferences}=useLive();
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const appearance=preferences.appearance||{};
  const options:{id:Theme;title:string;note:string}[]=[{id:'system',title:'System',note:'Follow your device'},{id:'frost',title:'Frost',note:'A clear, light workspace'},{id:'midnight',title:'Midnight',note:'A calm, low-light workspace'}];
  async function save(value:LivePreferences) {setBusy(true);setError('');try{await savePreferences(value);}catch(failure){setError(errorMessage(failure));}finally{setBusy(false);}}
  return <><SectionHeading title="Appearance" description="Choose how StethoFuse looks on this device."/><div className="sf-theme-options" role="group" aria-label="Appearance theme">{options.map(option=><button key={option.id} type="button" className={`sf-theme-option sf-theme-option--${option.id}`} aria-pressed={theme===option.id} onClick={()=>setTheme(option.id)}><span className="sf-theme-mini" aria-hidden="true"><i/><span><b/><b/><b/></span></span><span className="sf-theme-option-label">{option.id==='midnight'?<Moon size={17}/>:option.id==='frost'?<Sun size={17}/>:<GearSix size={17}/>}<strong>{option.title}</strong>{theme===option.id&&<CheckCircle size={18} weight="fill"/>}</span><small>{option.note}</small></button>)}</div><div className="sf-account-toggles">{(['reducedMotion','snow','highContrast'] as const).map(key=><label key={key} className="sf-setting-row"><span><strong>{{reducedMotion:'Reduced motion',snow:'Winter snow',highContrast:'Higher contrast'}[key]}</strong><small>{key==='reducedMotion'?'Minimize decorative movement.':key==='snow'?'Keep the calm winter background.':'Use the existing accessibility preference.'}</small></span><input type="checkbox" disabled={busy} checked={appearance[key]===true||(key==='snow'&&appearance[key]!==false)} onChange={event=>void save({appearance:{...appearance,[key]:event.target.checked}})}/></label>)}</div>{error&&<Notice danger>{error}</Notice>}</>;
}

function AudioSettings() {
  const {gain,setGain}=useFrostPreferences();
  return <><div className="sf-audio-setting"><div><SpeakerHigh size={22}/><div><h2>Playback, your way.</h2><p>Playback volume up to 200%. Saved files stay unchanged.</p></div></div><label className="sf-gain" data-boosted={gain>100}><span>Preferred playback gain<strong>{gain}% {gain>100?'· Boost':''}</strong></span><div className="sf-gain-track"><input type="range" aria-label="Preferred playback gain" aria-valuetext={`${gain} percent${gain>100?', boost enabled':''}`} min={0} max={200} step={5} value={gain} onChange={event=>setGain(Number(event.target.value))}/><div className="sf-gain-scale" aria-hidden="true"><span>0%</span><span>100%</span><span>200%</span></div></div></label></div><Notice>Live recording is coming soon. Existing PCM WAV uploads use the same validated upload and separation pipeline.</Notice></>;
}

function Security() {
  const {session,logout}=useLive(),{notify}=useApp();
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  return <><SectionHeading title="Account security" description="Your existing sign-in and private-resource permissions stay in place."/><p className="sf-account-copy">Firebase manages sign-in. Handles and public reference IDs are presentation metadata, not credentials.</p><div className="sf-setting-row"><div><h3>Password recovery</h3><p>Use the existing provider recovery request for {session!.user.email}.</p></div><Button variant="secondary" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await liveAuth.requestReset(session!.user.email);notify('Firebase accepted the recovery request. Check your inbox if eligible.');}catch(failure){setError(authErrorMessage(failure));}finally{setBusy(false);}}}>Request password reset</Button></div><div className="sf-setting-row"><div><h3>This browser session</h3><p>Sign out without removing recordings or results.</p></div><Button variant="ghost" onClick={()=>void logout()}>Sign out</Button></div>{error&&<Notice danger>{error}</Notice>}<Notice>Username login, provider linking and other-device session management require separate security work. They are not simulated here.</Notice></>;
}
