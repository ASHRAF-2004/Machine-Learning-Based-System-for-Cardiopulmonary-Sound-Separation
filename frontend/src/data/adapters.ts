import type {User,Recording,ProcessingJob,Assignment} from './types';
// These contracts are intentionally separate from the local demonstration store.
// Firebase proves identity only. FastAPI must return roles and enforce all object access.
export interface AuthenticationAdapter {
 signIn(email:string,password:string):Promise<User>;
 register(name:string,email:string,password:string):Promise<void>;
 signInWithGoogle():Promise<void>;
 sendPasswordReset(email:string):Promise<void>;
 signOut():Promise<void>;
}
export interface DataAdapter {
 getOwnRecordings():Promise<Recording[]>;
 requestEnsemble(recordingId:string):Promise<ProcessingJob>;
 getAuthorizedAssignments():Promise<Assignment[]>;
 getAuthorizedAudioUrl(recordingId:string,component:'original'|'heart'|'lung'):Promise<string>;
}
const unavailable=async():Promise<never>=>{throw new Error('Live integration is not configured. Use the explicitly labelled development demonstration.');};
export const authAdapter:AuthenticationAdapter={signIn:unavailable,register:unavailable,signInWithGoogle:unavailable,sendPasswordReset:unavailable,signOut:async()=>{}};
export const apiAdapter:DataAdapter={getOwnRecordings:unavailable,requestEnsemble:unavailable,getAuthorizedAssignments:unavailable,getAuthorizedAudioUrl:unavailable};
