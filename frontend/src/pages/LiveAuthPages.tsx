import {useEffect,useRef,useState,type FormEvent} from 'react';
import {Link,Navigate,useNavigate,useSearchParams} from 'react-router-dom';
import {ArrowRight,EnvelopeSimple} from '@phosphor-icons/react';
import {AuthLayout,AuthTitle,PasswordInput,safeReturn} from './PublicPages';
import {Button,Field,Notice} from '../components/ui';
import {AuthGoogleMark} from '../components/AuthScenery';
import {authAdapter} from '../data/adapters';
import {liveAuth,authErrorMessage} from '../auth/firebase';
import {firebaseConfigurationError} from '../config/runtime';
import {useLive} from '../data/live';

const paths=new Set(['/login','/register','/forgot-password','/reset-password','/verify-email','/auth/action','/auth/callback','/account-disabled','/session-expired']);
export const isLiveAuthPath=(path:string)=>paths.has(path);
const validEmail=(email:string)=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
const strongPassword=(value:string)=>value.length>=12&&/[A-Za-z]/.test(value)&&/[0-9]/.test(value);
function ConfigurationNotice(){return firebaseConfigurationError?<Notice tone="warning" title="Authentication setup required"><p>{firebaseConfigurationError}</p></Notice>:null;}
function Feedback({error,message}:{error?:string;message?:string}){return <>{error&&<Notice tone="danger"><p>{error}</p></Notice>}{message&&<Notice><p role="status">{message}</p></Notice>}</>;}
function GoogleButton(){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');const navigate=useNavigate();
 async function begin(){setBusy(true);setError('');try{await authAdapter.signInWithGoogle();navigate('/app/dashboard');}catch(failure){setError(authErrorMessage(failure));}finally{setBusy(false);}}
 return <><Button variant="secondary" disabled={busy||!!firebaseConfigurationError} onClick={begin}><AuthGoogleMark/>{busy?'Connecting…':'Continue with Google'}</Button><Feedback error={error}/></>;
}
function SignIn({register=false}:{register?:boolean}){
 const {status,error:sessionError,refreshAccount}=useLive();const [params]=useSearchParams();const navigate=useNavigate();
 const [name,setName]=useState(''),[email,setEmail]=useState(''),[password,setPassword]=useState(''),[confirmation,setConfirmation]=useState('');
 const [accepted,setAccepted]=useState(false),[remember,setRemember]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [errors,setErrors]=useState<Record<string,string>>({});const form=useRef<HTMLFormElement>(null);
 const destination=safeReturn(params.get('returnTo'));
 if(status==='ready')return <Navigate replace to={destination}/>;
 if(status==='unverified'&&!register)return <Navigate replace to="/verify-email"/>;
 async function submit(event:FormEvent){
  event.preventDefault();const next={email:validEmail(email.trim())?'':'Enter a valid email address.',password:register?(strongPassword(password)?'':'Use at least 12 characters with a letter and a number.'):(password?'':'Enter your password.'),name:!register||name.trim().length>=2?'':'Enter your name.',confirmation:!register||password===confirmation?'':'Passwords must match.',terms:!register||accepted?'':'Acknowledge the draft terms and privacy notice.'};
  setErrors(next);if(Object.values(next).some(Boolean)){requestAnimationFrame(()=>form.current?.querySelector<HTMLElement>('[aria-invalid=true]')?.focus());return;}
  setBusy(true);setError('');
  try{if(register){await authAdapter.register(name.trim(),email.trim(),password);navigate('/verify-email');}else{await authAdapter.signIn(email.trim(),password);navigate(destination);}}
  catch(failure){setError(authErrorMessage(failure));}finally{setPassword('');setConfirmation('');setBusy(false);}
 }
 return <AuthLayout><AuthTitle title={register?'Create your workspace.':'Welcome back.'} description={register?'Keep your recordings, processing runs and reviews together.':'Sign in to your own recording workspace.'}/><ConfigurationNotice/>
  {status==='error'&&!firebaseConfigurationError&&<><Feedback error={sessionError}/><Button variant="secondary" onClick={()=>void refreshAccount()}>Retry account connection</Button></>}
  <form ref={form} noValidate onSubmit={submit} aria-busy={busy}>
   {register&&<Field label="Full name" error={errors.name}><input name="name" autoComplete="name" maxLength={200} value={name} onChange={e=>setName(e.target.value)} required/></Field>}
   <Field label="Email address" error={errors.email}><div className="auth-input-icon"><EnvelopeSimple size={18} aria-hidden="true"/><input name="email" aria-label="Email address" type="email" autoComplete="username" placeholder="you@domain.com" value={email} onChange={e=>setEmail(e.target.value)} aria-invalid={!!errors.email} required/></div></Field>
   <PasswordInput id={register?'new-password':'password'} label="Password" autoComplete={register?'new-password':'current-password'} value={password} onChange={setPassword} error={errors.password} hint={register?'Use at least 12 characters, including a letter and a number.':undefined}/>
   {register?<><PasswordInput id="confirm-password" label="Confirm password" value={confirmation} onChange={setConfirmation} error={errors.confirmation}/><label className="auth-consent"><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/><span>I have read the <Link to="/terms">draft terms</Link> and <Link to="/privacy">privacy notice</Link>.</span></label>{errors.terms&&<p role="alert" className="field-error">{errors.terms}</p>}<p className="auth-account-scope">The backend assigns new verified accounts a personal Healthcare Staff workspace. No privileged role can be selected here.</p></>:<><div className="auth-links"><label className="remember-option"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)} aria-describedby="session-persistence-policy"/>Keep me signed in</label><Link to="/forgot-password">Forgot password?</Link></div><p id="session-persistence-policy" className="persistence-note">{remember?'Only this browser session is retained; closing this tab ends SDK persistence. Long-term “remember me” is not enabled.':'Sign-in survives refresh in this tab using Firebase session persistence. Long-term sign-in is not enabled.'}</p></>}
   <Feedback error={error}/><Button type="submit" disabled={busy||!!firebaseConfigurationError}>{busy?(register?'Creating account…':'Signing in…'):(register?'Create account':'Sign in')}<ArrowRight size={17}/></Button>
  </form><div className="form-divider">or</div><GoogleButton/><p className="auth-meta">{register?'Already have an account? ':'New here? '}<Link to={register?'/login':'/register'}>{register?'Sign in':'Create an account'}</Link></p></AuthLayout>;
}
function Forgot(){
 const [email,setEmail]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 async function submit(e:FormEvent){e.preventDefault();setError('');if(!validEmail(email.trim())){setError('Enter a valid email address.');return;}setBusy(true);try{await authAdapter.sendPasswordReset(email.trim());setMessage('The provider accepted the recovery request. If this address is eligible, check its inbox and spam folder. Delivery is not guaranteed.');}catch(failure){setError(authErrorMessage(failure));}finally{setBusy(false);}}
 return <AuthLayout><AuthTitle title={message?'Check your inbox.':'A fresh start.'} description="Request recovery through Firebase without revealing whether an account exists."/><ConfigurationNotice/><form noValidate onSubmit={submit}><Field label="Email address"><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required/></Field><Feedback error={error} message={message}/><Button type="submit" disabled={busy||!!message||!!firebaseConfigurationError}>{busy?'Requesting…':'Request reset link'}</Button></form><p className="auth-meta"><Link to="/login">Back to sign in</Link></p></AuthLayout>;
}
function EmailAction({mode}:{mode:'resetPassword'|'verifyEmail'|null}){
 const [params,setParams]=useSearchParams();
 // Read once into component memory, then replace the sensitive URL. Never log,
 // forward, render or persist action codes. Reload requires reopening the email.
 const [code]=useState(()=>params.get('oobCode')||'');
 const [stage,setStage]=useState<'checking'|'ready'|'success'|'invalid'>('checking');
 const [error,setError]=useState(''),[password,setPassword]=useState(''),[confirmation,setConfirmation]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{setParams({}, {replace:true});let cancelled=false;
  if(!code||!mode||firebaseConfigurationError){setStage('invalid');return;}
  const operation=mode==='resetPassword'?liveAuth.checkReset(code):liveAuth.verifyEmail(code);
  void operation.then(()=>{if(!cancelled)setStage(mode==='resetPassword'?'ready':'success');}).catch(failure=>{if(!cancelled){setStage('invalid');setError(authErrorMessage(failure));}});
  return()=>{cancelled=true;};
 // Code consumption must not repeat when removing the query changes router state.
 },[code,mode]);
 async function reset(e:FormEvent){e.preventDefault();setError('');if(!strongPassword(password)||password!==confirmation){setError('Use at least 12 characters with a letter and a number, and matching passwords.');return;}setBusy(true);try{await liveAuth.reset(code,password);setStage('success');}catch(failure){setError(authErrorMessage(failure));setStage('invalid');}finally{setPassword('');setConfirmation('');setBusy(false);}}
 return <AuthLayout><AuthTitle title={stage==='success'?(mode==='verifyEmail'?'Your email is verified.':'Your password has been reset.'):stage==='invalid'?'This link cannot be used.':mode==='resetPassword'?'Choose a new password.':'Checking your verification link…'} description={stage==='success'?'The identity provider confirmed this action. Sign in to continue.':'Account links are validated by Firebase; URL preview states do not grant access.'}/><ConfigurationNotice/><Feedback error={error}/>{stage==='checking'?<p role="status">Checking the account link…</p>:stage==='ready'?<form onSubmit={reset}><PasswordInput id="new-password" label="New password" value={password} onChange={setPassword}/><PasswordInput id="confirm-password" label="Confirm new password" value={confirmation} onChange={setConfirmation}/><Button type="submit" disabled={busy}>{busy?'Updating…':'Reset password'}</Button></form>:stage==='invalid'?<><Notice tone="warning">The link is missing, expired, already used or invalid. Request a fresh link; no success is assumed.</Notice><Button to={mode==='verifyEmail'?'/verify-email':'/forgot-password'}>Request a new link</Button></>:null}<p className="auth-meta"><Link to="/login">Return to sign in</Link></p></AuthLayout>;
}
function Verification(){
 const {status,refreshIdentity,logout}=useLive();const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[remaining,setRemaining]=useState(0);
 useEffect(()=>{if(!remaining)return;const timer=setTimeout(()=>setRemaining(x=>x-1),1000);return()=>clearTimeout(timer);},[remaining]);
 async function run(action:()=>Promise<void>,sent=false){setBusy(true);setError('');try{await action();if(sent){setMessage('Firebase accepted the verification email request. Check your inbox and spam folder.');setRemaining(30);}}catch(failure){setError(authErrorMessage(failure));}finally{setBusy(false);}}
 if(status==='ready')return <Navigate replace to="/app/dashboard"/>;
 return <AuthLayout><AuthTitle title="One more small step." description="Verify your email with Firebase before entering your workspace."/><ConfigurationNotice/><Feedback error={error} message={message}/><Notice>The backend independently requires a verified identity. Opening this page or changing a URL does not verify an email.</Notice><Button disabled={busy||remaining>0||!!firebaseConfigurationError} onClick={()=>void run(()=>liveAuth.sendVerification(),true)}>{remaining?`Resend available in ${remaining}s`:'Send verification email'}</Button><Button variant="secondary" disabled={busy||!!firebaseConfigurationError} onClick={()=>void run(refreshIdentity)}>I have verified my email</Button><p className="auth-meta"><button className="inline-link" onClick={()=>void logout().catch(failure=>setError(authErrorMessage(failure)))}>Sign out to use a different account</button><span> · </span><Link to="/login">Back to sign in</Link></p></AuthLayout>;
}
function AccountState({expired=false}:{expired?:boolean}){
 const {logout}=useLive(),navigate=useNavigate();const [params]=useSearchParams();const [error,setError]=useState('');
 return <AuthLayout><AuthTitle title={expired?'Let’s reconnect.':'This account is restricted.'} description={expired?'Your identity session has expired. Sign in again to continue.':'Only trusted account management can restore workspace access.'}/><Notice>Protected data has been removed from this workspace. No local fictional account can bypass this state.</Notice><Feedback error={error}/><Button onClick={async()=>{try{await logout();navigate(`/login?returnTo=${encodeURIComponent(safeReturn(params.get('returnTo')))}`);}catch(failure){setError(authErrorMessage(failure));}}}>Sign out and return to sign in</Button></AuthLayout>;
}
export default function LiveAuthPages({path}:{path:string}){
 const [params]=useSearchParams();const [actionMode]=useState(()=>params.get('mode'));const [hasActionCode]=useState(()=>params.has('oobCode'));
 if(path==='/login')return <SignIn/>;
 if(path==='/register')return <SignIn register/>;
 if(path==='/forgot-password')return <Forgot/>;
 if(path==='/reset-password')return <EmailAction mode="resetPassword"/>;
 if(path==='/auth/action')return <EmailAction mode={actionMode==='resetPassword'||actionMode==='verifyEmail'?actionMode:null}/>;
 if(path==='/verify-email')return hasActionCode?<EmailAction mode="verifyEmail"/>:<Verification/>;
 if(path==='/account-disabled')return <AccountState/>;
 if(path==='/session-expired')return <AccountState expired/>;
 return <AuthLayout><AuthTitle title="Return to sign in." description="Google authentication completes through the official popup. This route is not a Firebase OAuth handler."/><Button to="/login">Back to sign in</Button></AuthLayout>;
}
