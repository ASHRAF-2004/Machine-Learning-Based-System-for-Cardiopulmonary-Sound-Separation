"""Landmark-registered multi-view pose field. Never a single-frontal pseudo-yaw.

All source views and annotations are existing read-only project assets. This
bounded trial aligns complete feature regions before combining views; it does
not overlay independently moving eyes. Outputs remain review candidates.
"""
from pathlib import Path
import sys,json,argparse,hashlib,time
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
sys.path.insert(0,str(STUDY/'tools'))
from landmark_transition import landmarks
OUT=ROOT/'public/assets/owl/field-continuous'
EVIDENCE=ROOT/'evidence/owl-field-continuous'
CACHE=ROOT/'.cache/owl-field-continuous'
H,W=640,1163
cv2.setNumThreads(2)
SOURCES=json.loads((STUDY/'feather-continuity/rife-exports/sequence.json').read_text())['source_names']
def angles(name):
    if name=='neutral-original':return [0.,0.]
    import re
    m=re.match(r'yaw(-minus|-plus)?(\d+)-pitch(-minus|-plus)?(\d+)',name)
    if not m:raise ValueError(name)
    return [float(m[2])*(-1 if m[1]=='-minus' else 1),float(m[4])*(-1 if m[3]=='-minus' else 1)]
POSES=np.float32([angles(n) for n in SOURCES])
IMAGES=[np.asarray(Image.open(STUDY/'assembled'/f'{n}.png').convert('RGBA')) for n in SOURCES]
ANNOTATIONS={r['pose']:r for r in json.loads((STUDY/'evidence/landmarks.json').read_text())['poses']}
def coherent_points(name,im):
    p=landmarks(name,im)[:29].tolist()
    # Keep the exterior cage outside the complete eye opening at every view.
    # Fixed-y alpha samples are not facial topology vertices.
    for i in range(4,16,2):p[i][0]-=35;p[i+1][0]+=35
    # Previous broad beak rectangles overlap the far eye in turned-up views.
    # Use actual rigid beak contours, not that anatomically impossible cage.
    for start in [21,25]:
        q=np.float32(p[start:start+4]);center=q.mean(axis=0);q=center+(q-center)*.83;p[start:start+4]=q.tolist()
    r=ANNOTATIONS[name];base,tip=[np.float32(r['landmarks_xy'][k]) for k in ['beak_base','beak_tip']]
    axis=tip-base;side=np.float32([axis[1],-axis[0]]);side/=np.linalg.norm(side)
    p.append(base.tolist())
    for t in [.28,.55,.8]:
        center=base+(tip-base)*t;steps=np.arange(-50,51);samples=np.rint(center+steps[:,None]*side).astype(int)
        dark=np.max(im[samples[:,1],samples[:,0],:3],axis=1)<155
        selected=steps[dark & (np.abs(steps)<43)]
        left,right=(selected.min(),selected.max()) if len(selected)>1 else (-8,8)
        p.extend([(center+side*(left-1)).tolist(),(center+side*(right+1)).tolist()])
    p.append(tip.tolist())
    return np.float32(p)
POINTS=[coherent_points(n,im) for n,im in zip(SOURCES,IMAGES)]
NEUTRAL=IMAGES[SOURCES.index('neutral-original')]
FLOATS=[]
for im in IMAGES:
    f=im[:H].astype(np.float32)/255;f[:,:,:3]*=f[:,:,3:];FLOATS.append(f)
def triangles(points,bounds):
    sub=cv2.Subdiv2D(bounds)
    for p in points:sub.insert(tuple(float(x) for x in p))
    result=[]
    for tri in sub.getTriangleList().reshape(-1,3,2):
        ids=[int(np.argmin(np.sum((points-p)**2,axis=1))) for p in tri]
        if all(np.linalg.norm(points[i]-p)<.1 for i,p in zip(ids,tri)):result.append(ids)
    return result
VIEW_TRIS=triangles(POSES+np.float32([31,19]),(0,0,63,39))
def contributors(x,y):
    target=np.float32([x,y]);close=np.linalg.norm(POSES-target,axis=1)
    if close.min()<.001:return [int(close.argmin())],np.array([1.])
    for ids in VIEW_TRIS:
        p=POSES[ids];mat=np.vstack([p.T,np.ones(3)]);weights=np.linalg.solve(mat,np.r_[target,1])
        if weights.min()>-1e-5:return ids,np.clip(weights,0,1)
    raise ValueError(f'Outside approved pose hull {target}')
