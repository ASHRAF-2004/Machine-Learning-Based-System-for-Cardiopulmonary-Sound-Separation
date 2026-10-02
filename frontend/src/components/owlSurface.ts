/** Local multi-view image surface. A new pose is drawn on every changing RAF.
 * Images and displacement meshes are decoded once, never during pointer input.
 */
type View={id:number;name:string;yaw:number;pitch:number;texture:string;bytes:number};
type Edge={from:number;to:number;file:string;bytes:number;decodedBytes:number};
type Binary={file:string;bytes:number;decodedBytes:number};
type Mesh={id:number;vertexCount:number;indexCount:number;positions:Binary;indices:Binary};
type Manifest={version:number;width:number;height:number;views:View[];edges:Edge[];triangles:number[][];meshes:Mesh[];fixedBodyBoundary?:number[][];bodyTexture?:string;fixedBodyBlendWidth?:number};
export type Surface={draw:(yaw:number,pitch:number)=>void;resize:()=>void;dispose:()=>void;info:Record<string,unknown>};
const vertex=`#version 300 es
precision highp float;
layout(location=0) in vec2 position;
layout(location=1) in vec2 flowA;
layout(location=2) in vec2 flowB;
uniform vec2 amount;
uniform vec2 sourceSize;
out vec2 uv;
void main(){vec2 p=position+flowA*amount.x+flowB*amount.y;uv=position/sourceSize;gl_Position=vec4(p.x/sourceSize.x*2.-1.,1.-p.y/sourceSize.y*2.,0.,1.);}`;
const fragment=`#version 300 es
precision highp float;
in vec2 uv;uniform sampler2D source;out vec4 color;
void main(){color=texture(source,uv);}`;
const quadVertex=`#version 300 es
precision highp float;layout(location=0) in vec2 position;out vec2 uv;
void main(){uv=position*.5+.5;gl_Position=vec4(position,0.,1.);}`;
const compositeFragment=`#version 300 es
precision highp float;in vec2 uv;out vec4 color;
uniform sampler2D a;uniform sampler2D b;uniform sampler2D c;uniform sampler2D body;uniform sampler2D neutral;uniform vec3 weight;uniform vec2 bodyEdge[14];
uniform float surfaceHeight;uniform float blendWidth;
void main(){float y=(1.-uv.y)*1353.;if(y<surfaceHeight){vec2 p=vec2(uv.x,1.-y/surfaceHeight);color=texture(a,p)*weight.x+texture(b,p)*weight.y+texture(c,p)*weight.z;float x=uv.x*1163.;float edge=surfaceHeight;for(int i=0;i<13;i++){if(x>=bodyEdge[i].x&&x<=bodyEdge[i+1].x){float t=(x-bodyEdge[i].x)/max(.001,bodyEdge[i+1].x-bodyEdge[i].x);edge=mix(bodyEdge[i].y,bodyEdge[i+1].y,t);}}color=mix(color,texture(neutral,vec2(uv.x,y/surfaceHeight)),smoothstep(edge-blendWidth,edge,y));}else{color=texture(body,vec2(uv.x,(y-surfaceHeight)/(1353.-surfaceHeight)));}}`;

function program(gl:WebGL2RenderingContext,vs:string,fs:string){
 const shaders=[gl.VERTEX_SHADER,gl.FRAGMENT_SHADER].map((type,i)=>{const s=gl.createShader(type)!;gl.shaderSource(s,i?fs:vs);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||'Owl shader failed');return s;});
 const p=gl.createProgram()!;shaders.forEach(s=>gl.attachShader(p,s));gl.linkProgram(p);shaders.forEach(s=>gl.deleteShader(s));if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||'Owl shader link failed');return p;
}

