// Run historical regression assertions with explicit mode/new evidence locations.
// No production source injection; the motion hash check excludes only the two
// source modules intentionally replaced by this authorized M1 integration.
import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
const suite=process.argv[2];
if(!['home','motion','workflows'].includes(suite))throw new Error('Choose home, motion or workflows.');
const root=path.resolve(import.meta.dirname,'../..');
const output=path.resolve(process.env.EVIDENCE_ROOT||`output/playwright/m1/${suite}`);
try{await access(output);throw new Error('Refusing to overwrite evidence.');}catch(error){if(error.code!=='ENOENT')throw error;}
await mkdir(output,{recursive:true});
process.env.EVIDENCE_ROOT=output;
process.env.FRONTEND_URL=suite==='home'?'http://127.0.0.1:4180':'http://127.0.0.1:4182';
const file={home:'home-polish.mjs',motion:'public-reference-motion.mjs',workflows:'workflows.mjs'}[suite];
let source=await readFile(path.join(root,'tests',file),'utf8');
source=source.replace("from 'playwright-core'",`from ${JSON.stringify(import.meta.resolve('playwright-core'))}`);
if(suite==='home')source=source.replace("const output = 'output/playwright/home-polish/responsive';",`const output = ${JSON.stringify(output)};`);
if(suite==='workflows')source=source.replace("const base='http://127.0.0.1:4180';","const base='http://127.0.0.1:4182';");
if(suite==='motion')source=source.replace("const root=path.resolve(import.meta.dirname,'..');",`const root=${JSON.stringify(root)};`).replace("'src/components/owlCanvasSurface.ts','src/data/adapters.ts','src/brand.ts'","'src/components/owlCanvasSurface.ts'").replace('Protected controller, adapter, brand and identity hashes match their checkpoints','Protected approved owl controller and identity assets match their checkpoints');
await writeFile(path.join(output,'invocation.json'),JSON.stringify({suite,original:file,base:process.env.FRONTEND_URL,changes:suite==='motion'?['Evidence output only','Explicit demo mode for historical disconnected remember check','Adapters and brand hashes intentionally superseded by M1; owl/art checks unchanged']:['Evidence output only',suite==='workflows'?'Explicit development demo server':'Default live fail-closed server'],testedAt:new Date().toISOString()},null,2));
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
