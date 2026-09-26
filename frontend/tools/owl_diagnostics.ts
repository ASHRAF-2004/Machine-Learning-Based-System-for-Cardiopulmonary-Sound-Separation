import type {Plugin} from 'vite';
/** Local development-only, bounded capability/error diagnostics. No account data. */
export function owlDiagnostics():Plugin{
 const records:unknown[]=[];
 return {name:'owl-local-diagnostics',apply:'serve',configureServer(server){
  server.middlewares.use('/__owl_diagnostics',(req,res)=>{
   res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
   if(req.method==='GET'){res.end(JSON.stringify(records));return;}
   if(req.method!=='POST'){res.statusCode=405;res.end();return;}
   let body='';req.on('data',chunk=>{body+=chunk;if(body.length>4096)req.destroy();});
   req.on('end',()=>{try{records.push({time:Date.now(),data:JSON.parse(body)});if(records.length>30)records.shift();res.end('{}');}catch{res.statusCode=400;res.end('{}');}});
  });
 }};
}
