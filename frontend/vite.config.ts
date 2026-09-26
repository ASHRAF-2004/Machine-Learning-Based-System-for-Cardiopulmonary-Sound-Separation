import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import {owlDiagnostics} from './tools/owl_diagnostics.ts';
export default defineConfig(({mode})=>{
 const env=loadEnv(mode,process.cwd(),'');
 const target=env.STETHOFUSE_API_PROXY||'http://127.0.0.1:8000';
 if(!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(target))throw new Error('Development API proxy must be an explicit loopback HTTP port.');
 return {plugins:[react(),owlDiagnostics()],build:{chunkSizeWarningLimit:600},server:{host:'127.0.0.1',port:4180,strictPort:true,proxy:{'/api':{target,changeOrigin:false}}}};
});
