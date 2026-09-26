"""Build one continuous, texture-registered owl surface from existing artwork.

Source PNGs stay untouched. Every view is mapped into one neutral coordinate
system so both geometry and texture can interpolate without choosing a winner.
Runtime data is nine RGBA textures and nine correspondence meshes, not a frame
request on each pointer update. This is image-based rendering, not recovered 3D.
"""
from pathlib import Path
import argparse, hashlib, json, sys, time
import cv2
import numpy as np
from PIL import Image, ImageDraw
from compatible_mesh import compatible

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
OUT=ROOT/'public/assets/owl/smooth-v2'
EVIDENCE=ROOT/'evidence/owl-smooth-v2'
W,H=1163,600
cv2.setNumThreads(2)
SPECS=[('neutral-original',0,0),('yaw-plus30-pitch0',30,0),('yaw-plus30-pitch-plus18',30,18),('yaw0-pitch-plus18',0,18),('yaw-minus30-pitch-plus18',-30,18),('yaw-minus30-pitch0',-30,0),('yaw-minus30-pitch-minus18',-30,-18),('yaw0-pitch-minus18',0,-18),('yaw-plus30-pitch-minus18',30,-18)]
ANNOTATIONS={r['pose']:r for r in json.loads((STUDY/'evidence/landmarks.json').read_text())['poses']}
Y,X=np.mgrid[:H,:W].astype(np.float32)
GRID=np.dstack([X,Y])

def controls(name,image):
    r=ANNOTATIONS[name];p=[]
    # The full image boundary and the lower neck never move.
    for x in np.linspace(0,W-1,9):p.extend([[x,0],[x,H-1],[x,560]])
    for y in [90,210,350,460]:p.extend([[0,y],[W-1,y]])
    # Corresponding silhouette samples anchor width without cropping feather tips.
    top=int(np.where((image[:,:,3]>160).any(axis=1))[0][0])
    xs=np.where(image[top+2,:,3]>160)[0]
    p.append([float((xs[0]+xs[-1])/2),top+2])
    for f in [.06,.14,.27,.42,.63,.82,1]:
        y=round(top+(500-top)*f)
        xs=np.where(image[y,:,3]>160)[0]
        p.extend([[float(xs[0]),y],[float(xs[-1]),y]])
    for box in r['detection_evidence']['blue_iris_boxes_xyxy']:
        x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2
        rx=(x1-x0)/2+5;ry=(y1-y0)/2+5
        p.append([cx,cy])
        for a in np.linspace(0,np.pi*2,8,endpoint=False):p.append([cx+rx*np.cos(a),cy+ry*np.sin(a)])
    bx0,by0,bx1,by1=r['detection_evidence']['dark_beak_box_xyxy']
    dark=np.uint8(np.max(image[by0:by1,bx0:bx1,:3],axis=2)<155)
    count,labels,stats,_=cv2.connectedComponentsWithStats(dark)
    mask=np.uint8(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA])))
    for row in [int(np.where(mask.any(axis=1))[0][0]),int(np.where(mask.any(axis=1))[0][-1])]:
        xs=np.where(mask[row]>0)[0];p.append([float(bx0+(xs[0]+xs[-1])/2),float(by0+row)])
    for f in [.12,.25,.40,.55,.70,.85,.94]:
        row=min(mask.shape[0]-1,round((mask.shape[0]-1)*f))
        xs=np.where(mask[row]>0)[0]
        if not len(xs):raise ValueError((name,row))
        p.extend([[float(bx0+xs[0]),float(by0+row)],[float(bx0+xs[-1]),float(by0+row)]])
    for f in [.32,.63,.9]:
        row=round((mask.shape[0]-1)*f);xs=np.where(mask[row]>0)[0]
        p.append([float(bx0+(xs[0]+xs[-1])/2),float(by0+row)])
    return np.float32(p)

def triangulate(points):
    sub=cv2.Subdiv2D((0,0,W,H))
    for point in points:sub.insert(tuple(map(float,point)))
    tris=[]
    for tri in sub.getTriangleList().reshape(-1,3,2):
        ids=[int(np.argmin(np.sum((points-p)**2,axis=1))) for p in tri]
        if len(set(ids))==3 and all(np.linalg.norm(points[i]-p)<.1 for i,p in zip(ids,tri)):tris.append(ids)
    return tris