export async function createOwlSurface(canvas:HTMLCanvasElement,signal:AbortSignal):Promise<Surface>{
 // The user-approved connected-neck field is the normal experience. Older fields
 // remain available only through explicit development comparison flags.
 const params=new URLSearchParams(location.search);
 const base=import.meta.env.DEV&&params.has('owlLegacy')?'/assets/owl/smooth-field/':import.meta.env.DEV&&params.has('owlCandidate')?'/assets/owl/diagonal-candidate/':'/assets/owl/neck-candidate/';
 const forceCanvas=import.meta.env.DEV&&new URLSearchParams(location.search).has('owlCanvas');
 const gl=forceCanvas?null:canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false});
 if(!gl){const {createOwlCanvasSurface}=await import('./owlCanvasSurface');return createOwlCanvasSurface(canvas,signal,base);}
 const internalAbort=new AbortController();const loadSignal=AbortSignal.any([signal,internalAbort.signal]);
 const fetchChecked=async(url:string)=>{const r=await fetch(url,{signal:loadSignal});if(!r.ok)throw new Error(`Owl asset unavailable: ${r.status}`);return r;};
 const manifest:Manifest=await (await fetchChecked(base+'manifest.json')).json();
 if(manifest.version!==5||!Array.isArray(manifest.meshes)||manifest.width!==1163||!Number.isInteger(manifest.height)||manifest.height<600||manifest.height>1000)throw new Error('Unsupported owl surface; keeping the approved poster');
 const textures:WebGLTexture[]=[],buffers:WebGLBuffer[]=[],fbos:WebGLFramebuffer[]=[],programs:WebGLProgram[]=[];
 const buffer=(data:BufferSource,target:number=gl.ARRAY_BUFFER)=>{const b=gl.createBuffer()!;buffers.push(b);gl.bindBuffer(target,b);gl.bufferData(target,data,gl.STATIC_DRAW);return b;};
 const texture=()=>{const t=gl.createTexture()!;textures.push(t);gl.bindTexture(gl.TEXTURE_2D,t);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return t;};
 const dispose=()=>{textures.forEach(t=>gl.deleteTexture(t));buffers.forEach(b=>gl.deleteBuffer(b));fbos.forEach(f=>gl.deleteFramebuffer(f));programs.forEach(p=>gl.deleteProgram(p));};
 try{
  const loadTexture=async(url:string)=>{const blob=await(await fetchChecked(url)).blob();const image=await createImageBitmap(blob,{premultiplyAlpha:'premultiply',colorSpaceConversion:'none'});if(loadSignal.aborted){image.close();throw new DOMException('Aborted','AbortError');}const t=texture();gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);image.close();return t;};
  const loadedViews:WebGLTexture[]=new Array(manifest.views.length);
  // Small fixed set of source views, not thousands of independently loaded frames.
  let body:WebGLTexture;
  const jobs=[async()=>{body=await loadTexture(manifest.bodyTexture||'/assets/owl/body.webp');},...manifest.views.map(v=>async()=>{loadedViews[v.id]=await loadTexture(base+v.texture);})];
  const flows=new Map<string,WebGLBuffer>();
  const loadBinary=async(e:Binary)=>{
   const response=await fetchChecked(base+e.file);let bytes=await response.arrayBuffer();
   // Vite serves .gz with Content-Encoding, so fetch already decompresses it.
   // A plain file server may not. Detect the payload instead of decoding twice.
   const header=new Uint8Array(bytes,0,Math.min(3,bytes.byteLength));
   if(header[0]===31&&header[1]===139&&header[2]===8)bytes=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   if(e.decodedBytes&&bytes.byteLength!==e.decodedBytes)throw new Error('Invalid owl correspondence data');
   if(loadSignal.aborted)throw new DOMException('Aborted','AbortError');return bytes;
  };
  jobs.push(...manifest.edges.map(e=>async()=>{flows.set(`${e.from}-${e.to}`,buffer(await loadBinary(e)));}));
  const meshes=new Map<number,{positions:WebGLBuffer;indices:WebGLBuffer;count:number;vertices:number}>();
  jobs.push(...(manifest.meshes||[]).map(m=>async()=>{
   const positions=buffer(await loadBinary(m.positions));const indices=buffer(await loadBinary(m.indices),gl.ELEMENT_ARRAY_BUFFER);
   meshes.set(m.id,{positions,indices,count:m.indexCount,vertices:m.vertexCount});
  }));
  let next=0;await Promise.all(Array.from({length:4},async()=>{while(next<jobs.length)await jobs[next++]();}));
  if(gl.isContextLost()||loadSignal.aborted)throw new Error('Owl graphics initialization was interrupted');
  for(const ids of manifest.triangles)for(const id of ids){
   if(!meshes.has(id)||ids.some(other=>other!==id&&!flows.has(`${id}-${other}`)))throw new Error('Incomplete owl surface');
  }
  const quad=buffer(new Float32Array([-1,-1,1,-1,-1,1,1,1]));
  const warp=program(gl,vertex,fragment),compose=program(gl,quadVertex,compositeFragment);programs.push(warp,compose);
  gl.useProgram(warp);gl.uniform2f(gl.getUniformLocation(warp,'sourceSize'),manifest.width,manifest.height);
  gl.useProgram(compose);gl.uniform1f(gl.getUniformLocation(compose,'surfaceHeight'),manifest.height);gl.uniform1f(gl.getUniformLocation(compose,'blendWidth'),manifest.fixedBodyBlendWidth??12);
  const amount=gl.getUniformLocation(warp,'amount'),source=gl.getUniformLocation(warp,'source'),weight=gl.getUniformLocation(compose,'weight');
  const sourceTextures=[texture(),texture(),texture()];let fw=0,fh=0;
  for(const t of sourceTextures){const f=gl.createFramebuffer()!;fbos.push(f);gl.bindFramebuffer(gl.FRAMEBUFFER,f);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,t,0);}
  const resize=()=>{if(fw===canvas.width)return;fw=canvas.width;fh=Math.ceil(fw*manifest.height/manifest.width);for(const t of sourceTextures){gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,fw,fh,0,gl.RGBA,gl.UNSIGNED_BYTE,null);}};
  const setAttribute=(location:number,b:WebGLBuffer,type:number)=>{gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,2,type,false,0,0);};
  const contributors=(yaw:number,pitch:number):{ids:number[];weights:number[]}=>{
   for(const ids of manifest.triangles){const [a,b,c]=ids.map(id=>manifest.views[id]);const det=(b.pitch-c.pitch)*(a.yaw-c.yaw)+(c.yaw-b.yaw)*(a.pitch-c.pitch);const wa=((b.pitch-c.pitch)*(yaw-c.yaw)+(c.yaw-b.yaw)*(pitch-c.pitch))/det;const wb=((c.pitch-a.pitch)*(yaw-c.yaw)+(a.yaw-c.yaw)*(pitch-c.pitch))/det;const wc=1-wa-wb;if(Math.min(wa,wb,wc)>-1e-5)return{ids,weights:[Math.max(0,wa),Math.max(0,wb),Math.max(0,wc)]};}
   throw new Error(`Owl pose outside field: ${yaw}, ${pitch}`);
  };
  const draw=(yaw:number,pitch:number)=>{
   resize();const {ids,weights}=contributors(yaw,pitch);
   gl.disable(gl.BLEND);gl.disable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);gl.useProgram(warp);gl.uniform1i(source,0);gl.viewport(0,0,fw,fh);
   for(let n=0;n<3;n++){
    gl.bindFramebuffer(gl.FRAMEBUFFER,fbos[n]);gl.clear(gl.COLOR_BUFFER_BIT);if(weights[n]<.00001)continue;
    const other=[0,1,2].filter(i=>i!==n),mesh=meshes.get(ids[n])!;
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,mesh.indices);setAttribute(0,mesh.positions,gl.FLOAT);setAttribute(1,flows.get(`${ids[n]}-${ids[other[0]]}`)!,gl.FLOAT);setAttribute(2,flows.get(`${ids[n]}-${ids[other[1]]}`)!,gl.FLOAT);gl.uniform2f(amount,weights[other[0]],weights[other[1]]);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,loadedViews[ids[n]]);gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_INT,0);
   }
   gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(compose);setAttribute(0,quad,gl.FLOAT);gl.disableVertexAttribArray(1);gl.disableVertexAttribArray(2);
   [...sourceTextures,body,loadedViews[0]].forEach((t,i)=>{gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,t);gl.uniform1i(gl.getUniformLocation(compose,['a','b','c','body','neutral'][i]),i);});
   gl.uniform2fv(gl.getUniformLocation(compose,'bodyEdge'),(manifest.fixedBodyBoundary||Array.from({length:14},(_,i)=>[i/13*1163,manifest.height])).flat());
   const debugLayer=import.meta.env.DEV?new URLSearchParams(location.search).get('owlLayer'):null;
   gl.uniform3fv(weight,debugLayer===null?weights:[0,1,2].map(i=>i===Number(debugLayer)?1:0));gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
  };
  const extension=gl.getExtension('WEBGL_debug_renderer_info');
  return {draw,resize,dispose,info:{renderer:extension?gl.getParameter(extension.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),fieldVersion:manifest.version,sourceViews:manifest.views.length,surfaceHeight:manifest.height,compressedBytes:manifest.views.reduce((s,v)=>s+v.bytes,0)+manifest.edges.reduce((s,e)=>s+e.bytes,0)+(manifest.meshes||[]).reduce((s,m)=>s+m.positions.bytes+m.indices.bytes,0),sourceTextureBytes:manifest.views.length*manifest.width*manifest.height*4,flowBufferBytes:manifest.edges.reduce((s,e)=>s+(e.decodedBytes||e.bytes),0),meshBufferBytes:(manifest.meshes||[]).reduce((s,m)=>s+m.positions.decodedBytes+m.indices.decodedBytes,0),trianglesPerView:[...meshes].map(([id,m])=>({id,triangles:m.count/3}))}};
 }catch(error){internalAbort.abort();dispose();throw error;}
}
