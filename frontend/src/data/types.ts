export type Role = 'staff' | 'analyst' | 'admin';
export type UserStatus = 'active' | 'disabled' | 'pending';
export interface AuthIdentity {provider:'password'|'google';linkedAt:string}
export interface User {id:string;name:string;email:string;role:Role;status:UserStatus;verified:boolean;identities:AuthIdentity[];createdAt:string;lastActive:string}
export interface RecordingMetadata {site:string;position:string;notes:string;device:string;label:string}
export interface Recording {id:string;ownerId:string;title:string;source:'upload'|'device'|'sample';createdAt:string;duration:number;sampleRate:number;channels:number;size:number;archived:boolean;metadata:RecordingMetadata;isDemo:true}
export type JobStatus = 'queued'|'processing'|'completed'|'partial'|'failed'|'cancelled';
export interface ProcessingJob {id:string;recordingId:string;ownerId:string;status:JobStatus;stage:number;startedAt:string;updatedAt:string;error?:string;resultId?:string;ensembleVersion:string}
export interface EnsembleRun {id:string;jobId:string;version:string;experts:{name:string;version:string;status:string}[];fusion:string;referenceAvailable:false}
export interface SeparationResult {id:string;recordingId:string;jobId:string;ownerId:string;createdAt:string;status:'completed'|'partial';run:EnsembleRun}
export interface Assignment {id:string;recordingId:string;ownerId:string;analystId:string;permission:'review'|'listen';status:'pending'|'in-review'|'reviewed'|'re-record'|'revoked';createdAt:string;updatedAt:string}
export type Share = Assignment;
export interface Review {id:string;assignmentId:string;authorId:string;notes:{id:string;time:number;text:string}[];decision:'draft'|'reviewed'|'re-record';summary:string;updatedAt:string}
export interface Notification {id:string;userId:string;title:string;body:string;href:string;read:boolean;createdAt:string}
export interface AuditEvent {id:string;actorId:string;action:string;targetId:string;time:string;outcome:'success'|'blocked';detail:string}
export interface UserPreferences {timezone:string;dateFormat:string;reducedMotion:boolean;snow:boolean;highContrast:boolean;emailNotifications:boolean;jobNotifications:boolean;reviewNotifications:boolean;defaultSite:string;defaultPosition:string;sampleRate:number;retentionDays:number;preferredInput:string;playbackRate:number}
export interface DemoState {users:User[];recordings:Recording[];jobs:ProcessingJob[];results:SeparationResult[];assignments:Assignment[];reviews:Review[];notifications:Notification[];audit:AuditEvent[];preferences:Record<string,UserPreferences>;drafts:Record<string,Record<string,string>>;system:{maxUploadMB:number;retentionDays:number;maintenance:boolean;fusion:string}}
