import {getApps, initializeApp} from 'firebase/app';
import {applyActionCode, browserPopupRedirectResolver, browserSessionPersistence,
  checkActionCode, confirmPasswordReset, createUserWithEmailAndPassword, GoogleAuthProvider,
  initializeAuth, onIdTokenChanged, reload, sendEmailVerification, sendPasswordResetEmail,
  signInWithEmailAndPassword, signInWithPopup, signOut, updateProfile,
  verifyPasswordResetCode, type Auth, type User} from 'firebase/auth';
import {DEMO_ENABLED, firebaseConfiguration, PUBLIC_ORIGIN} from '../config/runtime';

let auth: Auth | undefined;
export function firebaseAuth(): Auth {
  if (DEMO_ENABLED) throw new Error('Live authentication is disabled in demonstration mode.');
  if (!auth) {
    const config = firebaseConfiguration();
    const app = getApps().find(a => a.name === 'stethofuse-live') || initializeApp(config, 'stethofuse-live');
    // SDK-managed tab/session persistence only. No manual ID/refresh-token storage.
    // Session storage remains JS-readable: this is not an HttpOnly/XSS-proof session.
    auth = initializeAuth(app, {persistence: browserSessionPersistence, popupRedirectResolver: browserPopupRedirectResolver});
  }
  return auth;
}
const actionSettings = () => ({url: `${import.meta.env.DEV ? window.location.origin : PUBLIC_ORIGIN}/login`, handleCodeInApp: false});
export const liveAuth = {
  observe(next: (user: User | null) => void, error: (error: Error) => void) {
    return onIdTokenChanged(firebaseAuth(), next, error);
  },
  async current() { const value = firebaseAuth(); await value.authStateReady(); return value.currentUser; },
  async token(force = false) {
    const user = await this.current();
    if (!user) throw new Error('Sign in again to continue.');
    return user.getIdToken(force);
  },
  async signIn(email: string, password: string) { return (await signInWithEmailAndPassword(firebaseAuth(), email, password)).user; },
  async register(name: string, email: string, password: string) {
    const {user} = await createUserWithEmailAndPassword(firebaseAuth(), email, password);
    await updateProfile(user, {displayName: name});
    return user;
  },
  async google() {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({prompt: 'select_account'});
    return (await signInWithPopup(firebaseAuth(), provider)).user;
  },
  async logout() { if (auth) await signOut(auth); },
  async reload() {
    const user = await this.current();
    if (!user) return null;
    await reload(user); await user.getIdToken(true); return user;
  },
  async sendVerification() {
    const user = await this.current();
    if (!user) throw new Error('Sign in before requesting verification.');
    await sendEmailVerification(user, actionSettings());
  },
  async requestReset(email: string) { await sendPasswordResetEmail(firebaseAuth(), email, actionSettings()); },
  async checkReset(code: string) { await verifyPasswordResetCode(firebaseAuth(), code); },
  async reset(code: string, password: string) { await confirmPasswordReset(firebaseAuth(), code, password); },
  async verifyEmail(code: string) {
    const info = await checkActionCode(firebaseAuth(), code);
    if (info.operation !== 'VERIFY_EMAIL') throw new Error('This is not an email verification link.');
    await applyActionCode(firebaseAuth(), code);
    if (await this.current()) await this.reload();
  },
};

export function authErrorMessage(error: unknown): string {
  const code = typeof error === 'object' && error !== null && 'code' in error ? String(error.code) : '';
  const messages: Record<string, string> = {
    'auth/invalid-credential': 'The sign-in details could not be verified. Try again or request password recovery.',
    'auth/wrong-password': 'The sign-in details could not be verified. Try again or request password recovery.',
    'auth/user-not-found': 'The sign-in details could not be verified. Try again or request password recovery.',
    'auth/email-already-in-use': 'This account could not be created. Try signing in or request password recovery.',
    'auth/invalid-email': 'Enter a valid email address.',
    'auth/weak-password': 'Choose a stronger password that meets the provider policy.',
    'auth/password-does-not-meet-requirements': 'Choose a password that meets the configured provider policy.',
    'auth/too-many-requests': 'Too many attempts. Wait a little before trying again.',
    'auth/network-request-failed': 'The identity provider could not be reached. Check your connection and retry.',
    'auth/popup-closed-by-user': 'Google sign-in was cancelled. No completed sign-in was confirmed.',
    'auth/cancelled-popup-request': 'Another sign-in attempt is in progress. Finish it before retrying.',
    'auth/popup-blocked': 'The sign-in window was blocked. Allow popups for this site and try again.',
    'auth/account-exists-with-different-credential': 'Sign in using your original method. Provider-approved linking is required; matching email addresses do not link accounts.',
    'auth/user-disabled': 'This account is restricted. Contact the project owner.',
    'auth/user-token-expired': 'Your session has expired. Sign in again.',
    'auth/requires-recent-login': 'Sign out and sign in again before this sensitive action.',
    'auth/expired-action-code': 'This link has expired. Request a new link.',
    'auth/invalid-action-code': 'This link is invalid or has already been used. Request a new link.',
    'auth/operation-not-allowed': 'This sign-in method is not enabled. Contact the project owner.',
    'auth/unauthorized-domain': 'This origin is not authorized for sign-in. Contact the project owner.',
  };
  // Never render raw provider messages, which can contain email, tokens or request details.
  return messages[code] || 'The identity operation could not be completed. Please retry or contact the project owner.';
}
