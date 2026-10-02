import type {Recording,ProcessingJob,Assignment} from './types';
import {DEMO_ENABLED} from '../config/runtime';
import {liveAuth} from '../auth/firebase';
// These contracts are intentionally separate from the local demonstration store.
// Firebase proves identity only. FastAPI must return roles and enforce all object access.
export interface AuthenticationAdapter {
 signIn(email:string,password:string):Promise<void>;
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
export const authAdapter:AuthenticationAdapter=DEMO_ENABLED?{signIn:unavailable,register:unavailable,signInWithGoogle:unavailable,sendPasswordReset:unavailable,signOut:async()=>{}}:{
 signIn:async(email,password)=>{await liveAuth.signIn(email,password);},
 register:async(name,email,password)=>{await liveAuth.register(name,email,password);},
 signInWithGoogle:async()=>{await liveAuth.google();},sendPasswordReset:email=>liveAuth.requestReset(email),signOut:()=>liveAuth.logout(),
};
export const apiAdapter:DataAdapter={getOwnRecordings:unavailable,requestEnsemble:unavailable,getAuthorizedAssignments:unavailable,getAuthorizedAudioUrl:unavailable};
