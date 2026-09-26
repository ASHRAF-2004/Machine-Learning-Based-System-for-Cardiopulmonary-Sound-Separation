import assert from 'node:assert/strict';
import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';

// Run the existing assertions unchanged; redirect their historical output path.
const sourceUrl=new URL('./admin.mjs',import.meta.url);
const source=await readFile(sourceUrl,'utf8');
const originalOutput="const output=path.resolve('evidence/winter-glass/admin');";
const originalImport="from 'playwright-core'";
assert.equal(source.split(originalOutput).length,2,'Admin output declaration changed; inspect before running.');
assert.equal(source.split(originalImport).length,2,'Playwright import changed; inspect before running.');
const output=path.resolve(process.env.EVIDENCE_ROOT||'evidence/reference-match/functional','admin');
try{await access(output);throw new Error(`Refusing to overwrite existing admin evidence: ${output}`);}catch(error){if(error.code!=='ENOENT')throw error;}
await mkdir(output,{recursive:true});
const executable=source.replace(originalOutput,`const output=${JSON.stringify(output)};`).replace(originalImport,`from ${JSON.stringify(import.meta.resolve('playwright-core'))}`);
await writeFile(path.join(output,'wrapper-provenance.json'),JSON.stringify({
 source:sourceUrl.pathname,sourceSha256:createHash('sha256').update(source).digest('hex'),
 output,changes:['Evidence output declaration only','Resolve unchanged Playwright import for data-URL execution'],
 assertions:'All assertions and actions are the unchanged existing tests/admin.mjs source',
},null,2));
await import(`data:text/javascript;base64,${Buffer.from(executable).toString('base64')}`);
