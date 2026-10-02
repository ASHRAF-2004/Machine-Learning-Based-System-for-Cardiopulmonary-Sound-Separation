"""Visual test for one new generated anchor before expanding pose coverage."""
from pathlib import Path
import sys
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
sys.path.insert(0,str(STUDY/'tools'))
from annotate_pose_landmarks import estimate
from build_pose_field import triangles,H,W
from compatible_mesh import compatible

def points(name,image):
    landmarks,debug=estimate(Image.fromarray(image))
    p=[[0,0],[1162,0],[1162,639],[0,639]]
    for y in [70,140,260,390,500,600]:
        ids=np.where(image[y,:,3]>128)[0];p.extend([[float(ids[0])-35,y],[float(ids[-1])+35,y]])
    p.extend([[490,35],[310,600],[490,600],[690,600],[880,600]])
    for box in debug['blue_iris_boxes_xyxy']:
        x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2;rx=(x1-x0)/2+9;ry=(y1-y0)/2+9
        p.extend([[cx-rx,cy-ry],[cx+rx,cy-ry],[cx+rx,cy+ry],[cx-rx,cy+ry]])
    base,tip=[np.float32(landmarks[k]) for k in ['beak_base','beak_tip']];axis=tip-base;side=np.float32([axis[1],-axis[0]]);side/=np.linalg.norm(side)
    p.append(base.tolist())
    for t in [.28,.55,.8]:
        center=base+(tip-base)*t;steps=np.arange(-50,51);samples=np.rint(center+steps[:,None]*side).astype(int);dark=np.max(image[samples[:,1],samples[:,0],:3],axis=1)<155;selected=steps[dark & (np.abs(steps)<43)];left,right=(selected.min(),selected.max()) if len(selected)>1 else (-8,8);p.extend([(center+side*(left-1)).tolist(),(center+side*(right+1)).tolist()])
    p.append(tip.tolist());return np.float32(p)

def main():
    a=np.asarray(Image.open(STUDY/'assembled/neutral-original.png').convert('RGBA'))
    path=ROOT/'evidence/owl-continuous-atlas/generated/yaw-plus7p5-pitch-plus4p5.png'
    b=np.asarray(Image.open(path).convert('RGBA'));pa,pb=points('neutral-original',a),points('generated-mid',b)
    out=ROOT/'evidence/owl-continuous-atlas/generated-transition';out.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(1900,390),'#edf5fb');draw=ImageDraw.Draw(sheet)
    for k,t in enumerate([0,.25,.5,.75,1]):
        target=pa*(1-t)+pb*t;mesh,folds=compatible(triangles(target,(0,0,W,H)),target,[pa,pb])
        if folds:raise ValueError(f'{folds} folds')
        result=np.zeros((H,W,4),np.float32)
        for image,source,weight in [(a,pa,1-t),(b,pb,t)]:
            mapping=np.zeros((H,W,2),np.float32)
            for tri in mesh:
                dst=target[tri];x,y,w,h=cv2.boundingRect(dst);x0,y0=max(x,0),max(y,0);x1,y1=min(W,x+w+1),min(H,y+h+1)
                yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32);hom=np.dstack([xx,yy,np.ones_like(xx)])
                mask=np.zeros(xx.shape,np.uint8);cv2.fillConvexPoly(mask,np.int32(np.rint(dst-[x0,y0])),1)
                matrix=cv2.getAffineTransform(dst,source[tri]);values=(hom@matrix.T).astype(np.float32);mapping[y0:y1,x0:x1][mask>0]=values[mask>0]
            f=image[:H].astype(np.float32)/255;f[:,:,:3]*=f[:,:,3:];result+=cv2.remap(f,mapping[:,:,0],mapping[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)*weight
        alpha=np.clip(result[:,:,3:],0,1);rgb=result[:,:,:3]/np.maximum(alpha,1e-5);rgba=np.uint8(np.clip(np.concatenate([rgb,alpha],2)*255+.5,0,255))[:600]
        Image.fromarray(rgba).save(out/f't-{t:.2f}.png')
        view=Image.fromarray(rgba).crop((170,0,850,560));view.thumbnail((375,350));sheet.paste(view,(k*380,30),view);draw.text((k*380+8,8),f't={t:.2f}',fill='#26394b')
    sheet.save(out/'inspection.png')
if __name__=='__main__':main()
