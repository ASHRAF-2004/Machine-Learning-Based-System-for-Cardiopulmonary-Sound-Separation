"""Build a genuine two-axis lookup from existing approved pose images.

This is local image interpolation, not a 3D reconstruction, video sprite reuse,
or new generated owl identity. It reuses the verified RIFE executable/weights.
The entire face is interpolated together. Body and rows 525+ are source-exact
before WebP encoding. Dense flow moves the transparent silhouette coherently.
"""
from pathlib import Path
from functools import lru_cache
import argparse,hashlib,json,os,subprocess,time
import cv2,numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
CONT=STUDY/'feather-continuity'
VENDOR=CONT/'vendor/rife'
EXE=VENDOR/'rife-ncnn-vulkan'
MODEL=VENDOR/'models/rife-v4.6'
CACHE=ROOT/'.cache/owl-field'
OUT=ROOT/'public/assets/owl/field'
EVIDENCE=ROOT/'evidence/owl-field'
SEQ=json.loads((CONT/'rife-exports/sequence.json').read_text())
X0,X1,Y1=128,896,544
GRID=np.stack(np.meshgrid(np.arange(X1-X0,dtype=np.float32),np.arange(Y1,dtype=np.float32)),axis=2)
BG=np.array([237,245,251],np.float32)
NEUTRAL=np.asarray(Image.open(STUDY/'assembled/neutral-original.png').convert('RGBA'))[:600].copy()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return np.asarray(Image.open(path).convert('RGBA'))[:600].copy()
def colour(im):
    a=im[:,:,3:]/255.;return im[:,:,:3]*a+BG*(1-a)
def sample(im,q):return cv2.remap(im,q[:,:,0],q[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
@lru_cache(maxsize=6)
def pair(ap,bp):
    a,b=read(Path(ap)),read(Path(bp));ar,br=colour(a)[:Y1,X0:X1],colour(b)[:Y1,X0:X1]
    ga=cv2.cvtColor(np.uint8(ar),cv2.COLOR_RGB2GRAY);gb=cv2.cvtColor(np.uint8(br),cv2.COLOR_RGB2GRAY)
    solver=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);solver.setFinestScale(0);solver.setGradientDescentIterations(25)
    forward=solver.calc(ga,gb,None);reverse=solver.calc(gb,ga,None)
    return a,b,forward,reverse
def inverse(flow,t):
    q=GRID-flow*t
    for _ in range(4):q=GRID-sample(flow,q)*t
    return q
@lru_cache(maxsize=200)
def prepared(path,scale):
    key=hashlib.sha256((str(path)+str(scale)).encode()).hexdigest()[:16]
    dst=CACHE/f'input-{key}.png'
    if not dst.exists():
        image=colour(read(Path(path)))[:Y1,X0:X1];image=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_LANCZOS4)
        Image.fromarray(np.uint8(np.clip(image,0,255))).save(dst)
    return dst
