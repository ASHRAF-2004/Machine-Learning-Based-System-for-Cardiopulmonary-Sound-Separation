import {useEffect, useRef, useState, type FormEvent, type ReactNode} from 'react';
import {Link, useLocation, useNavigate, useSearchParams} from 'react-router-dom';
import {ArrowLeft, ArrowRight, CheckCircle, Eye, EyeSlash, GoogleLogo, EnvelopeSimple, LockKey, ShieldCheck, Waveform, UploadSimple, Headphones, ArrowClockwise} from '@phosphor-icons/react';
import {Badge, Button, Field, InlineLink, Notice} from '../components/ui';
import Owl from '../components/Owl';
import {WinterArt} from '../components/WinterArt';
import {ReferenceArt} from '../components/ReferenceArt';
import {AuthScenery, AuthGoogleMark} from '../components/AuthScenery';
import {brand, DEMO_ENABLED} from '../brand';
import {useApp, roleLabel} from '../data/store';
import {authAdapter} from '../data/adapters';
import './public-pages.css';
import './public-reference.css';

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const delay = () => new Promise(resolve => setTimeout(resolve, 450));
const passwordAdvice = 'Use at least 12 characters, including a letter and a number. Do not use a real password in this demo.';

// Only application paths are eligible. Secrets and arbitrary query parameters are never propagated.
function safeReturn(value: string | null, fallback = '/app/dashboard') {
  if (!value || !value.startsWith('/app/') || /[\\\u0000-\u0020]/.test(value)) return fallback;
  try {
    const url = new URL(value, window.location.origin);
    const decoded = decodeURIComponent(url.pathname);
    if (url.origin !== window.location.origin || !decoded.startsWith('/app/') || /[\\\u0000-\u0020]|\/\//.test(decoded)) return fallback;
    return url.pathname;
  } catch { return fallback; }
}

function Logo() {
  return <Link to="/" className="brand-logo" aria-label={`${brand.name} home`}><img src={brand.logo} alt={brand.name} width="215" height="48"/></Link>;
}
function PublicNav() {
  return <header className="public-nav"><Logo/><nav className="public-nav-links" aria-label="Public navigation"><a href="/#how-it-works">How it works</a><a href="/#research-scope">Our purpose</a><Button to="/login" variant="secondary">Sign in</Button></nav></header>;
}
function Footer() {
  return <footer className="public-footer"><span>{brand.name} · {brand.researchNotice}</span><nav aria-label="Footer"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><a href="/#support">Help</a></nav></footer>;
}
function Snow() {
  const {preferences} = useApp();
  if (!preferences.snow || preferences.reducedMotion) return null;
  return <div className="snow-drift" aria-hidden="true">{Array.from({length: 13}, (_, i) => <i key={i} style={{left: `${(i * 23 + 11) % 100}%`, top: `${(i * 17) % 90}%`, animationDelay: `${-i * 2.7}s`, animationDuration: `${20 + (i % 4) * 4}s`}}/>)}</div>;
}

function Welcome() {
  return <div className="public-page welcome-page">
    <section className="winter-hero" aria-labelledby="welcome-title"><PublicNav/><Snow/>
      <main id="main" className="hero-inner"><div className="hero-copy"><p className="eyebrow">Cardiopulmonary sound separation</p><h1 id="welcome-title"><span>Hear the</span>{' '}<em>signals within.</em></h1><p>Separate mixed chest recordings into heart and lung components, with space to listen, compare and review.</p><div className="hero-actions"><Button to="/register">Get started <ArrowRight size={17}/></Button><Button to="/login" variant="secondary">Sign in</Button></div></div><Owl/></main>
    </section>
    <section className="public-section" id="how-it-works" aria-labelledby="workflow-title"><div className="welcome-section-intro"><h2 id="workflow-title">One recording.<br/>Room for every signal.</h2><p>A considered workflow, from first capture to a shared review. Keep your original recording and each processing run together.</p><WinterArt kind="signalFine"/></div><div className="workflow-grid">
      <article className="workflow-step"><UploadSimple size={29} weight="light"/><h3>Bring the recording</h3><p>Upload a WAV file or capture from a compatible audio input. Add pseudonymous context, without patient identifiers.</p></article>
      <article className="workflow-step"><Waveform size={29} weight="light"/><h3>Separate the components</h3><p>Request ensemble processing and keep working while the job runs. Each result stays linked to its source and processing version.</p></article>
      <article className="workflow-step"><Headphones size={29} weight="light"/><h3>Listen with context</h3><p>Compare original, heart and lung signals. Inspect waveforms and share a recording with an explicitly assigned analyst.</p></article>
    </div></section>
    <section className="public-band" id="research-scope" aria-labelledby="scope-title"><div className="public-section welcome-scope"><div><h2 id="scope-title">A focused tool.<br/>A thoughtful boundary.</h2><p>{brand.name} is a university research application for recording management and cardiopulmonary sound separation. It does not diagnose conditions, recommend treatment or replace professional judgment.</p><InlineLink to="/privacy">How access is intended to work</InlineLink></div><div className="scope-principles"><div><ShieldCheck size={23}/><div><h3>Your workspace, your recordings</h3><p>Each account has its own history. Sharing is explicit and can be revoked.</p></div></div><div><LockKey size={23}/><div><h3>Access follows permission</h3><p>Analysts review assigned files. Administration does not automatically grant access to private audio.</p></div></div>{DEMO_ENABLED && <Notice title="You are viewing a demonstration"><p>Fictional accounts, synthetic audio and simulated processing. No clinical recordings, authentication or model inference.</p><Link className="inline-link" to="/login#demo-personas">Explore the demo <ArrowRight size={16}/></Link></Notice>}</div></div></section>
    <section className="public-section welcome-help" id="support" aria-labelledby="support-title"><div><h2 id="support-title">Before you begin.</h2><p>A few practical details about this research workspace.</p><WinterArt kind="feather"/></div><div>
      <details><summary>Can I use this for diagnosis?</summary><p>No. This is a research and educational prototype for sound separation, recording organization and audio review. Outputs are not diagnostic findings or treatment advice.</p></details>
      {DEMO_ENABLED ? <details><summary>What can I try in the demonstration?</summary><p>Choose one of the clearly labelled fictional personas on the sign-in page. Explore separate staff workspaces, analyst assignments and administrative metadata. Only non-sensitive demonstration state is saved in this browser.</p><InlineLink to="/login#demo-personas">Choose a demo account</InlineLink></details> : <details><summary>How do I access my workspace?</summary><p>Open the sign-in page to access your workspace when account services are connected. Authentication is not configured in this build, so sign-in will explain its availability without creating a session.</p><InlineLink to="/login">Check sign-in availability</InlineLink></details>}
      <details><summary>Will my file or password be sent anywhere?</summary><p>The current demonstration does not upload audio, send emails or authenticate real credentials. Use fictional details. Live Firebase Authentication and permission-enforced FastAPI services require separate integration.</p></details>
      <details><summary>How do I get help with a recording?</summary><p>Signed-in users can open Help for upload, device and review guidance. For access restrictions, contact the project owner through your existing contact channel. A public support inbox has not been configured.</p><InlineLink to="/login?returnTo=%2Fapp%2Fhelp">Open workspace help</InlineLink></details>
    </div></section><Footer/>
  </div>;
}

function AuthLayout({children}: {children: ReactNode}) {
  const {pathname} = useLocation();
  return <div className={`auth-page reference-auth ${pathname === '/login' ? 'reference-login' : ''}`}><AuthScenery/><header className="auth-brand"><Logo/></header><aside className="auth-art-copy"><h2>A little space<br/>to listen closely.</h2><p>Heart and lung signals,<br/>brought into focus for<br/>research and review.</p></aside><div className="auth-form-wrap"><main className="auth-form" id="main">{children}</main></div><footer className="auth-foot"><Link to="/">Back to home</Link><span><Link to="/privacy">Privacy</Link><span aria-hidden="true"> · </span><Link to="/terms">Terms</Link></span></footer></div>;
}
function AuthTitle({title, description, icon}: {title: string; description: string; icon?: ReactNode}) {
  return <>{icon && <div className="auth-state-icon" aria-hidden="true">{icon}</div>}<h1>{title}</h1><p className="muted">{description}</p></>;
}
function DemoNotice({children}: {children?: ReactNode}) {
  return <p className="auth-demo-note">{DEMO_ENABLED ? <><strong>Development demonstration.</strong> {children || 'Use fictional details only. Live authentication is not connected.'}</> : <><strong>Authentication is not configured.</strong> No credentials will be sent. Please contact the project owner.</>}</p>;
}
function StatePicker({options, value, onChange}: {options: {id: string; label: string}[]; value: string; onChange: (value: string) => void}) {
  if (!DEMO_ENABLED) return null;
  return <details className="auth-state-picker"><summary>Development: preview page states</summary><Field label="Demo state"><select value={value} onChange={e => onChange(e.target.value)}>{options.map(o => <option value={o.id} key={o.id}>{o.label}</option>)}</select></Field><small>This changes the preview only. It does not verify a user or contact a provider.</small></details>;
}
function usePageState(fallback: string, choices: string[]) {
  const [params, setParams] = useSearchParams();
  const queryState = params.get('state');
  const value = DEMO_ENABLED && queryState && choices.includes(queryState) ? queryState : fallback;
  const update = (next: string) => {
    // Never copy oobCode, tokens or provider callback parameters into demo navigation.
    const clean = new URLSearchParams();
    if (DEMO_ENABLED) clean.set('state', next);
    const target = safeReturn(params.get('returnTo'), '');
    if (target) clean.set('returnTo', target);
    setParams(clean, {replace: true});
  };
  return [value, update] as const;
}
function PasswordInput({id, label, value, onChange, error, autoComplete = 'new-password', hint}: {id: string; label: string; value: string; onChange: (value: string) => void; error?: string; autoComplete?: string; hint?: string}) {
  const [visible, setVisible] = useState(false);
  return <Field label={label} error={error}><div className="password-field auth-input-icon"><LockKey size={18} aria-hidden="true"/><input id={id} name={id} aria-label={label} type={visible ? 'text' : 'password'} autoComplete={autoComplete} placeholder={autoComplete === 'current-password' ? 'Your password' : undefined} value={value} onChange={e => onChange(e.target.value)} aria-invalid={!!error} aria-describedby={hint ? `${id}-hint` : undefined} required/><button className="icon-button" type="button" aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(v => !v)}>{visible ? <EyeSlash size={19}/> : <Eye size={19}/>}</button></div>{hint && <small id={`${id}-hint`}>{hint}</small>}</Field>;
}
function GoogleButton() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function begin() {
    if (DEMO_ENABLED) { navigate('/auth/callback?state=completing'); return; }
    setBusy(true);
    try { await authAdapter.signInWithGoogle(); } catch { setError('Google sign-in is not connected. No Google account was accessed.'); } finally { setBusy(false); }
  }
  return <><Button variant="secondary" onClick={begin} disabled={busy}><AuthGoogleMark/>{busy ? 'Connecting…' : 'Continue with Google'}</Button>{error && <Notice tone="danger"><p>{error}</p></Notice>}</>;
}

