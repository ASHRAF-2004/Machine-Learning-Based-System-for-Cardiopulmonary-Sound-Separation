// TEST ONLY SDK stand-in. Not real Firebase or an authentication emulator.
const listeners=new Set();let active=null;
window.__m1SdkCalls=[];
const note=method=>window.__m1SdkCalls.push({method});
const failure=code=>Object.assign(new Error('Mock provider failure; no secrets.'),{code});
function user(uid,verified=true){return {uid,email:`${uid}@example.invalid`,displayName:uid,emailVerified:verified,async getIdToken(force){note(force?'token.force':'token.current');return `M1-MOCK:${uid}`;}};}
function publish(next){active.currentUser=next;if(next)sessionStorage.setItem('__m1_test_identity',JSON.stringify({uid:next.uid,verified:next.emailVerified}));else sessionStorage.removeItem('__m1_test_identity');for(const listener of listeners)queueMicrotask(()=>listener(next));}
export const browserSessionPersistence={type:'SESSION'};
export const browserPopupRedirectResolver={};
export function initializeAuth(app,options){note('initializeAuth');if(options.persistence!==browserSessionPersistence)throw new Error('Expected SDK session persistence');const saved=JSON.parse(sessionStorage.getItem('__m1_test_identity')||'null');active={currentUser:saved?user(saved.uid,saved.verified):null,authStateReady:async()=>{}};return active;}
export function onIdTokenChanged(auth,next){listeners.add(next);queueMicrotask(()=>next(auth.currentUser));return()=>listeners.delete(next);}
export async function signInWithEmailAndPassword(auth,email,password){note('signInWithEmailAndPassword');if(!password||email.startsWith('invalid'))throw failure('auth/invalid-credential');const value=user(email.split('@')[0],!email.startsWith('unverified'));publish(value);return{user:value};}
export async function createUserWithEmailAndPassword(auth,email,password){note('createUserWithEmailAndPassword');if(!password)throw failure('auth/weak-password');const value=user(email.split('@')[0],false);publish(value);return{user:value};}
export async function updateProfile(value,patch){note('updateProfile');value.displayName=patch.displayName;}
export class GoogleAuthProvider{setCustomParameters(params){if(params.prompt!=='select_account')throw new Error('Expected account choice');}}
export async function signInWithPopup(){note('signInWithPopup');const value=user('google');publish(value);return{user:value};}
export async function signOut(){note('signOut');publish(null);}
export async function reload(value){note('reload');if(window.__m1Verified){value.emailVerified=true;publish(value);}}
export async function sendEmailVerification(){note('sendEmailVerification');}
export async function sendPasswordResetEmail(){note('sendPasswordResetEmail');}
export async function verifyPasswordResetCode(auth,code){note('verifyPasswordResetCode');if(code!=='mock-reset')throw failure('auth/expired-action-code');return 'mock@example.invalid';}
export async function confirmPasswordReset(auth,code,password){note('confirmPasswordReset');if(code!=='mock-reset'||!password)throw failure('auth/invalid-action-code');}
export async function checkActionCode(auth,code){note('checkActionCode');if(code!=='mock-verify')throw failure('auth/invalid-action-code');return{operation:'VERIFY_EMAIL'};}
export async function applyActionCode(){note('applyActionCode');window.__m1Verified=true;}
