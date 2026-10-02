"""Multi-view pose field with an anatomically compatible common image mesh.

Only existing supplied views; no model generation or independently moving eyes.
The geometry interpolates correspondence between views, not 3D reconstruction.
"""
from pathlib import Path
import json,time,hashlib,argparse
import cv2,numpy as np
from PIL import Image,ImageDraw
from build_pose_field import ROOT,STUDY,SOURCES,IMAGES,POINTS,POSES,contributors,triangles,H,W,NEUTRAL
from compatible_mesh import compatible
OUT=ROOT/'public/assets/owl/pose-field';EVIDENCE=ROOT/'evidence/owl-pose-field';CACHE=ROOT/'.cache/owl-pose-field'
def frame(x,y):
    ids,weights=contributors(x,y)
    if len(ids)==1:return IMAGES[ids[0]][:600].copy()
    pts=np.sum(np.array([POINTS[i] for i in ids])*weights[:,None,None],axis=0).astype(np.float32)
    tris,folds=compatible(triangles(pts,(0,0,W,H)),pts,[POINTS[i] for i in ids])
    if folds:raise ValueError(f'Unsafe mesh at {x},{y}: {folds} folded source triangles')
    result=np.zeros((H,W,4),np.float32);warps=[]
    for i,w in zip(ids,weights):
        if w<1e-7:continue
        mapping=np.zeros((H,W,2),np.float32)
        for tri in tris:
            dst=pts[tri];sx,sy,sw,sh=cv2.boundingRect(dst);x0,y0=max(0,sx),max(0,sy);x1,y1=min(W,sx+sw+1),min(H,sy+sh+1)
            yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32);hom=np.dstack([xx,yy,np.ones_like(xx)])
            mask=np.zeros(xx.shape,np.uint8);cv2.fillConvexPoly(mask,np.int32(np.rint(dst-[x0,y0])),1)
            mat=cv2.getAffineTransform(dst,POINTS[i][tri]);mapping[y0:y1,x0:x1][mask>0]=(hom@mat.T).astype(np.float32)[mask>0]
        rgba=IMAGES[i][:H].astype(np.float32)/255;rgba[:,:,:3]*=rgba[:,:,3:]
        warped=cv2.remap(rgba,mapping[:,:,0],mapping[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        result+=warped*w
    alpha=np.clip(result[:,:,3:],0,1);rgb=result[:,:,:3]/np.maximum(alpha,1e-5)
    rgba=np.uint8(np.clip(np.concatenate([rgb,alpha],axis=2)*255+.5,0,255))[:600]
    taper=np.clip((550-np.arange(600))/35,0,1)[:,None,None]
    rgba=np.uint8(np.round(rgba*taper+NEUTRAL[:600]*(1-taper)));rgba[550:]=NEUTRAL[550:600]
    return rgba
def main():
    p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');args=p.parse_args()
    for folder in [CACHE,OUT,EVIDENCE]:folder.mkdir(parents=True,exist_ok=True)
    samples=[(-21,12),(21,12),(-21,-12),(21,-12),(0,0),(30,0),(0,18),(30,18),(15,9),(-15,9)]
    positions=[(x*1.5,y*1.5) for x in range(-20,21) for y in range(-12,13)] if args.all else samples
    start=time.monotonic()
    for k,(x,y) in enumerate(positions):
        Image.fromarray(frame(x,y)).save(OUT/f'pose-{round(x/1.5)+20:02d}-{round(y/1.5)+12:02d}.webp','WEBP',quality=94,method=6,exact=True)
        if k%25==0:print(k+1,len(positions),round(time.monotonic()-start,1),flush=True)
    sheet=Image.new('RGB',(2000,800),'#edf5fb');draw=ImageDraw.Draw(sheet)
    for k,(x,y) in enumerate(samples):
        im=Image.fromarray(frame(x,y)).crop((150,0,850,550));im.thumbnail((400,360));sheet.paste(im,((k%5)*400,(k//5)*400+30),im);draw.text(((k%5)*400+10,(k//5)*400+10),f'yaw {x:+g} / pitch {y:+g}',fill='#26394b')
    sheet.save(EVIDENCE/'inspection.png');print('finished',time.monotonic()-start)
if __name__=='__main__':main()
