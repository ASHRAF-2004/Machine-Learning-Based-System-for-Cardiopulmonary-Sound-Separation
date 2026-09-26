import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import {owlDiagnostics} from './tools/owl_diagnostics.ts';
export default defineConfig({plugins:[react(),owlDiagnostics()],build:{chunkSizeWarningLimit:600},server:{host:'127.0.0.1',port:4180,strictPort:true}});