def interpolate(ap,bp,t,dest,scale=2):
    if dest.exists():return
    if t<1e-7:Image.open(ap).save(dest);return
    if t>1-1e-7:Image.open(bp).save(dest);return
    key=hashlib.sha256((str(ap)+str(bp)+str(round(t,6))+str(scale)).encode()).hexdigest()[:16]
    rawpath=CACHE/f'rgb-{key}.png'
    if not rawpath.exists():
        cmd=[str(EXE),'-0',str(prepared(str(ap),scale)),'-1',str(prepared(str(bp),scale)),'-o',str(rawpath),'-s',str(t),'-m',str(MODEL),'-g','0','-j','1:2:1','-z']
        run=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'OMP_NUM_THREADS':'2','OMP_THREAD_LIMIT':'2'})
        if run.returncode:raise RuntimeError(run.stderr[-2000:])
    raw=np.asarray(Image.open(rawpath).convert('RGB'));raw=cv2.resize(raw,(X1-X0,Y1),interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    a,b,f,r=pair(str(ap),str(bp));qa,qb=inverse(f,t),inverse(r,1-t)
    aa=sample(a[:Y1,X0:X1,3].astype(np.float32)/255,qa);ab=sample(b[:Y1,X0:X1,3].astype(np.float32)/255,qb)
    alpha=np.clip(aa*(1-t)+ab*t,0,1)
    rgb=(raw-BG[None,None,:]*(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],.015)
    result=NEUTRAL.copy();result[:Y1,X0:X1,:3]=np.uint8(np.clip(rgb,0,255));result[:Y1,X0:X1,3]=np.uint8(np.round(alpha*255))
    # Every source was already registered to this fixed body. Keep that anchorage.
    weight=np.clip((525-np.arange(600,dtype=np.float32))/32,0,1)[:,None,None]
    result=np.uint8(np.round(result.astype(np.float32)*weight+NEUTRAL*(1-weight)))
    result[525:]=NEUTRAL[525:]
    Image.fromarray(result).save(dest)
def source_pose(name):return STUDY/'assembled'/f'{name}.png'
def middle(x):
    if x==0:return source_pose('neutral-original')
    rows=SEQ['rows'][(0 if x<0 else 1)*150: (0 if x<0 else 1)*150+75]
    def yaw(row):
        def value(name):
            if name=='neutral-original':return 0
            return int(name.split('yaw-')[1].split('-pitch')[0].replace('minus','-').replace('plus',''))
        return value(row['source_a'])*(1-row['interpolation'])+value(row['source_b'])*row['interpolation']
    return CONT/min(rows,key=lambda r:abs(yaw(r)-x))['file']
def endpoint(x,sign,scale):
    pitch='plus18' if sign>0 else 'minus18'
    if x==0:return source_pose(f'yaw0-pitch-{pitch}')
    side='minus30' if x<0 else 'plus30';destination=CACHE/f'endpoint-{x:+05.1f}-{sign:+d}.png'
    interpolate(source_pose(f'yaw0-pitch-{pitch}'),source_pose(f'yaw-{side}-pitch-{pitch}'),abs(x)/30,destination,scale)
    return destination
def build(x,y,scale):
    dest=OUT/f'pose-{x+20:02d}-{y+12:02d}.webp';native=CACHE/f'pose-{x+20:02d}-{y+12:02d}.png'
    if dest.exists():return dest
    if y==0:
        im=read(middle(x*1.5));Image.fromarray(im).save(native)
    else:interpolate(middle(x*1.5),endpoint(x*1.5,1 if y>0 else -1,scale),abs(y)/12,native,scale)
    Image.open(native).save(dest,'WEBP',quality=94,method=6,exact=True)
    return dest
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true');parser.add_argument('--scale',type=int,default=2);args=parser.parse_args()
    for d in [CACHE,OUT,EVIDENCE]:d.mkdir(parents=True,exist_ok=True)
    if not EXE.is_file():raise RuntimeError('Verified local RIFE executable is missing; no download attempted.')
    positions=[(-14,8),(14,8),(-14,-8),(14,-8),(0,0),(20,0),(0,12),(20,12),(10,6),(-10,6)] if not args.all else [(x,y) for x in range(-20,21) for y in range(-12,13)]
    started=time.monotonic()
    for i,(x,y) in enumerate(positions):
        build(x,y,args.scale)
        if i%10==0:print(i+1,'/',len(positions),x,y,round(time.monotonic()-started,1),'seconds',flush=True)
    sheet=Image.new('RGB',(5*400,2*400),'#edf5fb');draw=ImageDraw.Draw(sheet)
    for i,(x,y) in enumerate([(-14,8),(14,8),(-14,-8),(14,-8),(0,0),(20,0),(0,12),(20,12),(10,6),(-10,6)]):
        im=Image.open(build(x,y,args.scale)).crop((150,0,850,550));im.thumbnail((400,360),Image.Resampling.LANCZOS);sheet.paste(im,((i%5)*400,(i//5)*400+30),im);draw.text(((i%5)*400+10,(i//5)*400+10),f'yaw target {x*1.5:+g} / pitch {y*1.5:+g}',fill='#26394b')
    sheet.save(EVIDENCE/'field-first-inspection.png')
    manifest={'status':'locally interpolated two-axis field; visual review required','method':'RIFE v4.6 x2 temporal TTA; dense-flow alpha; fixed original body','source':str(SEQ['source_sha256']),'rife_sha256':sha(EXE),'cols':41,'rows':25,'yaw_limit':30,'pitch_limit':18,'width':1163,'head_height':600,'head_files':len(list(OUT.glob('pose-*.webp'))),'bytes':sum(p.stat().st_size for p in OUT.glob('pose-*.webp')),'seconds':round(time.monotonic()-started,1),'unseen_geometry':'Image interpolation only; not measured 3D anatomy or eye contact at arbitrary camera depth.'}
    (EVIDENCE/'build.json').write_text(json.dumps(manifest,indent=2));(OUT/'manifest.json').write_text(json.dumps(manifest));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