function DemoPersonas() {
  const {state, loginPersona} = useApp();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  if (!DEMO_ENABLED) return null;
  return <details className="demo-entry" id="demo-personas" open={window.location.hash === '#demo-personas'}><summary>Explore with a fictional demo account <ArrowRight size={15}/></summary><p>No password needed. This development-only selector is not real sign-in and is not available in a normal production build.</p><div className="persona-list">{state.users.filter(u => ['USR-1001', 'USR-1002', 'USR-2001', 'USR-3001'].includes(u.id)).map((u, i) => <button className="persona-option" key={u.id} onClick={() => {
    try {
      loginPersona(u.id);
      navigate(u.status === 'disabled' ? '/account-disabled' : u.status === 'pending' ? '/verify-email' : safeReturn(params.get('returnTo'), u.role === 'admin' ? '/app/admin' : '/app/dashboard'));
    } catch (e) { setError(e instanceof Error ? e.message : 'Demo account unavailable.'); }
  }}><span className="avatar" aria-hidden="true">{u.name.split(' ').map(n => n[0]).join('')}</span><span><strong>{u.name}</strong><small>{i < 2 ? `Staff ${i === 0 ? 'A' : 'B'} · ` : ''}{roleLabel(u.role)}</small></span><Badge>Demo</Badge></button>)}</div>{error && <Notice tone="danger"><p>{error}</p></Notice>}</details>;
}