def piecewise_map(a,b,tris):
    result=GRID.copy()
    for tri in tris:
        dest=a[tri];x,y,w,h=cv2.boundingRect(dest)
        x0,y0,x1,y1=max(0,x),max(0,y),min(W,x+w+1),min(H,y+h+1)
        yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32)
        mask=np.zeros(xx.shape,np.uint8)
        cv2.fillConvexPoly(mask,np.int32(np.rint(dest-[x0,y0])),1)
        matrix=cv2.getAffineTransform(dest,b[tri]);mapped=np.dstack([xx,yy,np.ones_like(xx)])@matrix.T
        result[y0:y1,x0:x1][mask>0]=mapped[mask>0]
    weight=np.clip((555-Y)/65,0,1);weight=weight*weight*(3-2*weight)
    return GRID+(result-GRID)*weight[:,:,None]

def tps_map(a,b):
    # Solve in normalized units; evaluate a regular coarse field, then bicubic
    # interpolation gives a smooth map without per-triangle topology switches.
    norm=np.float32([W,H]);q=a/norm;rr=np.sum((q[:,None]-q[None,:])**2,axis=2)
    k=rr*np.log(rr+1e-12);p=np.c_[np.ones(len(q)),q]
    matrix=np.block([[k+np.eye(len(q))*1e-7,p],[p.T,np.zeros((3,3))]])
    coef=np.linalg.solve(matrix,np.r_[(b-a)/norm,np.zeros((3,2))])
    yy,xx=np.mgrid[0:H:3,0:W:3].astype(np.float32);query=np.dstack([xx/W,yy/H]).reshape(-1,2)
    rr=np.sum((query[:,None]-q[None,:])**2,axis=2)
    values=np.c_[rr*np.log(rr+1e-12),np.ones(len(query)),query]@coef
    delta=cv2.resize(values.reshape(*xx.shape,2).astype(np.float32),(W,H),interpolation=cv2.INTER_CUBIC)*norm
    # Make the lower shoulder join exactly fixed, with a broad smooth taper.
    weight=np.clip((555-Y)/65,0,1);weight=weight*weight*(3-2*weight)
    return GRID+delta*weight[:,:,None]

def rgba_float(image):
    f=image.astype(np.float32)/255;f[:,:,:3]*=f[:,:,3:];return f

