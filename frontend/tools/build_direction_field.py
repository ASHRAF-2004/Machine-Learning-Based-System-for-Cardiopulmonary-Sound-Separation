"""Two-dimensional view lookup using the existing approved multi-view sources.

Uses the source study's feature-guided dense correspondence, never a frontal
image pretending to be 3D. New output is isolated until browser visual review.
"""
from pathlib import Path
import sys,json,time,argparse,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
sys.path.insert(0,str(STUDY/'tools'))
from test_transition import flow_pair,inverse_coordinates,rgba_float,sample
from build_pose_field import SOURCES,POSES,IMAGES,contributors
from functools import lru_cache
CACHE=ROOT/'.cache/owl-direction-field';OUT=ROOT/'public/assets/owl/directions';EVIDENCE=ROOT/'evidence/owl-directions'
cv2.setNumThreads(2)
NEUTRAL=IMAGES[SOURCES.index('neutral-original')][:600]
@lru_cache(maxsize=15)
def pair(i,j):
    name=f'{SOURCES[i]}--{SOURCES[j]}--features.npz'
    return flow_pair(IMAGES[i],IMAGES[j],'features',CACHE/name)
def flow(i,j):
    if i<j:return pair(i,j)[0]
    return pair(j,i)[1]
def frame(x,y):
    ids,weights=contributors(x,y)
    if len(ids)==1:return IMAGES[ids[0]][:600].copy()
    result=np.zeros((640,1163,4),np.float32)
    for i,w in zip(ids,weights):
        if w<1e-6:continue
        field=np.zeros((640,1163,2),np.float32)
        for j,v in zip(ids,weights):
            if i!=j and v>1e-6:field+=flow(i,j)*v
        q=inverse_coordinates(field,1)
        result+=sample(rgba_float(IMAGES[i][:640]),q)*w
    alpha=result[:,:,3:];rgb=result[:,:,:3]/np.maximum(alpha,1e-5)
    rgba=np.uint8(np.clip(np.concatenate([rgb,alpha],axis=2)*255+.5,0,255))[:600]
    taper=np.clip((550-np.arange(600))/35,0,1)[:,None,None]
    rgba=np.uint8(np.round(rgba*taper+NEUTRAL*(1-taper)));rgba[550:]=NEUTRAL[550:]
    return rgba
def main():
    p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');args=p.parse_args()
    for folder in [CACHE,OUT,EVIDENCE]:folder.mkdir(parents=True,exist_ok=True)
    sample_poses=[(-21,12),(21,12),(-21,-12),(21,-12),(0,0),(30,0),(0,18),(30,18),(15,9),(-15,9)]
    positions=[(x*1.5,y*1.5) for x in range(-20,21) for y in range(-12,13)] if args.all else sample_poses
    started=time.monotonic()
    for k,(x,y) in enumerate(positions):
        Image.fromarray(frame(x,y)).save(OUT/f'pose-{round(x/1.5)+20:02d}-{round(y/1.5)+12:02d}.webp','WEBP',quality=94,method=6,exact=True)
        if k%25==0:print(k+1,len(positions),time.monotonic()-started,flush=True)
    sheet=Image.new('RGB',(2000,800),'#edf5fb');draw=ImageDraw.Draw(sheet)
    for k,(x,y) in enumerate(sample_poses):
        im=Image.fromarray(frame(x,y)).crop((150,0,850,550));im.thumbnail((400,360));sheet.paste(im,((k%5)*400,(k//5)*400+30),im);draw.text(((k%5)*400+10,(k//5)*400+10),f'yaw {x:+g} / pitch {y:+g}',fill='#26394b')
    sheet.save(EVIDENCE/'inspection.png')
    print('finished',time.monotonic()-started)
if __name__=='__main__':main()
