// Explicit one-time LOCAL manual-review setup. Never imported by product code.
// Ordinary grant policy is reused; existing owner review choices are not re-granted.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const review=path.join(root,'.local/shared-review'),receipt=path.join(review,'manual-assignments.json');
const state=JSON.parse(await readFile(path.join(review,'session.json'),'utf8'));
assert.equal(state.status,'ready');assert.equal(state.url,'http://127.0.0.1:4199');
assert.equal(state.api,'http://127.0.0.1:8199');assert.equal(state.database,path.join(review,'data/review.sqlite3'));
let previous;
try{previous=JSON.parse(await readFile(receipt,'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}
if(previous){console.log('Manual assignments already prepared. Existing notes/revocations are preserved; no grants created.');process.exit(0);}
async function api(route,uid='alice',body){const response=await fetch(state.api+'/api'+route,{method:body?'POST':'GET',headers:{Authorization:'Bearer M1-MOCK:'+uid,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store'});assert(response.ok,`Local request failed: ${response.status}`);return response.json();}
const person=(await api('/auth/me','analyst')).user;assert.equal(person.role,'audio_analyst');
const result=(await api('/results')).items.find(item=>item.is_owner&&item.provenance?.input_artifact_sha256==='8e0efd28aaf89f7efbd8107805a74bd837bcc70ea3dc4b4b783eff0e6a220616');assert(result);
const recording=await api('/recordings/'+result.recording_id);assert(recording.is_owner&&recording.original_resource_id);
const existing=(await api('/recordings/'+recording.id+'/grants')).items;
const items=[];
for(const [scope,resource] of [['Original audio only',recording.original_resource_id],['Result details only',result.id]]){
  const matching=existing.find(item=>item.recipient_id===person.id&&item.resource_id===resource&&item.permission==='review'&&item.status==='active'&&(item.expires_at==null||item.expires_at>Date.now()/1000));
  const grant=matching||await api('/recordings/'+recording.id+'/grants','alice',{recipient_handle:person.handle,recipient_public_id:person.public_id,permission:'review',resource_id:resource});
  items.push({scope,assignmentId:grant.id,assignmentPublicId:grant.assignment_public_id,resourceId:resource});
}
await writeFile(receipt,JSON.stringify({status:'ready',purpose:'Owner manual review, isolated fictional identities and real existing raw non-test HLS artifacts',recordingId:recording.id,recordingReference:recording.public_id,analystHandle:person.handle,createdAt:new Date().toISOString(),items},null,2)+'\n',{flag:'wx',mode:0o600});
console.log(`LOCAL manual review ready: @${person.handle}; Original and result-details assignments. No Heart/Lung grant, model execution or source changes.`);
