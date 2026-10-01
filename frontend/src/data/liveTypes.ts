export type LiveRole = 'healthcare_staff' | 'audio_analyst' | 'admin';
export type LiveStatus = 'active' | 'suspended' | 'disabled';
export interface LiveUser {id:string;uid:string;email:string;display_name:string;role:LiveRole;status:LiveStatus;email_verified:boolean;public_id?:string;handle?:string;handle_change_count?:number;handle_changed_at?:number|null}
export interface SessionEnvelope {user:LiveUser;mode:'live';capabilities:{recordings:boolean;sharing:boolean;reviews:boolean;admin:boolean;ensemble:boolean;separation?:boolean}}
export interface MediaResource {id:string;public_id?:string;kind:string;media_type:string|null;url:string|null}
export interface LiveRecording {id:string;public_id?:string;owner_id:string;title:string;original_filename:string|null;created_at:number;duration_sec:number;sample_rate_hz:number;channels:number;file_size_bytes:number;original_resource_id:string|null;resources:MediaResource[];is_owner:boolean}
export interface LiveJob {id:string;public_id?:string;recording_id:string;requester_id:string;status:string;created_at:number;started_at:number|null;completed_at:number|null;error_code:string|null;result_id:string|null}
export interface LiveResult {id:string;public_id?:string;recording_id:string;job_id:string;created_at:number;method_label:string;resources:MediaResource[];is_owner:boolean;provenance?:{sample_rate:number;output_samples:number;runtime_seconds:number;model_version:string}|null}
export interface SharingRecipient {display_name:string;handle:string;public_id:string}
export interface LiveGrant {id:string;public_id?:string;assignment_public_id?:string|null;recording_id:string;resource_id:string|null;grantor_id:string;recipient_id:string;recipient?:SharingRecipient;permission:'read'|'review';status:'active'|'revoked';expires_at:number|null;created_at:number;revoked_at:number|null}
export interface LiveAssignment extends LiveGrant {recording_title?:string|null;recording_public_id?:string;resource_kind?:string;review_decision?:LiveReview['decision'];review_updated_at?:number|null}
export interface LiveReview {assignment_id:string;assignment_public_id?:string;resource_id:string;resource_kind?:string;recording_title?:string|null;recording_public_id?:string;reviewer_id:string;decision:'pending'|'accepted'|'needs_attention';notes:string;updated_at:number|null}
export interface LiveAudit {id:string;actor_id:string;action:string;target_id:string;created_at:number}
export type LivePreferences = Record<string,Record<string,unknown>>;
export const liveRoleLabel = (role:LiveRole) => ({healthcare_staff:'Healthcare Staff',audio_analyst:'Audio Analyst',admin:'Administrator'}[role]);

export function validateSession(value: SessionEnvelope): SessionEnvelope {
  if (value?.mode !== 'live' || !value.user?.id || !value.user.uid ||
      !['healthcare_staff','audio_analyst','admin'].includes(value.user.role) ||
      !['active','suspended','disabled'].includes(value.user.status) ||
      typeof value.user.email_verified !== 'boolean' || !value.capabilities) throw new Error('The application returned an invalid account response.');
  return value;
}
