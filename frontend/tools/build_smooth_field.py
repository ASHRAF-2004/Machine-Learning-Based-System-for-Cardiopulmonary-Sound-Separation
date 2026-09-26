"""Continuous local view interpolation using the original clean pose set.

The source images are immutable. Correspondence is cached and sampled into
small GPU meshes; no per-pointer image decoding and no hard texture winner.
This is multi-view image interpolation, not a recovered 3D owl.
"""
from pathlib import Path
import sys,json,hashlib,time,argparse,gzip,io
import cv2,numpy as np
from PIL import Image,ImageDraw
from build_pose_field import STUDY,ROOT,angles,triangles
sys.path.insert(0,str(STUDY/'tools'))
from test_transition import rgba_float,inverse_coordinates,sample
from owl_correspondence import controls,triangulate
from compatible_mesh import compatible
cv2.setNumThreads(2)
ANNOTATIONS=json.loads((STUDY/'evidence/landmarks.json').read_text())['poses']
SOURCES=['neutral-original']+sorted(r['pose'] for r in ANNOTATIONS if r['pose']!='neutral-original')
POSES=np.float32([angles(n) for n in SOURCES])
IMAGES=[np.asarray(Image.open(STUDY/'assembled'/f'{n}.png').convert('RGBA')).copy() for n in SOURCES]
for im in IMAGES[1:]:
    # End all head texture changes before the shared, fixed body boundary.
    t=np.clip((555-np.arange(im.shape[0],dtype=np.float32))/25,0,1)[:,None,None]
    im[:]=np.uint8(im*t+IMAGES[0]*(1-t)+.5)
VIEW_TRIS=triangles(POSES+np.float32([31,19]),(0,0,63,39))
def contributors(x,y):
    target=np.float32([x,y]);d=np.linalg.norm(POSES-target,axis=1)
    if d.min()<1e-5:return[int(d.argmin())],np.float32([1])
    for ids in VIEW_TRIS:
        weights=np.linalg.solve(np.vstack([POSES[ids].T,np.ones(3)]),np.r_[target,1])
        if weights.min()>-1e-6:return ids,np.float32(np.clip(weights,0,1))
    raise ValueError((x,y))
OUT=ROOT/'public/assets/owl/smooth-field'
EVIDENCE=ROOT/'evidence/owl-smooth-v2/local-field'
CACHE=ROOT/'.cache/owl-smooth-field'
H,W=640,1163
Y,X=np.mgrid[:H,:W].astype(np.float32);GRID=np.dstack([X,Y])
FLOWS={}
REFINE=False
POINTS=[controls(name,im[:600]) for name,im in zip(SOURCES,IMAGES)]

def refine_feathers(i,j,field):
    a=rgba_float(IMAGES[i][:H]);b=sample(rgba_float(IMAGES[j][:H]),GRID+field)
    def gray(im):return cv2.cvtColor(np.uint8(np.clip((im[:,:,:3]+(1-im[:,:,3:])*.8)*255,0,255)),cv2.COLOR_RGB2GRAY)
    solver=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM);solver.setFinestScale(0)
    solver.setGradientDescentIterations(30);solver.setVariationalRefinementIterations(10)
    f=np.clip(solver.calc(gray(a),gray(b),None),-3,3)
    protect=np.zeros((H,W),np.uint8)
    # Only fine feather registration. The entire eyes, lids, beak and silhouette
    # are excluded from residual flow; there are no replacement eye overlays.
    from owl_correspondence import ANNOTATIONS
    r=ANNOTATIONS[SOURCES[i]]
    for x0,y0,x1,y1 in r['detection_evidence']['blue_iris_boxes_xyxy']:
        cv2.ellipse(protect,(round((x0+x1)/2),round((y0+y1)/2)),(round((x1-x0)/2+35),round((y1-y0)/2+30)),0,0,360,1,-1)
    x0,y0,x1,y1=r['detection_evidence']['dark_beak_box_xyxy'];protect[max(0,y0-20):y1+24,max(0,x0-28):x1+28]=1
    weight=np.clip(cv2.distanceTransform(1-protect,cv2.DIST_L2,5)/18,0,1)
    weight*=np.clip((cv2.distanceTransform(np.uint8(a[:,:,3]>.95),cv2.DIST_L2,5)-10)/15,0,1)
    weight*=np.clip((490-Y)/45,0,1)
    q=GRID+f*weight[:,:,None]
    return (q+sample(field,q)-GRID).astype(np.float32)

def geometry_field(i,j,tris):
    a,b=POINTS[i],POINTS[j];field=np.zeros((H,W,2),np.float32)
    for tri in tris:
        dest=a[tri];x,y,w,h=cv2.boundingRect(dest);x0,y0,x1,y1=max(0,x),max(0,y),min(W,x+w+1),min(600,y+h+1)
        if x1<=x0 or y1<=y0:continue
        yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float64)
        # Rasterize the actual floating-point triangle. Rounded polygon masks
        # paint beyond thin triangles, overwriting adjacent neck pixels with
        # extrapolated transforms (large spikes in the final regular GPU mesh).
        bary=cv2.getAffineTransform(dest,np.float32([[0,0],[1,0],[0,1]]))
        uv=np.dstack([xx,yy,np.ones_like(xx)])@bary.T
        inside=(uv[:,:,0]>=-1e-7)&(uv[:,:,1]>=-1e-7)&(uv.sum(axis=2)<=1+1e-7)
        displacement=b[tri]-dest
        delta=displacement[0]+uv[:,:,0,None]*(displacement[1]-displacement[0])+uv[:,:,1,None]*(displacement[2]-displacement[0])
        field[y0:y1,x0:x1][inside]=delta[inside]
    return field

