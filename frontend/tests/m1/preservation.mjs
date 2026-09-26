import assert from 'node:assert/strict';
import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../../..');
const output=path.resolve(process.env.EVIDENCE_ROOT||'output/playwright/m1/preservation');
try{await access(output);throw new Error('Refusing to overwrite evidence.');}catch(error){if(error.code!=='ENOENT')throw error;}
await mkdir(output,{recursive:true});
const baseline='c681839';
const files=execFileSync('git',['ls-tree','-r','--name-only',baseline,'frontend/src','frontend/public/assets'],{cwd:root,encoding:'utf8'}).trim().split('\n').filter(file=>file.startsWith('frontend/public/assets/')||file.endsWith('.css')||/\/components\/(Owl|owl[^/]*|AuthScenery|WinterArt|ReferenceArt)\.(tsx|ts)$/.test(file));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const rows=[];
for(const file of files){const expected=hash(execFileSync('git',['show',`${baseline}:${file}`],{cwd:root,maxBuffer:30*1024*1024}));const actual=hash(await readFile(path.join(root,file)));rows.push({file,expected,actual,matches:expected===actual});}
await writeFile(path.join(output,'results.json'),JSON.stringify({baseline,scope:'All tracked public assets, CSS and approved owl/scenery/rendering source compared byte-for-byte against the pre-M1 checkpoint.',checked:rows.length,mismatches:rows.filter(r=>!r.matches),rows,testedAt:new Date().toISOString()},null,2));
assert(rows.length>20);assert(rows.every(r=>r.matches));console.log(`PASS ${rows.length} protected source/assets unchanged from ${baseline}`);
