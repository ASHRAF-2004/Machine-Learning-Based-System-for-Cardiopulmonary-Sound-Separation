import type {Surface} from './owlSurface';

type Binary={file:string;bytes:number;decodedBytes:number};
type View={id:number;name:string;yaw:number;pitch:number;texture:string;bytes:number};
type Edge=Binary&{from:number;to:number};
type Manifest={version:number;width:number;height:number;views:View[];edges:Edge[];triangles:number[][];meshes:{id:number;vertexCount:number;indexCount:number;positions:Binary;indices:Binary}[];fixedBodyBoundary?:number[][];bodyTexture?:string;fixedBodyBlendWidth?:number};
type Texture={pixels:Uint8ClampedArray};
type Mesh={positions:Float32Array;indices:Uint32Array;destination:Float32Array};

/** The same v5 piecewise-affine surface as WebGL, rasterized into Canvas2D.
 * Half-open scanlines share triangle edges exactly: clipped drawImage calls
 * would leave antialiased cracks, especially across the eyes and feathers.
 * Textures, correspondences, raster buffers, and the fixed neck are cached.
 */
export async function createOwlCanvasSurface(canvas:HTMLCanvasElement,signal:AbortSignal,base=import.meta.env.DEV&&new URLSearchParams(location.search).has('owlCandidate')?'/assets/owl/diagonal-candidate/':'/assets/owl/smooth-field/'):Promise<Surface>{
 const context=canvas.getContext('2d',{alpha:true});
 if(!context)throw new Error('Canvas2D unavailable');
 const internalAbort=new AbortController(),loadSignal=AbortSignal.any([signal,internalAbort.signal]);
 const textures=new Map<number,Texture>(),meshes=new Map<number,Mesh>(),flows=new Map<string,Float32Array>();
 const scratch=document.createElement('canvas'),scratchContext=scratch.getContext('2d',{alpha:true})!;
 let body:ImageBitmap|undefined,disposed=false;
 const dispose=()=>{if(disposed)return;disposed=true;internalAbort.abort();body?.close();textures.clear();meshes.clear();flows.clear();scratch.width=scratch.height=1;};
 const fetchChecked=async(url:string)=>{const r=await fetch(url,{signal:loadSignal});if(!r.ok)throw new Error(`Owl asset unavailable: ${r.status}`);return r;};
 const checkAbort=()=>{if(loadSignal.aborted)throw new DOMException('Aborted','AbortError');};
 try{
  const manifest:Manifest=await(await fetchChecked(base+'manifest.json')).json();
  if(manifest.version!==5||!Array.isArray(manifest.meshes)||manifest.width!==1163||!Number.isInteger(manifest.height)||manifest.height<600||manifest.height>1000)throw new Error('Unsupported owl surface');
  const width=manifest.width,height=manifest.height,totalHeight=1353,blendWidth=manifest.fixedBodyBlendWidth??12;
  if(!Number.isFinite(blendWidth)||blendWidth<1||blendWidth>height)throw new Error('Invalid owl body blend width');
  if(manifest.bodyTexture!==undefined&&typeof manifest.bodyTexture!=='string')throw new Error('Invalid owl body texture');
  const loadImage=async(url:string)=>{const image=await createImageBitmap(await(await fetchChecked(url)).blob(),{premultiplyAlpha:'premultiply',colorSpaceConversion:'none'});if(loadSignal.aborted){image.close();checkAbort();}return image;};
  const loadBinary=async(entry:Binary)=>{
   let bytes=await(await fetchChecked(base+entry.file)).arrayBuffer();
   const header=new Uint8Array(bytes,0,Math.min(3,bytes.byteLength));
   if(header[0]===31&&header[1]===139&&header[2]===8)bytes=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   if(entry.decodedBytes&&entry.decodedBytes!==bytes.byteLength)throw new Error('Invalid owl correspondence data');
   checkAbort();return bytes;
  };
  const jobs=[async()=>{body=await loadImage(manifest.bodyTexture||'/assets/owl/body.webp');},...manifest.views.map(view=>async()=>{
   const image=await loadImage(base+view.texture);
   const decode=document.createElement('canvas');decode.width=width;decode.height=height;
   const decodeContext=decode.getContext('2d',{willReadFrequently:true})!;let pixels:Uint8ClampedArray;
   try{decodeContext.drawImage(image,0,0);pixels=decodeContext.getImageData(0,0,width,height).data;}finally{image.close();decode.width=decode.height=1;}
   // Interpolate premultiplied colors, like the WebGL texture and framebuffer.
   for(let i=0;i<pixels.length;i+=4){const alpha=pixels[i+3]/255;pixels[i]*=alpha;pixels[i+1]*=alpha;pixels[i+2]*=alpha;}
   textures.set(view.id,{pixels});
  }),...manifest.edges.map(edge=>async()=>{flows.set(`${edge.from}-${edge.to}`,new Float32Array(await loadBinary(edge)));}),...manifest.meshes.map(mesh=>async()=>{
   const positions=new Float32Array(await loadBinary(mesh.positions)),indices=new Uint32Array(await loadBinary(mesh.indices));
   if(positions.length!==mesh.vertexCount*2||indices.length!==mesh.indexCount)throw new Error('Invalid owl mesh');
   meshes.set(mesh.id,{positions,indices,destination:new Float32Array(positions.length)});
  })];
  let next=0;await Promise.all(Array.from({length:4},async()=>{while(next<jobs.length){checkAbort();await jobs[next++]();}}));checkAbort();
  for(const ids of manifest.triangles)for(const id of ids){const mesh=meshes.get(id);if(!mesh||!textures.has(id)||ids.some(other=>other!==id&&flows.get(`${id}-${other}`)?.length!==mesh.positions.length))throw new Error('Incomplete owl surface');}
  // A summed-area alpha table rejects only entirely transparent triangles.
  // Padding includes every texel bilinear filtering can touch.
  const originalTriangles=[...meshes].map(([id,mesh])=>({id,triangles:mesh.indices.length/3}));
  for(const [id,mesh] of meshes){
   const pixels=textures.get(id)!.pixels,stride=width+1,alpha=new Uint32Array(stride*(height+1));
   for(let y=0;y<height;y++){let row=0;for(let x=0;x<width;x++){row+=pixels[(y*width+x)*4+3]>0?1:0;alpha[(y+1)*stride+x+1]=alpha[y*stride+x+1]+row;}}
   const active:number[]=[],p=mesh.positions;
   for(let t=0;t<mesh.indices.length;t+=3){
    const a=mesh.indices[t]*2,b=mesh.indices[t+1]*2,c=mesh.indices[t+2]*2;
    const left=Math.max(0,Math.floor(Math.min(p[a],p[b],p[c]))-1),right=Math.min(width,Math.ceil(Math.max(p[a],p[b],p[c]))+2);
    const top=Math.max(0,Math.floor(Math.min(p[a+1],p[b+1],p[c+1]))-1),bottom=Math.min(height,Math.ceil(Math.max(p[a+1],p[b+1],p[c+1]))+2);
    if(right>left&&bottom>top&&alpha[bottom*stride+right]-alpha[top*stride+right]-alpha[bottom*stride+left]+alpha[top*stride+left]>0)active.push(a,b,c);
   }
   // Indices become offsets into the interleaved vec2 arrays after culling.
   mesh.indices=new Uint32Array(active);
  }
  const info:Record<string,unknown>={renderer:'Canvas2D software surface',fieldVersion:manifest.version,sourceViews:manifest.views.length,maxHeadRasterWidth:590,sourceTextureBytes:manifest.views.length*width*height*4,compressedBytes:manifest.views.reduce((s,v)=>s+v.bytes,0)+manifest.edges.reduce((s,e)=>s+e.bytes,0)+manifest.meshes.reduce((s,m)=>s+m.positions.bytes+m.indices.bytes,0),flowBufferBytes:manifest.edges.reduce((s,e)=>s+e.decodedBytes,0),meshBufferBytes:manifest.meshes.reduce((s,m)=>s+m.positions.decodedBytes+m.indices.decodedBytes,0),trianglesPerView:originalTriangles,rasterizedTrianglesPerView:[...meshes].map(([id,m])=>({id,triangles:m.indices.length/3})),quality:'Head raster capped at 590 pixels wide; body uses full canvas resolution'};
  let fw=0,fh=0,output:ImageData,accumulation=new Float32Array(0),fixed=new Float32Array(0),moving=new Float32Array(0);
  const boundary=manifest.fixedBodyBoundary||[[0,height],[width,height]];
  const sample=(pixels:Uint8ClampedArray,x:number,y:number,target:Float32Array,offset:number,weight:number)=>{
   x=Math.max(0,Math.min(width-1,x));y=Math.max(0,Math.min(height-1,y));
   const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy,a=(iy*width+ix)*4,b=ix<width-1?a+4:a,c=iy<height-1?a+width*4:a,d=c+b-a;
   for(let channel=0;channel<4;channel++)target[offset+channel]=(pixels[a+channel]*(1-fx)*(1-fy)+pixels[b+channel]*fx*(1-fy)+pixels[c+channel]*(1-fx)*fy+pixels[d+channel]*fx*fy)*weight;
  };
  const resize=()=>{
   const nextWidth=Math.max(1,Math.min(590,canvas.width));if(nextWidth===fw)return;
   fw=nextWidth;fh=Math.ceil(fw*height/width);scratch.width=fw;scratch.height=fh;
   output=scratchContext.createImageData(fw,fh);accumulation=new Float32Array(fw*fh*4);fixed=new Float32Array(fw*fh*4);moving=new Float32Array(fw*fh);
   const neutral=textures.get(0)!.pixels;
   for(let x=0;x<fw;x++){
    const sourceX=(x+.5)*width/fw;let edge=height;
    for(let i=0;i<boundary.length-1;i++)if(sourceX>=boundary[i][0]&&sourceX<=boundary[i+1][0]){const t=(sourceX-boundary[i][0])/Math.max(.001,boundary[i+1][0]-boundary[i][0]);edge=boundary[i][1]+(boundary[i+1][1]-boundary[i][1])*t;break;}
    for(let y=0;y<fh;y++){
     const sourceY=(y+.5)*height/fh,t=Math.max(0,Math.min(1,(sourceY-edge+blendWidth)/blendWidth)),blend=t*t*(3-2*t),pixel=y*fw+x;
     moving[pixel]=1-blend;if(blend)sample(neutral,sourceX-.5,sourceY-.5,fixed,pixel*4,blend);
    }
   }
   info.headRasterWidth=fw;info.headRasterHeight=fh;
  };
  const contributors=(yaw:number,pitch:number)=>{
   for(const ids of manifest.triangles){const [a,b,c]=ids.map(id=>manifest.views[id]);const det=(b.pitch-c.pitch)*(a.yaw-c.yaw)+(c.yaw-b.yaw)*(a.pitch-c.pitch);const wa=((b.pitch-c.pitch)*(yaw-c.yaw)+(c.yaw-b.yaw)*(pitch-c.pitch))/det,wb=((c.pitch-a.pitch)*(yaw-c.yaw)+(a.yaw-c.yaw)*(pitch-c.pitch))/det,wc=1-wa-wb;if(Math.min(wa,wb,wc)>-1e-5)return{ids,weights:[Math.max(0,wa),Math.max(0,wb),Math.max(0,wc)]};}
   throw new Error(`Owl pose outside field: ${yaw}, ${pitch}`);
  };
  const debugLayer=import.meta.env.DEV?new URLSearchParams(location.search).get('owlLayer'):null;
  const rasterize=(mesh:Mesh,pixels:Uint8ClampedArray,flowA:Float32Array,flowB:Float32Array,amountA:number,amountB:number,weight:number)=>{
   const p=mesh.positions,destination=mesh.destination,indices=mesh.indices,scaleX=fw/width,scaleY=fh/height;
   for(let i=0;i<p.length;i+=2){destination[i]=(p[i]+flowA[i]*amountA+flowB[i]*amountB)*scaleX;destination[i+1]=(p[i+1]+flowA[i+1]*amountA+flowB[i+1]*amountB)*scaleY;}
   for(let triangle=0;triangle<indices.length;triangle+=3){
    let a=indices[triangle],b=indices[triangle+1],c=indices[triangle+2];
    if(destination[a+1]>destination[b+1]){const swap=a;a=b;b=swap;}if(destination[b+1]>destination[c+1]){const swap=b;b=c;c=swap;}if(destination[a+1]>destination[b+1]){const swap=a;a=b;b=swap;}
    const x0=destination[a],y0=destination[a+1],x1=destination[b],y1=destination[b+1],x2=destination[c],y2=destination[c+1];
    const dx1=x1-x0,dy1=y1-y0,dx2=x2-x0,dy2=y2-y0,det=dx1*dy2-dx2*dy1;
    if(Math.abs(det)<.000001)continue;
    const sx0=p[a],sy0=p[a+1],sx1=p[b]-sx0,sy1=p[b+1]-sy0,sx2=p[c]-sx0,sy2=p[c+1]-sy0;
    const ux=(sx1*dy2-sx2*dy1)/det,uy=(sx2*dx1-sx1*dx2)/det,vx=(sy1*dy2-sy2*dy1)/det,vy=(sy2*dx1-sy1*dx2)/det;
    const first=Math.max(0,Math.ceil(y0-.5)),last=Math.min(fh,Math.ceil(y2-.5)),longSlope=dx2/dy2;
    for(let y=first;y<last;y++){
     const py=y+.5,longX=x0+(py-y0)*longSlope,shortX=py<y1?x0+(py-y0)*dx1/dy1:x1+(py-y1)*(x2-x1)/(y2-y1);
     const left=Math.max(0,Math.ceil(Math.min(longX,shortX)-.5)),right=Math.min(fw,Math.ceil(Math.max(longX,shortX)-.5));
     let u=sx0+(left+.5-x0)*ux+(py-y0)*uy,v=sy0+(left+.5-x0)*vx+(py-y0)*vy,pixel=y*fw+left;
     for(let x=left;x<right;x++,pixel++,u+=ux,v+=vx){
      const blend=weight*moving[pixel];if(blend===0)continue;
      const sourceX=Math.max(0,Math.min(width-1,u-.5)),sourceY=Math.max(0,Math.min(height-1,v-.5)),ix=Math.floor(sourceX),iy=Math.floor(sourceY),fx=sourceX-ix,fy=sourceY-iy;
      const ia=(iy*width+ix)*4,ib=ix<width-1?ia+4:ia,ic=iy<height-1?ia+width*4:ia,id=ic+ib-ia,wa=(1-fx)*(1-fy)*blend,wb=fx*(1-fy)*blend,wc=(1-fx)*fy*blend,wd=fx*fy*blend,o=pixel*4;
      accumulation[o]+=pixels[ia]*wa+pixels[ib]*wb+pixels[ic]*wc+pixels[id]*wd;
      accumulation[o+1]+=pixels[ia+1]*wa+pixels[ib+1]*wb+pixels[ic+1]*wc+pixels[id+1]*wd;
      accumulation[o+2]+=pixels[ia+2]*wa+pixels[ib+2]*wb+pixels[ic+2]*wc+pixels[id+2]*wd;
      accumulation[o+3]+=pixels[ia+3]*wa+pixels[ib+3]*wb+pixels[ic+3]*wc+pixels[id+3]*wd;
     }
    }
   }
  };
  const draw=(yaw:number,pitch:number)=>{
   if(disposed)return;resize();const {ids,weights}=contributors(yaw,pitch);accumulation.set(fixed);
   for(let n=0;n<3;n++){
    const weight=debugLayer===null?weights[n]:Number(debugLayer)===n?1:0;if(weight<.00001||weights[n]<.00001)continue;
    const other=[0,1,2].filter(i=>i!==n);rasterize(meshes.get(ids[n])!,textures.get(ids[n])!.pixels,flows.get(`${ids[n]}-${ids[other[0]]}`)!,flows.get(`${ids[n]}-${ids[other[1]]}`)!,weights[other[0]],weights[other[1]],weight);
   }
   const data=output.data;
   for(let i=0;i<data.length;i+=4){const alpha=accumulation[i+3],unpremultiply=alpha>0?255/alpha:0;data[i]=accumulation[i]*unpremultiply;data[i+1]=accumulation[i+1]*unpremultiply;data[i+2]=accumulation[i+2]*unpremultiply;data[i+3]=alpha;}
   scratchContext.putImageData(output,0,0);context.clearRect(0,0,canvas.width,canvas.height);
   const headHeight=canvas.height*height/totalHeight;
   context.drawImage(body!,0,headHeight,canvas.width,canvas.height-headHeight);context.drawImage(scratch,0,0,canvas.width,headHeight);
  };
  return{draw,resize,dispose,info};
 }catch(error){dispose();throw error;}
}