function Login() {
  const [view, setView] = usePageState('ready', ['ready', 'submitting', 'failure', 'offline']);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [remember, setRemember] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const next = {email: emailPattern.test(email.trim()) ? '' : 'Enter a valid email address.', password: password ? '' : 'Enter your password.'};
    setErrors(next);
    if (Object.values(next).some(Boolean)) { requestAnimationFrame(() => form.current?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus()); return; }
    setBusy(true); setFailure('');
    try {
      await delay();
      await authAdapter.signIn(email.trim(), password);
    } catch {
      setFailure(DEMO_ENABLED ? 'Live sign-in is not connected. Your credentials were not sent or stored. Use the fictional demo accounts below to explore.' : 'Sign-in is unavailable because the identity provider has not been configured. Please contact the project owner.');
    } finally { setPassword(''); setBusy(false); }
  }
  return <AuthLayout><AuthTitle title="Welcome back." description="Sign in to your own recording workspace."/><DemoNotice/>{view === 'failure' && <Notice tone="danger"><p>Demo: the supplied credentials could not be verified. Try again or use password recovery.</p></Notice>}{view === 'offline' && <Notice tone="warning"><p>You appear to be offline. Reconnect before signing in.</p></Notice>}<form ref={form} onSubmit={submit} noValidate aria-busy={busy || view === 'submitting'}>
    <Field label="Email address" error={errors.email}><div className="auth-input-icon"><EnvelopeSimple size={18} aria-hidden="true"/><input name="email" type="email" autoComplete="username" placeholder="you@domain.com" value={email} onChange={e => setEmail(e.target.value)} aria-invalid={!!errors.email} required/></div></Field>
    <PasswordInput id="password" label="Password" value={password} onChange={setPassword} error={errors.password} autoComplete="current-password"/>
    <div className="auth-links"><label className="remember-option"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} aria-describedby={remember ? 'persistence-unavailable' : undefined}/>Keep me signed in</label><Link to="/forgot-password">Forgot password?</Link></div>
    {remember && <p className="persistence-note" id="persistence-unavailable">Session persistence requires connected authentication. This preview does not save credentials or create a session.</p>}
    {failure && <Notice tone="danger"><p>{failure}</p></Notice>}<Button type="submit" disabled={busy || view === 'submitting' || view === 'offline'}>{busy || view === 'submitting' ? 'Signing in…' : 'Sign in'}<ArrowRight size={17}/></Button>
  </form><div className="form-divider">or</div><GoogleButton/><p className="auth-meta">New here? <Link to="/register">Create an account</Link></p><DemoPersonas/><StatePicker value={view} onChange={setView} options={[{id:'ready',label:'Ready'},{id:'submitting',label:'Submitting'},{id:'failure',label:'Sign-in failure'},{id:'offline',label:'Offline'}]}/></AuthLayout>;
}

