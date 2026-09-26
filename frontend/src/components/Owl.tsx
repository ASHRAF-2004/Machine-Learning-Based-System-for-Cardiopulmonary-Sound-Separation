import {useEffect,useRef} from 'react';
import {useApp} from '../data/store';
import {createOwlSurface,type Surface} from './owlSurface';

type Sample={time:number;yaw:number;pitch:number;targetYaw:number;targetPitch:number;drawMs:number};
type DebugElement=HTMLDivElement&{owlSamples?:Sample[];owlInfo?:Record<string,unknown>};

/** Pointer controller is independent of the continuous local image surface. */
export default function Owl({className='',staticOnly=false}:{className?:string;staticOnly?:boolean}){
 const wrap=useRef<DebugElement>(null),canvas=useRef<HTMLCanvasElement>(null),readout=useRef<HTMLOutputElement>(null);
 const {preferences}=useApp();
 const showDebug=import.meta.env.DEV&&new URLSearchParams(location.search).has('owlDebug');
 useEffect(()=>{
  const element=wrap.current,layer=canvas.current;if(!element||!layer||staticOnly)return;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),fine=matchMedia('(pointer: fine)');
  const diagnostic=(state:string,detail?:unknown)=>{if(import.meta.env.DEV&&showDebug)void fetch('/__owl_diagnostics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state,detail,fine:fine.matches,reduced:reduced.matches,preference:preferences.reducedMotion,userAgent:navigator.userAgent})}).catch(()=>{});};
  diagnostic('controller-init');
  if(preferences.reducedMotion||!fine.matches)return;
  const connection=(navigator as Navigator&{connection?:{saveData?:boolean}}).connection;if(connection?.saveData)return;
  const hero=element.closest('.winter-hero')||element.closest('.auth-art')||element.parentElement!;
  const abort=new AbortController();let surface:Surface|null=null,disposed=false,visible=false,started=false,graphicsLost=false,frame=0,last=0;
  let bounds=element.getBoundingClientRect(),heroBounds=hero.getBoundingClientRect();
  let yaw=0,pitch=0,targetYaw=0,targetPitch=0,drawCount=0;
  let pointer:{x:number;y:number}|null=null,pointerDiagnosed=false;
  // The reference point belongs to the unchanged layout, never the moving mesh.
  const retarget=()=>{
   if(!pointer)return;
   if(pointer.x<heroBounds.left||pointer.x>heroBounds.right||pointer.y<heroBounds.top||pointer.y>heroBounds.bottom){targetYaw=0;targetPitch=0;return;}
   const cx=bounds.left+bounds.width*497.5/1163,cy=bounds.top+bounds.height*260/1353;
   let x=(pointer.x-cx)/Math.max(155,heroBounds.width*.34),y=(cy-pointer.y)/Math.max(115,heroBounds.height*.34);
   const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}
   targetYaw=x*30;targetPitch=y*18;
  };
  const samples:Sample[]=[];if(import.meta.env.DEV)element.owlSamples=samples;
  const fallback=()=>{layer.classList.remove('ready');element.classList.remove('has-frames');};
  const draw=(time:number)=>{if(!surface)return;const before=performance.now();surface.draw(yaw,pitch);drawCount++;element.dataset.yaw=yaw.toFixed(4);element.dataset.pitch=pitch.toFixed(4);element.dataset.targetYaw=targetYaw.toFixed(4);element.dataset.targetPitch=targetPitch.toFixed(4);element.dataset.drawCount=String(drawCount);element.dataset.renderer='continuous-surface';layer.classList.add('ready');element.classList.add('has-frames');if(import.meta.env.DEV){samples.push({time,yaw,pitch,targetYaw,targetPitch,drawMs:performance.now()-before});if(samples.length>8000)samples.splice(0,1000);}if(showDebug&&readout.current)readout.current.textContent=`target  ${targetYaw.toFixed(2)}° / ${targetPitch.toFixed(2)}°\nhead    ${yaw.toFixed(2)}° / ${pitch.toFixed(2)}°\nrendered ${drawCount} draws · no frame grid`;};
  const resize=()=>{bounds=element.getBoundingClientRect();heroBounds=hero.getBoundingClientRect();retarget();const width=Math.min(1163,Math.max(1,Math.round(bounds.width*Math.min(devicePixelRatio,2))));if(layer.width!==width){layer.width=width;layer.height=Math.round(width*1353/1163);surface?.resize();}wake();};
  const wake=()=>{if(!frame&&surface&&visible&&!document.hidden&&!disposed&&!reduced.matches)frame=requestAnimationFrame(tick);};
  function tick(time:number){frame=0;if(!visible||document.hidden||disposed||reduced.matches)return;const dt=last?Math.min(.05,(time-last)/1000):1/60;last=time;const gain=-Math.expm1(-dt*13);yaw+=(targetYaw-yaw)*gain;pitch+=(targetPitch-pitch)*gain;const moving=Math.abs(yaw-targetYaw)+Math.abs(pitch-targetPitch)>.001;if(!moving){yaw=targetYaw;pitch=targetPitch;}draw(time);if(moving)wake();}
  const start=async()=>{if(started||disposed||reduced.matches)return;started=true;element.dataset.loading='true';try{const ready=await createOwlSurface(layer,abort.signal);if(disposed||graphicsLost){ready.dispose();return;}surface=ready;diagnostic('ready',ready.info);if(import.meta.env.DEV)element.owlInfo=ready.info;element.dataset.sourceViews=String(ready.info.sourceViews);element.dataset.renderMode=String(ready.info.renderer).startsWith('Canvas2D')?'canvas2d':'webgl2';element.dataset.loading='false';resize();wake();}catch(error){if(disposed||graphicsLost)return;diagnostic('fallback',String(error));element.dataset.fallback='surface-unavailable';element.dataset.loading='false';fallback();console.warn('Owl uses its static fallback.',error);}};
  const move=(event:Event)=>{const e=event as PointerEvent;if(e.pointerType==='touch'||!visible)return;pointer={x:e.clientX,y:e.clientY};retarget();if(!pointerDiagnosed){diagnostic('pointer-received',{targetYaw,targetPitch});pointerDiagnosed=true;}last=frame?last:0;wake();};
  const leave=()=>{pointer=null;targetYaw=0;targetPitch=0;last=frame?last:0;wake();};
  const visibility=()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;last=0;}else{resize();wake();}};
  const motion=()=>{if(reduced.matches){cancelAnimationFrame(frame);frame=0;fallback();}else{last=0;void start();wake();}};
  const lost=(e:Event)=>{e.preventDefault();graphicsLost=true;abort.abort();cancelAnimationFrame(frame);frame=0;surface?.dispose();surface=null;element.dataset.fallback='graphics-context-lost';fallback();};
  const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible){resize();void start();wake();}else{cancelAnimationFrame(frame);frame=0;last=0;targetYaw=0;targetPitch=0;}},{threshold:.08});observer.observe(element);
  const resizer=new ResizeObserver(resize);resizer.observe(element);
  hero.addEventListener('pointermove',move,{passive:true});hero.addEventListener('pointerleave',leave);window.addEventListener('blur',leave);window.addEventListener('resize',resize);window.addEventListener('scroll',resize,{passive:true});document.addEventListener('visibilitychange',visibility);reduced.addEventListener('change',motion);layer.addEventListener('webglcontextlost',lost);
  return()=>{disposed=true;abort.abort();cancelAnimationFrame(frame);surface?.dispose();observer.disconnect();resizer.disconnect();hero.removeEventListener('pointermove',move);hero.removeEventListener('pointerleave',leave);window.removeEventListener('blur',leave);window.removeEventListener('resize',resize);window.removeEventListener('scroll',resize);document.removeEventListener('visibilitychange',visibility);reduced.removeEventListener('change',motion);layer.removeEventListener('webglcontextlost',lost);fallback();};
 },[staticOnly,preferences.reducedMotion,showDebug]);
 return <div ref={wrap} className={`owl-art ${className}`} aria-hidden="true"><img src="/assets/owl-poster-720.webp" srcSet="/assets/owl-poster-420.webp 420w, /assets/owl-poster-720.webp 720w, /assets/owl-poster-1163.webp 1163w" sizes="(max-width: 600px) 300px, (max-width:900px) 45vw, 580px" alt="" width="1163" height="1353" fetchPriority="high" decoding="async"/><canvas ref={canvas} width="1163" height="1353"/>{showDebug&&<output ref={readout} className="owl-debug-readout"/>}</div>;
}