def get_flow(i,j):
    if i==j:return GRID*0
    if (i,j) not in FLOWS:
        candidates=[]
        for t in [0,1,.5,.2,.4,.6,.8]:
            seed=POINTS[i]*(1-t)+POINTS[j]*t
            candidate=compatible(triangulate(seed),seed,[POINTS[i],POINTS[j]])
            candidates.append(candidate)
            if candidate[1]==0:break
        tris,folds=min(candidates,key=lambda item:item[1])
        if folds:raise ValueError(f'Unsafe correspondence topology {SOURCES[i]} / {SOURCES[j]}: {folds} folds')
        print('pair',i,j,'folds',folds,flush=True)
        f,r=geometry_field(i,j,tris),geometry_field(j,i,tris)
        if REFINE:f,r=refine_feathers(i,j,f),refine_feathers(j,i,r)
        taper=np.clip((555-Y)/60,0,1);taper=taper*taper*(3-2*taper)
        FLOWS[i,j]=f*taper[:,:,None];FLOWS[j,i]=r*taper[:,:,None]
        return FLOWS[i,j]
    return FLOWS[i,j]

def frame(x,y):
    ids,weights=contributors(x,y)
    if len(ids)==1:return IMAGES[ids[0]][:600].copy()
    out=np.zeros((H,W,4),np.float32)
    for i,w in zip(ids,weights):
        field=np.float32(sum(get_flow(i,j)*np.float32(v) for j,v in zip(ids,weights)))
        q=inverse_coordinates(field,1)
        out+=sample(rgba_float(IMAGES[i][:H]),q)*w
    a=np.clip(out[:,:,3:],0,1);rgb=out[:,:,:3]/np.maximum(a,1e-5)
    return np.uint8(np.clip(np.concatenate([rgb,a],2)*255+.5,0,255))[:600]

def main():
    global REFINE
    p=argparse.ArgumentParser();p.add_argument('--export',action='store_true');p.add_argument('--refine',action='store_true');p.add_argument('--skip-evidence',action='store_true');args=p.parse_args();REFINE=args.refine
    for folder in [OUT,EVIDENCE,CACHE]:folder.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    poses=[(0,0)]+[(30*r*np.cos(a),18*r*np.sin(a)) for r in [.35,.65,.92] for a in np.linspace(0,np.pi*2,12,endpoint=False)]
    sheet=Image.new('RGB',(6*360,7*320),'#eaf3f9');draw=ImageDraw.Draw(sheet)
    for k,(x,y) in enumerate([] if args.skip_evidence else poses):
        im=Image.fromarray(frame(x,y));im.save(EVIDENCE/f'pose-{k:02d}.png')
        im=im.crop((140,0,900,560));im.thumbnail((350,280));xx=(k%6)*360;yy=(k//6)*320
        sheet.paste(im,(xx,yy+30),im);draw.text((xx+10,yy+10),f'{k}: {x:+.2f}, {y:+.2f}',fill='#243d50')
    if not args.skip_evidence:sheet.save(EVIDENCE/'validation.png')
    if args.export:
        views=[];edges=[]
        for i,(name,pose,im) in enumerate(zip(SOURCES,POSES,IMAGES)):
            encoded=io.BytesIO();Image.fromarray(im[:600]).save(encoded,'WEBP',quality=97,method=6,exact=True)
            data=encoded.getvalue();dest=OUT/f'view-{i}-{hashlib.sha256(data).hexdigest()[:12]}.webp';dest.write_bytes(data)
            views.append({'id':i,'name':name,'yaw':float(pose[0]),'pitch':float(pose[1]),'texture':dest.name,'bytes':dest.stat().st_size,'source_sha256':hashlib.sha256((STUDY/'assembled'/f'{name}.png').read_bytes()).hexdigest()})
        # Five-pixel source mesh. Texture is full native resolution; mesh density
        # and photographic sampling are independent.
        mx,my=np.meshgrid(np.linspace(0,W-1,233,dtype=np.float32),np.linspace(0,599,121,dtype=np.float32))
        pairs=sorted({tuple(sorted([a,b])) for tri in VIEW_TRIS for a,b in zip(tri,tri[1:]+tri[:1])})
        for a,b in pairs:
            for i,j in [(a,b),(b,a)]:
                f=get_flow(i,j);vertices=cv2.remap(f,mx,my,cv2.INTER_LINEAR)
                raw=vertices.astype('<f2').tobytes();data=gzip.compress(raw,compresslevel=9,mtime=0)
                dest=OUT/f'flow-{i}-{j}-{hashlib.sha256(data).hexdigest()[:12]}.bin.gz';dest.write_bytes(data)
                edges.append({'from':i,'to':j,'file':dest.name,'bytes':dest.stat().st_size,'decodedBytes':len(raw)})
        manifest={'version':4,'width':W,'height':600,'meshWidth':233,'meshHeight':121,'views':views,'triangles':VIEW_TRIS,'edges':edges,'floatEncoding':'float16-le-gzip','featherRefinement':REFINE,'source_role':'original clean generated appearance anchors, not video frames; nominal artistic angles'}
        # Publish last. A failed build never points the running site at a mix
        # of old textures and new topology. Hashed assets are immutable.
        staged=OUT/'manifest.next.json';staged.write_text(json.dumps(manifest,indent=2));staged.replace(OUT/'manifest.json')
        print('bytes',sum(v['bytes'] for v in views)+sum(e['bytes'] for e in edges),flush=True)
    print('done',time.monotonic()-start,flush=True)

if __name__=='__main__':main()