function Register() {
  const [view, setView] = usePageState('ready', ['ready', 'submitting', 'failure', 'success']);
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [confirmation, setConfirmation] = useState(''); const [accepted, setAccepted] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({}); const [busy, setBusy] = useState(false); const [failure, setFailure] = useState(''); const form = useRef<HTMLFormElement>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const next = {name: name.trim().length >= 2 ? '' : 'Enter your name.', email: emailPattern.test(email.trim()) ? '' : 'Enter a valid email address.', password: password.length >= 12 && /[A-Za-z]/.test(password) && /[0-9]/.test(password) ? '' : 'Use at least 12 characters with a letter and a number.', confirmation: confirmation === password && confirmation ? '' : 'Passwords must match.', terms: accepted ? '' : 'Acknowledge the draft terms and privacy notice.'};
    setErrors(next); if (Object.values(next).some(Boolean)) { requestAnimationFrame(() => form.current?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus()); return; }
    setBusy(true); setFailure('');
    try { await delay(); if (DEMO_ENABLED) setView('success'); else await authAdapter.register(name.trim(), email.trim(), password); }
    catch { setFailure('Account creation is not available until authentication is connected. Nothing was sent or stored.'); }
    finally { setPassword(''); setConfirmation(''); setBusy(false); }
  }
  return <AuthLayout><AuthTitle title={view === 'success' ? 'A place to begin.' : 'Create your workspace.'} description={view === 'success' ? 'Your registration form is ready for the future identity-provider connection.' : 'Keep your recordings, processing runs and reviews together.'}/><DemoNotice/>{view === 'success' ? <><Notice title="Demo registration preview"><p>The form passed validation. No real account was created, no password was stored and no email was sent.</p></Notice><Button to="/verify-email">Preview email verification <ArrowRight size={17}/></Button><p className="auth-meta"><Link to="/login#demo-personas">Continue with an existing fictional account</Link></p></> : <><form ref={form} noValidate onSubmit={submit} aria-busy={busy || view === 'submitting'}>
    <Field label="Full name" error={errors.name}><input name="name" autoComplete="name" value={name} onChange={e => setName(e.target.value)} aria-invalid={!!errors.name} required/></Field>
    <Field label="Email address" error={errors.email}><input name="email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} aria-invalid={!!errors.email} required/></Field>
    <PasswordInput id="new-password" label="Password" value={password} onChange={setPassword} error={errors.password} hint={passwordAdvice}/>
    <PasswordInput id="confirm-password" label="Confirm password" value={confirmation} onChange={setConfirmation} error={errors.confirmation}/>
    <label className="auth-consent"><input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} aria-invalid={!!errors.terms}/><span>I have read the <Link to="/terms">draft terms</Link> and <Link to="/privacy">privacy notice</Link>.</span></label>{errors.terms && <p className="field-error" role="alert">{errors.terms}</p>}
    <p className="auth-account-scope">New accounts start in a personal Healthcare Staff workspace. This application role does not verify professional credentials.</p>
    {(failure || view === 'failure') && <Notice tone="danger"><p>{failure || 'Demo: account creation could not be completed. Please retry. No account was created.'}</p></Notice>}
    <Button type="submit" disabled={busy || view === 'submitting'}>{busy || view === 'submitting' ? 'Preparing account…' : 'Create account'}<ArrowRight size={17}/></Button>
  </form><div className="form-divider">or</div><GoogleButton/></>}<p className="auth-meta">Already have an account? <Link to="/login">Sign in</Link></p><StatePicker value={view} onChange={setView} options={[{id:'ready',label:'Ready'},{id:'submitting',label:'Submitting'},{id:'failure',label:'Registration failure'},{id:'success',label:'Validation success preview'}]}/></AuthLayout>;
}

