"""Restore connected full-source necks without touching the original PNGs.

The old assembled/library import restored neutral at500–555, inside the neck.
This experiment keeps the original head pixels and registers the lower torso
before a single750–900 premultiplied transition. It is not head generation.
"""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image

def smooth(a,b,y):
    t=np.clip((y-a)/(b-a),0,1);return t*t*(3-2*t)

def prepare(root,study,names,existing):
    out=root/'assets/owl-neck-continuity/registered';out.mkdir(parents=True,exist_ok=True)
    metrics={Path(r['raw']).stem:r for r in json.loads((study/'evidence/assembly-metrics.json').read_text())['poses']}
    neutral=np.asarray(Image.open(study/'key-poses/neutral-original.png').convert('RGBA'))
    yy,xx=np.mgrid[:1353,:1163].astype(np.float32)
    records=[];result=[];paths={}
    def gray(a):
        rgb=a[:,:,:3].astype(np.float32)*a[:,:,3:]/255
        return cv2.cvtColor(np.uint8(rgb),cv2.COLOR_RGB2GRAY)
    solver=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);solver.setFinestScale(0)
    # Only estimates lower-body image registration; never used on face/head.
    for name,old in zip(names,existing):
        source=study/'key-poses'/f'{name}.png'
        if not source.exists():
            # Existing up-right head repair is retained unchanged. The new
            # down-left crop is excluded by the caller: it lacks full neck.
            result.append(old.copy());paths[name]=root/'assets/owl-repairs/2026-09-24'/f'{name}.png';continue
        im=np.asarray(Image.open(source).convert('RGBA'))
        dx,dy=metrics[name]['registration']['applied_translation_xy']
        aligned=cv2.warpAffine(im,np.float32([[1,0,dx],[0,1,dy]]),(1163,1353),flags=cv2.INTER_NEAREST)
        if name=='neutral-original':registered=neutral.copy();maximum=0.
        else:
            flow=solver.calc(gray(neutral[480:1050]),gray(aligned[480:1050]),None)
            # Preserve the complete face/neck through500; registration rises
            # gradually through the breast. Limit bad flow in blank padding.
            flow=np.clip(flow,-24,24)
            flow=cv2.GaussianBlur(flow,(0,0),5)
            full=np.zeros((1353,1163,2),np.float32);full[480:1050]=flow
            full[1050:]=flow[-1]
            full*=smooth(500,760,yy)[:,:,None]
            f=aligned.astype(np.float32)/255;f[:,:,:3]*=f[:,:,3:]
            warped=cv2.remap(f,xx+full[:,:,0],yy+full[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            n=neutral.astype(np.float32)/255;n[:,:,:3]*=n[:,:,3:]
            t=smooth(750,900,yy)[:,:,None];p=warped*(1-t)+n*t
            p[:,:,:3]/=np.maximum(p[:,:,3:],1e-6)
            registered=np.uint8(np.clip(p*255+.5,0,255));registered[:500]=aligned[:500];registered[900:]=neutral[900:]
            maximum=float(np.linalg.norm(full[500:900],axis=2).max())
        dest=out/f'{name}.png';Image.fromarray(registered).save(dest)
        assert np.array_equal(registered[:500],aligned[:500])
        assert np.array_equal(registered[900:],neutral[900:])
        paths[name]=dest;result.append(registered)
        records.append({'name':name,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'file':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'head_translation':[dx,dy],'head_unchanged_below_row':500,'fixed_body_from_row':900,'max_body_registration_pixels':maximum})
    (out/'manifest.json').write_text(json.dumps({'method':'Full-source head/neck; lower torso registration only; one750–900 transition','views':records},indent=2))
    return result,paths

def extend_controls(points,image):
    p=points.copy()
    # Existing indices are retained so manually traced eye/pupil boundaries
    # still identify the same geometry. Move only the old fixed outer cage.
    p[:27,1][p[:27,1]==599]=899
    p[:27,1][p[:27,1]==560]=880
    # Full lower-neck silhouette, not the abruptly restored neutral contour.
    extras=[]
    for y in [530,560,600,640,690,740,790,840]:
        xs=np.where(image[y,:,3]>160)[0]
        extras.extend([[float(xs[0]),y],[float(xs[-1]),y]])
    # Interior torso correspondence is fixed after registration, not head yaw.
    for y in [620,740,840]:
        for x in [320,450,580,710,840]:extras.append([x,y])
    return np.vstack([p,extras]).astype(np.float32)