def frame(x,y):
    ids,weights=contributors(x,y)
    if len(ids)==1:return IMAGES[ids[0]][:600].copy(),0
    pts=np.sum(np.array([POINTS[i] for i in ids])*weights[:,None,None],axis=0).astype(np.float32)
    result=np.zeros((H,W,4),np.float32);folds=0
    norm=np.float32([W,H]);cp=pts/norm
    delta=cp[:,None,:]-cp[None,:,:];rr=np.sum(delta*delta,axis=2);kernel=rr*np.log(rr+1e-10)
    pp=np.c_[np.ones(len(cp)),cp]
    matrix=np.block([[kernel+np.eye(len(cp))*.00001,pp],[pp.T,np.zeros((3,3))]])
    yy,xx=np.mgrid[0:H:4,0:W:4].astype(np.float32);qq=np.stack([xx/W,yy/H],axis=2).reshape(-1,2)
    rr=np.sum((qq[:,None,:]-cp[None,:,:])**2,axis=2);query=np.c_[rr*np.log(rr+1e-10),np.ones(len(qq)),qq]
    warped_sources=[]
    for source,weight in zip(ids,weights):
        if weight<1e-6:continue
        coefficient=np.linalg.solve(matrix,np.r_[POINTS[source]/norm,np.zeros((3,2))])
        mapped=(query@coefficient).reshape(*xx.shape,2)*norm
        displacement=mapped-np.stack([xx,yy],axis=2)
        displacement=cv2.resize(displacement,(W,H),interpolation=cv2.INTER_CUBIC)
        yy0,xx0=np.mgrid[:H,:W].astype(np.float32);mapping=(np.stack([xx0,yy0],axis=2)+displacement).astype(np.float32)
        warped=cv2.remap(FLOATS[source],mapping[:,:,0],mapping[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        warped_sources.append((warped,weight))
    # Correct the remaining small image correspondence after anatomical alignment.
    # This is optical flow between actual different views, not independent eyes.
    gray=[cv2.cvtColor(np.uint8(np.clip((a[:,:,:3]+(1-a[:,:,3:])*.9)*255,0,255)),cv2.COLOR_RGB2GRAY) for a,w in warped_sources]
    solver=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);solver.setFinestScale(0)
    solver.setGradientDescentIterations(40);solver.setVariationalRefinementIterations(20)
    yy0,xx0=np.mgrid[:H,:W].astype(np.float32);g=np.stack([xx0,yy0],axis=2)
    for i,(a,w) in enumerate(warped_sources):
        displacement=np.zeros_like(g)
        for j,(b,v) in enumerate(warped_sources):
            if i!=j:displacement+=solver.calc(gray[i],gray[j],None)*v
        q=g-displacement
        for _ in range(6):q=.5*q+.5*(g-cv2.remap(displacement,q[:,:,0],q[:,:,1],cv2.INTER_LINEAR))
        result+=cv2.remap(a,q[:,:,0],q[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)*w
    alpha=np.clip(result[:,:,3:],0,1);rgb=np.divide(result[:,:,:3],np.maximum(alpha,1e-5))
    rgba=np.uint8(np.clip(np.concatenate([rgb,alpha],axis=2)*255+.5,0,255))[:600]
    taper=np.clip((525-np.arange(600))/35,0,1)[:,None,None]
    rgba=np.uint8(np.round(rgba*taper+NEUTRAL[:600]*(1-taper)));rgba[525:]=NEUTRAL[525:600]
    return rgba,folds
def main():
    p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    sample=[(-21,12),(21,12),(-21,-12),(21,-12),(0,0),(30,0),(0,18),(30,18),(15,9),(-15,9)]
    positions=[(x*1.5,y*1.5) for x in range(-20,21) for y in range(-12,13)] if args.all else sample
    records=[];started=time.monotonic()
    for i,(x,y) in enumerate(positions):
        path=OUT/f'pose-{round(x/1.5)+20:02d}-{round(y/1.5)+12:02d}.webp'
        im,folds=frame(x,y);Image.fromarray(im).save(path,'WEBP',quality=94,method=6,exact=True)
        records.append({'yaw':x,'pitch':y,'folds':folds,'bytes':path.stat().st_size})
        if i%25==0:print(i+1,len(positions),round(time.monotonic()-started,1),flush=True)
    sheet=Image.new('RGB',(2000,800),'#edf5fb');draw=ImageDraw.Draw(sheet)
    for i,(x,y) in enumerate(sample):
        im,folds=frame(x,y);im=Image.fromarray(im).crop((150,0,850,550));im.thumbnail((400,360));sheet.paste(im,((i%5)*400,(i//5)*400+30),im);draw.text(((i%5)*400+10,(i//5)*400+10),f'yaw {x:+g} / pitch {y:+g} / folds {folds}',fill='#26394b')
    sheet.save(EVIDENCE/'aligned-inspection.png');(EVIDENCE/'build.json').write_text(json.dumps({'records':records,'seconds':time.monotonic()-started},indent=2));print('finished',time.monotonic()-started)
if __name__=='__main__':main()