def remap(image,mapping):return cv2.remap(image,mapping[:,:,0],mapping[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)

def to_rgba(f):
    alpha=np.clip(f[:,:,3:],0,1);rgb=f[:,:,:3]/np.maximum(alpha,1e-5)
    return np.uint8(np.clip(np.concatenate([rgb,alpha],2)*255+.5,0,255))

def contributors(x,y):
    if abs(x)+abs(y)<1e-8:return [0,1,2],np.float32([1,0,0])
    for i in range(1,9):
        j=1 if i==8 else i+1
        p=np.float32([[0,0],SPECS[i][1:],SPECS[j][1:]])
        weights=np.linalg.solve(np.vstack([p.T,np.ones(3)]),np.float32([x,y,1]))
        if weights.min()>-1e-6:return [0,i,j],np.float32(np.clip(weights,0,1))
    raise ValueError((x,y))

def render(maps,images,x,y):
    ids,weights=contributors(x,y)
    mapping=sum(maps[i]*weight for i,weight in zip(ids,weights))
    delta=mapping-GRID;q=GRID-delta
    for _ in range(24):q=q*.5+(GRID-remap(delta,q))*.5
    f=np.zeros((H,W,4),np.float32)
    for i,weight in zip(ids,weights):
        source=remap(maps[i],q)
        f+=remap(rgba_float(images[i]),source)*weight
    return to_rgba(f)

def main():
    p=argparse.ArgumentParser();p.add_argument('--refine',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
    images=[np.asarray(Image.open(STUDY/'assembled'/f'{s[0]}.png').convert('RGBA'))[:H] for s in SPECS]
    points=[controls(s[0],im) for s,im in zip(SPECS,images)]
    canonical=points[0];maps=[];entries=[]
    tris,folds=compatible(triangulate(canonical),canonical,points)
    print('compatible triangles',len(tris),'folds',folds,flush=True)
    start=time.monotonic()
    for index,(name,yaw,pitch) in enumerate(SPECS):
        mapping=GRID.copy() if index==0 else piecewise_map(canonical,points[index],tris)
        normalized=remap(rgba_float(images[index]),mapping)
        if args.refine and index:
            neutral=rgba_float(images[0]);a=np.uint8(np.clip((neutral[:,:,:3]+(1-neutral[:,:,3:])*.8)*255,0,255));b=np.uint8(np.clip((normalized[:,:,:3]+(1-normalized[:,:,3:])*.8)*255,0,255))
            solver=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);solver.setFinestScale(0);solver.setGradientDescentIterations(30);solver.setVariationalRefinementIterations(10)
            flow=solver.calc(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY),cv2.cvtColor(b,cv2.COLOR_RGB2GRAY),None)
            # DIS only aligns short residual feather/edge displacements after
            # anatomy has been registered. Limit correction to prevent melting.
            flow=np.clip(flow,-14,14)
            guard=np.ones((H,W),np.float32)
            for box in ANNOTATIONS['neutral-original']['detection_evidence']['blue_iris_boxes_xyxy']:
                x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2
                rad=np.sqrt(((X-cx)/((x1-x0)/2+12))**2+((Y-cy)/((y1-y0)/2+12))**2)
                guard=np.minimum(guard,np.clip((rad-1)/.6,0,1))
            bx0,by0,bx1,by1=ANNOTATIONS['neutral-original']['detection_evidence']['dark_beak_box_xyxy'];rad=np.sqrt(((X-(bx0+bx1)/2)/55)**2+((Y-(by0+by1)/2)/85)**2);guard=np.minimum(guard,np.clip((rad-1)/.6,0,1))
            guard*=np.clip((550-Y)/70,0,1)
            mapping=remap(mapping,GRID+flow*guard[:,:,None]);normalized=remap(rgba_float(images[index]),mapping)
        maps.append(mapping)
        Image.fromarray(to_rgba(normalized)).save(EVIDENCE/f'normalized-{index}.png')
        # Native source resolution, no generated replacement pose or sharpening.
        texture=OUT/f'view-{index}.webp';Image.fromarray(images[index]).save(texture,'WEBP',quality=97,method=6,exact=True)
        # One shared 233×121 mesh, with fixed coordinate sampling at endpoints.
        mx,my=np.meshgrid(np.linspace(0,W-1,233,dtype=np.float32),np.linspace(0,H-1,121,dtype=np.float32));vertices=cv2.remap(mapping,mx,my,cv2.INTER_LINEAR)
        vertices.astype('<f4').tofile(OUT/f'map-{index}.bin')
        entries.append({'id':index,'name':name,'yaw':yaw,'pitch':pitch,'texture':texture.name,'map':f'map-{index}.bin','source_sha256':hashlib.sha256((STUDY/'assembled'/f'{name}.png').read_bytes()).hexdigest(),'bytes':texture.stat().st_size+(OUT/f'map-{index}.bin').stat().st_size})
        print(index,name,round(time.monotonic()-start,1),flush=True)
    np.savez_compressed(EVIDENCE/'maps.npz',maps=np.asarray(maps))
    positions=[(0,0)]+[(30*.62*np.cos(a),18*.62*np.sin(a)) for a in np.linspace(0,np.pi*2,12,endpoint=False)]+[(30*.92*np.cos(a),18*.92*np.sin(a)) for a in np.linspace(0,np.pi*2,12,endpoint=False)]
    sheet=Image.new('RGB',(5*440,5*370),'#eaf3f9');draw=ImageDraw.Draw(sheet)
    for i,(x,y) in enumerate(positions):
        rgba=render(maps,images,x,y);Image.fromarray(rgba).save(EVIDENCE/f'pose-{i:02d}.png');view=Image.fromarray(rgba).crop((140,0,880,550));view.thumbnail((430,330));xx=(i%5)*440;yy=(i//5)*370;sheet.paste(view,(xx,yy+28),view);draw.text((xx+8,yy+8),f'{i}: {x:+.2f}, {y:+.2f}',fill='#21364c')
    sheet.save(EVIDENCE/'validation.png')
    (OUT/'manifest.json').write_text(json.dumps({'version':2,'width':W,'height':H,'meshWidth':233,'meshHeight':121,'views':entries,'source_role':'existing approved appearance poses; nominal artistic angles','refine':args.refine},indent=2))
    print('done',round(time.monotonic()-start,1),sum(e['bytes'] for e in entries),flush=True)

if __name__=='__main__':main()