function useCooldown(initial = 0) {
  const [remaining, setRemaining] = useState(initial);
  useEffect(() => { if (remaining <= 0) return; const timer = setTimeout(() => setRemaining(s => Math.max(0, s - 1)), 1000); return () => clearTimeout(timer); }, [remaining]);
  return [remaining, setRemaining] as const;
}
function ForgotPassword() {
  const [view, setView] = usePageState('ready', ['ready', 'success', 'throttled', 'failure']);
  const [email, setEmail] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [remaining, setRemaining] = useCooldown();
  useEffect(() => { if (view === 'throttled') setRemaining(30); }, [view, setRemaining]);
  async function submit(e: FormEvent) {
    e.preventDefault(); setError(''); if (!emailPattern.test(email.trim())) { setError('Enter a valid email address.'); return; } setBusy(true);
    try { await delay(); if (DEMO_ENABLED) { setView('success'); setRemaining(30); } else await authAdapter.sendPasswordReset(email.trim()); }
    catch { setError('Recovery is unavailable until the identity provider is connected. No email was sent.'); }
    finally { setBusy(false); }
  }
  return <AuthLayout><AuthTitle title={view === 'success' ? 'Check your inbox.' : 'A fresh start.'} description={view === 'success' ? 'If the address belongs to an eligible account, the connected service would send recovery instructions.' : 'Enter your email to request a password reset.'} icon={<EnvelopeSimple size={30} weight="light"/>}/><DemoNotice>Demo: no email was sent. We do not reveal whether an account exists.</DemoNotice>{view === 'success' ? <><Notice title="Request acknowledgment preview"><p>This is a demonstration of the recovery flow, not confirmation of email delivery. No account lookup was performed.</p></Notice><Button variant="secondary" disabled={remaining > 0} onClick={() => {setView('ready'); setError('');}}>{remaining > 0 ? `Try again in ${remaining}s` : 'Request another link'}</Button>{DEMO_ENABLED && <p className="auth-meta"><Link to="/reset-password?state=valid">Preview a valid reset form</Link></p>}</> : <form noValidate onSubmit={submit} aria-busy={busy}><Field label="Email address" error={error}><input type="email" name="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} aria-invalid={!!error} required/></Field>{view === 'throttled' && <Notice tone="warning"><p>{remaining > 0 ? `Too many requests. Please wait ${remaining} seconds before retrying.` : 'You can try again now.'}</p></Notice>}{view === 'failure' && <Notice tone="danger"><p>Demo: the recovery provider could not be reached. Please try again.</p></Notice>}<Button type="submit" disabled={busy || (view === 'throttled' && remaining > 0)}>{busy ? 'Requesting…' : 'Request reset link'}<ArrowRight size={17}/></Button></form>}<p className="auth-meta"><Link to="/login">Back to sign in</Link></p><StatePicker value={view} onChange={setView} options={[{id:'ready',label:'Ready'},{id:'success',label:'Generic acknowledgment'},{id:'throttled',label:'Rate limited'},{id:'failure',label:'Provider failure'}]}/></AuthLayout>;
}

function ResetPassword() {
  const [view, setView] = usePageState(DEMO_ENABLED ? 'valid' : 'invalid', ['valid', 'ready', 'expired', 'invalid', 'used', 'success', 'failure']);
  const [password, setPassword] = useState(''); const [confirmation, setConfirmation] = useState(''); const [errors, setErrors] = useState<Record<string, string>>({}); const [busy, setBusy] = useState(false);
  const badLink = ['expired', 'invalid', 'used'].includes(view);
  const title = {expired:'This link has expired.', invalid:'This link cannot be used.', used:'This link was already used.', success:'Your next sign-in is ready.'}[view] || 'Choose a new password.';
  async function submit(e: FormEvent) {
    e.preventDefault();
    const next = {password: password.length >= 12 && /[A-Za-z]/.test(password) && /[0-9]/.test(password) ? '' : 'Use at least 12 characters with a letter and a number.', confirmation: password === confirmation && confirmation ? '' : 'Passwords must match.'};
    setErrors(next); if (Object.values(next).some(Boolean)) return; setBusy(true); await delay(); setPassword(''); setConfirmation(''); setBusy(false); if (DEMO_ENABLED) setView('success');
  }
  return <AuthLayout><AuthTitle title={title} description={badLink ? 'Request a new recovery link to continue. Your existing account has not been changed.' : view === 'success' ? 'The password-reset success state is ready for review.' : 'Use a unique password you have not used elsewhere.'} icon={view === 'success' ? <CheckCircle size={31} weight="light"/> : <LockKey size={30} weight="light"/>}/><DemoNotice>Demo: no email was sent and no real password is changed. Do not enter a real password.</DemoNotice>{badLink ? <><Notice tone="warning"><p>{view === 'expired' ? 'Reset links are time-limited. This example has expired.' : view === 'used' ? 'Recovery links are single-use. Request another if you still need help.' : 'The recovery link is missing, invalid or cannot be verified because authentication is not connected.'}</p></Notice><Button to="/forgot-password">Request a new link</Button></> : view === 'success' ? <><Notice title="Demo: password reset preview complete"><p>Your input was validated and discarded. No password was sent, saved or changed. The real provider will confirm success when connected.</p></Notice><Button to="/login">Return to sign in <ArrowRight size={17}/></Button></> : <form noValidate onSubmit={submit} aria-busy={busy}>{view === 'failure' && <Notice tone="danger"><p>The update could not be completed. The existing password remains unchanged. Please retry.</p></Notice>}<PasswordInput id="new-password" label="New password" value={password} onChange={setPassword} error={errors.password} hint={passwordAdvice}/><PasswordInput id="confirm-password" label="Confirm new password" value={confirmation} onChange={setConfirmation} error={errors.confirmation}/><Button type="submit" disabled={busy || !DEMO_ENABLED}>{busy ? 'Validating…' : 'Reset password'}<ArrowRight size={17}/></Button></form>}{view !== 'success' && <p className="auth-meta"><Link to="/login">Back to sign in</Link></p>}<StatePicker value={view} onChange={setView} options={[{id:'valid',label:'Valid-link preview'},{id:'expired',label:'Expired link'},{id:'invalid',label:'Invalid link'},{id:'used',label:'Already-used link'},{id:'failure',label:'Update failed'},{id:'success',label:'Success preview'}]}/></AuthLayout>;
}

function VerifyEmail() {
  const [view, setView] = usePageState('pending', ['pending', 'success', 'verified', 'expired', 'invalid', 'failure', 'throttled']);
  const [remaining, setRemaining] = useCooldown(); const [sent, setSent] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const verified = view === 'verified' || view === 'success';
  useEffect(() => {setSent(false); if (view === 'throttled') setRemaining(30);}, [view, setRemaining]);
  async function resend() {setError(''); if (!DEMO_ENABLED) {setError('Verification delivery is not connected. No email was sent.'); return;} setBusy(true); await delay(); setBusy(false); setSent(true); setRemaining(30);}
  return <AuthLayout><AuthTitle title={verified ? 'Email verification preview.' : ['expired', 'invalid'].includes(view) ? 'Let’s try a new link.' : 'One more small step.'} description={verified ? 'This shows the verified state without modifying a real identity.' : 'Use the verification link from your identity provider before entering your workspace.'} icon={verified ? <CheckCircle size={31} weight="light"/> : <EnvelopeSimple size={31} weight="light"/>}/><DemoNotice>Demo: no email was sent. Verification is simulated and does not change account access.</DemoNotice>{verified ? <><Notice title="Demo verified state"><p>No live email address has been verified. In the connected application, Firebase verification is checked before backend workspace access.</p></Notice><Button to="/login">Continue to sign in</Button></> : <><Notice tone={['expired','invalid','failure'].includes(view) ? 'warning' : 'info'} title={['expired','invalid'].includes(view) ? 'Verification link unavailable' : 'Check the right inbox'}><p>{view === 'expired' ? 'This example link has expired. Request a new one from the connected identity provider.' : view === 'invalid' ? 'This example link is invalid or incomplete. Request a fresh verification email.' : view === 'failure' ? 'The provider could not verify the email. Please try again.' : 'In the live flow, check your inbox and spam folder. Return here after opening the verification link.'}</p></Notice>{sent && <p className="auth-success-message" role="status">Demo resend requested. No email was sent.</p>}{error && <Notice tone="danger"><p>{error}</p></Notice>}<Button onClick={resend} disabled={busy || remaining > 0}>{busy ? 'Preparing…' : remaining > 0 ? `Resend available in ${remaining}s` : 'Resend verification email'}</Button><p className="auth-meta"><Link to="/register">Use a different email</Link><span aria-hidden="true"> · </span><Link to="/login">Back to sign in</Link></p></>}<StatePicker value={view} onChange={setView} options={[{id:'pending',label:'Check inbox'},{id:'verified',label:'Verified preview'},{id:'expired',label:'Expired link'},{id:'invalid',label:'Invalid link'},{id:'failure',label:'Provider failure'},{id:'throttled',label:'Resend cooldown'}]}/></AuthLayout>;
}

function GoogleCallback() {
  const [view, setView] = usePageState(DEMO_ENABLED ? 'completing' : 'error', ['completing', 'cancelled', 'error', 'link-conflict']);
  const {search} = useLocation();
  useEffect(() => {if (view !== 'completing') return; const timer = setTimeout(() => setView('error'), 1600); return () => clearTimeout(timer);}, [view, search]);
  const titles = {completing:'Completing sign-in…', cancelled:'Sign-in was cancelled.', error:'Google is not connected.', 'link-conflict':'Keep your identities linked safely.'};
  const unavailableMessage = DEMO_ENABLED ? 'No authentication took place. Use a fictional demo account to explore, or ask the project owner to configure Firebase Authentication.' : 'No authentication took place. Ask the project owner to configure Firebase Authentication before trying to sign in.';
  return <AuthLayout><AuthTitle title={titles[view as keyof typeof titles]} description={view === 'completing' ? 'Checking the sign-in integration. Please keep this page open.' : view === 'cancelled' ? 'No new session was created. You can choose another sign-in method.' : view === 'link-conflict' ? 'An existing account needs provider-approved linking before this Google identity can be used.' : 'This build does not have a configured Google identity-provider connection.'} icon={<GoogleLogo size={31} weight="light"/>}/><DemoNotice>No Google account was contacted or linked. This screen never creates a successful session.</DemoNotice>{view === 'completing' ? <div className="auth-callback-pending" role="status"><span/><span/><p>Checking connection availability</p></div> : <><Notice tone={view === 'cancelled' ? 'info' : 'warning'}><p>{view === 'link-conflict' ? 'Sign in using the original method, then use the identity provider’s verified linking flow. Matching email strings alone are not permission to merge accounts.' : view === 'cancelled' ? 'You remain signed out of this attempted connection.' : unavailableMessage}</p></Notice><Button to="/login">Back to sign in</Button>{DEMO_ENABLED && <p className="auth-meta"><Link to="/login#demo-personas">Open development demo accounts</Link></p>}</>}<StatePicker value={view} onChange={setView} options={[{id:'completing',label:'Completing (then unavailable)'},{id:'cancelled',label:'User cancelled'},{id:'error',label:'Provider unavailable'},{id:'link-conflict',label:'Identity-linking conflict'}]}/></AuthLayout>;
}

function AuthAction() {
  const [params] = useSearchParams();
  // Action codes are deliberately neither read nor logged in this unconfigured frontend.
  const mode = params.get('mode');
  const target = mode === 'resetPassword' ? '/reset-password' : mode === 'verifyEmail' ? '/verify-email' : null;
  const demoState = DEMO_ENABLED && ['expired', 'invalid', 'used', 'success'].includes(params.get('state') || '') ? params.get('state')! : 'invalid';
  return <AuthLayout><AuthTitle title="An account action needs checking." description="Recovery and verification links must be validated by the configured identity provider." icon={<ShieldCheck size={31} weight="light"/>}/><DemoNotice>No action code is displayed, saved or submitted by this preview.</DemoNotice><Notice tone="warning"><p>{target ? 'This link cannot be verified while authentication is disconnected. You can inspect the matching account-action screen below.' : 'The action is missing or is not supported by this frontend. Request a fresh link using the appropriate recovery page.'}</p></Notice>{target && <Button to={`${target}?state=${demoState}`}>Open {mode === 'resetPassword' ? 'password recovery' : 'verification'} screen</Button>}<div className="auth-link-stack"><InlineLink to="/forgot-password">Request password recovery</InlineLink><InlineLink to="/verify-email">Email verification help</InlineLink><InlineLink to="/login">Back to sign in</InlineLink></div></AuthLayout>;
}

function AccountState({session = false}: {session?: boolean}) {
  const {logout} = useApp(); const navigate = useNavigate(); const [params] = useSearchParams();
  return <AuthLayout><AuthTitle title={session ? 'Let’s reconnect.' : 'This account is restricted.'} description={session ? 'Your session has expired. Reauthenticate before continuing in your workspace.' : 'Workspace access is disabled or restricted. This does not delete your account’s recordings.'} icon={<LockKey size={31} weight="light"/>}/><Notice tone="warning"><p>{session ? 'Non-sensitive demo drafts remain in this browser. Signing in again will return you to your intended application page.' : 'Please contact the project owner through your existing contact channel. The sign-in page cannot reactivate an account or change its role.'}</p></Notice>{DEMO_ENABLED && <DemoNotice>This is a demonstration account state. No real session or server permissions are changed.</DemoNotice>}<Button onClick={() => {logout(); navigate(`/login?returnTo=${encodeURIComponent(safeReturn(params.get('returnTo')))}`);}}>{session ? 'Sign in again' : 'Sign out and return to sign in'}<ArrowRight size={17}/></Button><p className="auth-meta"><a href="/#support">Get help</a></p></AuthLayout>;
}

function Legal({terms = false}: {terms?: boolean}) {
  return <div className="public-page legal-page"><PublicNav/><main id="main" className="legal-content"><p className="eyebrow">For project-owner review</p><h1>{terms ? 'Terms of use' : 'Privacy notice'}</h1><Notice title="Draft copy, not a legal-compliance statement"><p>This text describes the demonstration and the intended integration boundaries. The owner must approve operational policies, contact details and applicable legal terms before a live service is offered.</p></Notice>{terms ? <>
    <h2>A research workspace</h2><p>{brand.name} supports cardiopulmonary recording management, sound separation and audio review for research and education. It is not a diagnostic service, a certified medical device or a source of treatment recommendations.</p>
    <h2>Using the demonstration</h2><p>Use fictional account details and non-sensitive demonstration content. Do not enter patient identifiers or real passwords. Processing stages and outputs in demonstration mode are simulated and do not establish accuracy or comparative algorithm performance.</p>
    <h2>Your account and access</h2><p>In the intended connected application, identity is verified by the configured provider. Roles and recording access are controlled by the backend. A Healthcare Staff application role does not verify professional qualifications. You may only access recordings you own or have been explicitly permitted to review.</p>
    <h2>Audio and review content</h2><p>You are responsible for obtaining authorization to use any audio in a future live service. Review notes must remain non-diagnostic. Do not attempt to bypass access restrictions or use another person’s account. Separation outputs must be considered alongside their original recording and processing provenance.</p>
    <h2>Availability and changes</h2><p>This prototype may contain limitations, interruptions and incomplete integrations. No service-level commitment, clinical guarantee or suitability for patient care is offered. Availability, retention, liability and dispute terms require owner and appropriate legal review before deployment.</p>
    <h2>Questions or access problems</h2><p>Use your existing project-owner contact channel. A public support address has not yet been configured. Do not send credentials, reset links or sensitive recordings with a support request.</p>
  </> : <>
    <h2>What this build stores</h2><p>The local demonstration stores fictional accounts, recording metadata, preferences, notes and simulated processing history in your browser. The selected fictional persona is kept in session storage. This is not secure authentication.</p>
    <h2>What this build does not send</h2><p>The demonstration does not send authentication emails, upload your audio or execute separation models. Password inputs are temporary form state and are discarded after the preview action. Passwords, reset codes, provider tokens and private audio must not be stored in local storage.</p>
    <h2>Recording access</h2><p>Each intended live account owns its recordings and processing history. Sharing and review assignments grant explicit, revocable access. Administrator privileges do not automatically include access to private audio, passwords, reset links or account impersonation.</p>
    <h2>Future connected services</h2><p>Firebase Authentication is the intended identity provider. A future FastAPI integration must enforce authorization for every record, stream, download, visualization and mutation. Hosting location, provider disclosures, legal basis and real retention periods have not been finalized by this draft.</p>
    <h2>Your demonstration data</h2><p>Signed-in demo users can inspect Data and storage settings and request simulated export or deletion actions. Browser data can also be cleared through browser settings. Demo deletion does not claim to delete live server data. Do not place real health information in this build.</p>
    <h2>Before live use</h2><p>The project owner must confirm the operating organization, contact channel, data categories, security controls, retention policy and applicable rights before collecting real data. This notice is not a claim of GDPR, HIPAA or any other regulatory compliance.</p>
  </>}<div className="toolbar"><Button to="/" variant="secondary"><ArrowLeft size={17}/> Back to home</Button><InlineLink to={terms ? '/privacy' : '/terms'}>{terms ? 'Read privacy notice' : 'Read terms of use'}</InlineLink></div></main><Footer/></div>;
}

const utilityContent: Record<string, {code: string; title: string; text: string}> = {
  '/403': {code: '403', title: 'This space is private.', text: 'Your account does not have permission to open this page or recording. Ask its owner for explicit access, or return to your own workspace.'},
  '/404': {code: '404', title: 'A little off the path.', text: 'We could not find that page. The link may be incomplete, or the content may have moved.'},
  '/500': {code: '500', title: 'Something interrupted us.', text: 'The requested page could not be completed. Your saved demonstration data remains in this browser. Please try again.'},
  '/offline': {code: 'Offline', title: 'Waiting for a connection.', text: 'Reconnect to continue with connected services. Keep this tab open to preserve any unsaved form details.'},
  '/maintenance': {code: 'A brief pause', title: 'The workspace is resting.', text: 'The service is temporarily unavailable. Please try again later. No completion time has been confirmed.'},
};
function Utility({path}: {path: string}) {
  const {user} = useApp(); const [message, setMessage] = useState(''); const content = utilityContent[path] || utilityContent['/404'];
  return <div className="public-page utility-page"><PublicNav/><main id="main" className="utility-screen"><ReferenceArt kind="utilityLandscape"/><div className="utility-inner"><WinterArt kind="utilitySignal"/><div className={`utility-code ${path === '/offline' || path === '/maintenance' ? 'utility-code-text' : ''}`}>{content.code}</div><h1>{content.title}</h1><p>{content.text}</p><div className="toolbar">{['/offline','/500','/maintenance'].includes(path) && <Button onClick={() => setMessage(navigator.onLine ? 'This preview is reachable. Live service health is not connected; retrying did not change any data.' : 'The browser still reports no network connection.')}><ArrowClockwise size={17}/> Try again</Button>}<Button to={user ? '/app/dashboard' : '/'} variant="secondary">{user ? 'My workspace' : 'Back to home'} <ArrowRight size={17}/></Button>{path === '/403' && <Button to="/login" variant="ghost">Switch account</Button>}</div>{message && <p role="status" className="utility-feedback">{message}</p>}<a className="inline-link" href="/#support">Get help <ArrowRight size={16}/></a></div></main><Footer/></div>;
}

export default function PublicPages() {
  const {pathname} = useLocation();
  switch (pathname.replace(/\/$/, '') || '/') {
    case '/': return <Welcome/>;
    case '/login': return <Login/>;
    case '/register': return <Register/>;
    case '/forgot-password': return <ForgotPassword/>;
    case '/reset-password': return <ResetPassword/>;
    case '/verify-email': return <VerifyEmail/>;
    case '/auth/action': return <AuthAction/>;
    case '/auth/callback': return <GoogleCallback/>;
    case '/account-disabled': return <AccountState/>;
    case '/session-expired': return <AccountState session/>;
    case '/privacy': return <Legal/>;
    case '/terms': return <Legal terms/>;
    default: return <Utility path={pathname}/>;
  }
}
