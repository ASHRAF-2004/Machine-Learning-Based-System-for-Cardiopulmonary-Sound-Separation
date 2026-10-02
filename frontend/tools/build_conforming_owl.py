"""Conforming refinement of the existing registered multi-view owl surface.

Every source mesh follows ALL of its pairwise correspondence boundaries.
Unlike a regular grid, no GPU triangle cuts across a narrow eyelid/beak cell.
Shared pose edges reuse exactly the same maps; no sector-dependent remeshing.
This is image interpolation, not 3D reconstruction. Two separately generated
repair crops supplement the unchanged original appearance sources.
"""
from pathlib import Path
import json,hashlib,gzip,time,io,os
import cv2,numpy as np
from PIL import Image
from build_smooth_field import ROOT,OUT,SOURCES,POSES,IMAGES,POINTS,VIEW_TRIS
from owl_correspondence import triangulate,controls,SILHOUETTE_FRACTIONS
from compatible_mesh import compatible
TRIAL=os.environ.get('OWL_DIAGONAL_TRIAL')=='1'
if TRIAL:OUT=ROOT/'public/assets/owl/diagonal-candidate'
NECK=os.environ.get('OWL_NECK_TRIAL')=='1'
H=900 if NECK else 600
if NECK:OUT=ROOT/'public/assets/owl/neck-candidate'
SOURCE_PATHS={n:ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study/assembled'/f'{n}.png' for n in SOURCES}
from owl_correspondence import ANNOTATIONS
repairs=ROOT/'assets/owl-repairs/2026-09-24'
extra=json.loads((repairs/'manifest.json').read_text())['views']
if NECK:extra=[r for r in extra if r['name']!='repair-down-left']
SOURCES=SOURCES+[r['name'] for r in extra]
POSES=np.vstack([POSES,np.float32([[r['yaw'],r['pitch']] for r in extra])])
IMAGES=IMAGES+[np.array(Image.open(repairs/r['file']).convert('RGBA')) for r in extra]
for r in extra:ANNOTATIONS[r['name']]=r;SOURCE_PATHS[r['name']]=repairs/r['file']
if NECK:
    from owl_full_sources import prepare,extend_controls
    from build_smooth_field import STUDY
    IMAGES,SOURCE_PATHS=prepare(ROOT,STUDY,SOURCES,IMAGES)
from build_pose_field import triangles
VIEW_TRIS=triangles(POSES+np.float32([31,19]),(0,0,63,39))

def signed(poly):
    p=np.asarray(poly,dtype=np.float64);return np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))/2

def bounds(poly):return np.r_[poly.min(axis=0),poly.max(axis=0)]

def clip_triangle(cell,tri):
    p=cell.astype(np.float64)
    for a,b in zip(tri,np.roll(tri,-1,axis=0)):
        if len(p)<3:return None
        edge=b-a;distance=edge[0]*(p[:,1]-a[1])-edge[1]*(p[:,0]-a[0])
        inside=distance>=-1e-9
        if inside.all():continue
        if not inside.any():return None
        out=[]
        for k in range(len(p)):
            previous=k-1
            if inside[k]!=inside[previous]:
                t=distance[previous]/(distance[previous]-distance[k])
                out.append(p[previous]+(p[k]-p[previous])*t)
            if inside[k]:out.append(p[k])
        p=np.asarray(out)
    return p

def overlay(cells,triangles):
    boxes=np.asarray([bounds(t) for t in triangles]);out=[]
    for cell in cells:
        bb=bounds(cell)
        candidates=np.where((boxes[:,0]<=bb[2])&(boxes[:,2]>=bb[0])&(boxes[:,1]<=bb[3])&(boxes[:,3]>=bb[1]))[0]
        for index in candidates:
            poly=clip_triangle(cell,triangles[index])
            if poly is not None and abs(signed(poly))>1e-5:
                p=poly
                # OpenCV can repeat the first/last vertex on a shared edge.
                keep=np.linalg.norm(p-np.roll(p,1,axis=0),axis=1)>1e-4;p=p[keep]
                if len(p)>=3:out.append(p if signed(p)>0 else p[::-1])
    return out

def map_points(q,a,b,tris):
    result=np.zeros_like(q);covered=np.zeros(len(q),bool)
    for ids in tris:
        source=a[ids];bb=bounds(source)
        candidates=np.where((q[:,0]>=bb[0]-.002)&(q[:,0]<=bb[2]+.002)&(q[:,1]>=bb[1]-.002)&(q[:,1]<=bb[3]+.002)&~covered)[0]
        if not len(candidates):continue
        m=cv2.getAffineTransform(source,np.float32([[0,0],[1,0],[0,1]]))
        uv=np.c_[q[candidates],np.ones(len(candidates))]@m.T
        valid=(uv.min(axis=1)>=-1e-4)&(uv.sum(axis=1)<=1+1e-4)
        at=candidates[valid];v=uv[valid];delta=b[ids]-source
        result[at]=delta[0]+v[:,0,None]*(delta[1]-delta[0])+v[:,1,None]*(delta[2]-delta[0]);covered[at]=True
    if not covered.all():raise ValueError(('Uncovered mesh vertices',q[~covered][:10]))
    return result

def write_binary(prefix,data):
    raw=data.tobytes();compressed=gzip.compress(raw,compresslevel=9,mtime=0)
    name=f'{prefix}-{hashlib.sha256(compressed).hexdigest()[:12]}.bin.gz'
    (OUT/name).write_bytes(compressed)
    return {'file':name,'bytes':len(compressed),'decodedBytes':len(raw)}

def main():
    start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    # The original shoulder/wing must not participate in head interpolation.
    # Follow its observed upper feather boundary, rather than a horizontal
    # crop that accidentally includes and deforms large wing-feather markings.
    body_edge=np.float32([[0,555],[210,555],[260,535],[350,535],[450,550],[530,555],[600,515],[660,465],[715,436],[760,438],[810,459],[860,500],[950,555],[1163,555]])
    if NECK:
        # Keep the folded wing's own feather contour anchored, but DO NOT
        # extend its mask horizontally across the left neck/breast silhouette.
        # The old555px collar did exactly that and cut off oblique necks.
        body_edge=np.float32([[0,900],[210,900],[260,900],[350,900],[450,850],[530,650],[600,535],[660,480],[715,450],[760,450],[810,465],[860,510],[950,600],[1163,900]])
    edge_y=np.interp(np.arange(1163),body_edge[:,0],body_edge[:,1])
    body_weight=np.clip((np.arange(H)[:,None]-edge_y[None,:]+12)/12,0,1)
    body_weight=body_weight*body_weight*(3-2*body_weight)
    images=[im.copy() for im in IMAGES]
    neutral=images[0][:H].astype(np.float32)/255
    for im in images[1:]:
        source=im[:H].astype(np.float32)/255;t=body_weight[:,:,None]
        alpha=source[:,:,3:]*(1-t)+neutral[:,:,3:]*t
        rgb=(source[:,:,:3]*source[:,:,3:]*(1-t)+neutral[:,:,:3]*neutral[:,:,3:]*t)/np.maximum(alpha,1e-6)
        im[:H]=np.uint8(np.clip(np.concatenate([rgb,alpha],axis=2)*255+.5,0,255))
    # Pixel-edge coordinates, with shared lower neck fixed in every source.
    pts=[controls(name,im[:600],semantic=True) for name,im in zip(SOURCES,images)]
    if NECK:pts=[extend_controls(p,im) for p,im in zip(pts,images)]
    fixed=body_edge[1:-1]
    for i,p in enumerate(pts):
        # Silhouette samples on the static shoulder are correspondences to the
        # original body, not independent alpha-edge measurements of each pose.
        for k in range(36,36+2*len(SILHOUETTE_FRACTIONS)):
            x,y=p[k]
            if y>=np.interp(x,body_edge[:,0],body_edge[:,1]):p[k]=pts[0][k]
        pts[i]=np.vstack([p,fixed]).astype(np.float32)
    for p in pts:
        p[p[:,0]==1162,0]=1163;p[p[:,1]==H-1,1]=H
    pairs=sorted({tuple(sorted([a,b])) for tri in VIEW_TRIS for a,b in zip(tri,tri[1:]+tri[:1])})
    manual=json.loads((ROOT/'tools/owl_manual_features.json').read_text())['poses']
    detailed={i for i,name in enumerate(SOURCES) if all('pupilRing8' in eye for eye in manual.get(name,{}).get('eyes',[{}]))}
    eye_start=36+2*len(SILHOUETTE_FRACTIONS)
    pupil_vertices={eye_start+eye*25+17+k for eye in range(2) for k in range(8)}
    topologies={}
    for i,j in pairs:
        # Pupil contours are used only where BOTH source pupils were actually
        # observed and traced. Hidden pupils are not invented or forced into
        # a common eight-point shape. All pairs retain the eyelid/iris rims.
        active=np.array([k for k in range(len(pts[i])) if i in detailed and j in detailed or k not in pupil_vertices])
        checks=[pts[i]*(1-t)+pts[j]*t for t in np.linspace(0,1,9)]
        for t in [.5,0,1,.2,.4,.6,.8]:
            seed=pts[i]*(1-t)+pts[j]*t
            # cv2 Subdiv expects points strictly inside its bounds.
            from build_pose_field import triangles
            initial=active[np.asarray(triangles(seed[active],(0,0,1164,H+1)))].tolist()
            tr,folds=compatible(initial,seed,checks)
            if not folds:break
        if folds:
            bad=[]
            for k,q in enumerate(checks):
                v=q[np.array(tr)];a=v[:,1]-v[:,0];b=v[:,2]-v[:,0];area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
                for ids in np.array(tr)[area<-.001]:bad.append({'sample':k,'ids':ids.tolist(),'a':pts[i][ids].tolist(),'b':pts[j][ids].tolist()})
            debug=ROOT/'evidence/owl-diagonal-repair/fold-diagnostic.json';debug.write_text(json.dumps({'pair':[i,j],'folds':bad},indent=2))
            raise ValueError(('Invalid pair topology',i,j,folds))
        topologies[i,j]=topologies[j,i]=tr
    meshes=[];edges=[];data={}
    for i in range(len(SOURCES)):
        neighbors=sorted(j for a,j in topologies if a==i)
        cells=[np.float32([[0,0],[1163,0],[1163,H],[0,H]])]
        for j in neighbors:cells=overlay(cells,[pts[i][ids] for ids in topologies[i,j]])
        vertices=[];indices=[];lookup={}
        def vertex(p):
            key=tuple(np.round(p,4))
            if key not in lookup:lookup[key]=len(vertices);vertices.append(p)
            return lookup[key]
        for polygon in cells:
            ids=[vertex(p) for p in polygon]
            for n in range(1,len(ids)-1):
                if len({ids[0],ids[n],ids[n+1]})==3:indices.append([ids[0],ids[n],ids[n+1]])
        q=np.float32(vertices);ix=np.uint32(indices)
        area=sum(abs(signed(q[t])) for t in ix)
        if abs(area-1163*H)>.2:raise ValueError(('Incomplete conforming surface',i,area))
        flows={j:map_points(q,pts[i],pts[j],topologies[i,j]) for j in neighbors}
        data[i]=(q,ix,flows)
        meshes.append({'id':i,'vertexCount':len(q),'indexCount':ix.size,'positions':write_binary(f'mesh-{i}',q.astype('<f4')),'indices':write_binary(f'indices-{i}',ix.astype('<u4'))})
        for j,flow in flows.items():edges.append({'from':i,'to':j,**write_binary(f'exact-flow-{i}-{j}',flow.astype('<f4'))})
        print('source',i,'vertices',len(q),'triangles',len(ix),'coverage',area,flush=True)
    # Check the actual exported representation, including blends of two maps.
    failures=[];worst=1.;tested=0
    for ids in VIEW_TRIS:
        for a in range(13):
            for b in range(13-a):
                weights=np.float32([a,b,12-a-b])/12
                for slot,i in enumerate(ids):
                    if weights[slot]<.00001:continue
                    q,ix,flows=data[i];dest=q.copy()
                    for k,j in enumerate(ids):
                        if j!=i:dest+=flows[j]*weights[k]
                    v=dest[ix].astype(np.float64);base=q[ix].astype(np.float64)
                    cross=lambda p:(p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0])
                    areas=cross(v);baseareas=cross(base);negative=np.maximum(0,-areas*.5).sum()*weights[slot]
                    worst=min(worst,float(areas.min()));tested+=1
                    if negative>.01:failures.append({'views':ids,'weights':weights.tolist(),'source':i,'invertedArea':float(negative)})
    report={'representation':'pair-boundary-conforming source meshes','testedContributorPoses':tested,'worstSignedDoubleArea':worst,'significantInversions':failures,'thresholdWeightedSourcePixelsSquared':.01,'scope':'Finite geometry check, not visual approval'}
    evidence=ROOT/('evidence/owl-neck-continuity/conforming' if NECK else 'evidence/owl-diagonal-repair/conforming');evidence.mkdir(parents=True,exist_ok=True);(evidence/'geometry.json').write_text(json.dumps(report,indent=2))
    if failures:raise ValueError(('Unsafe intermediate geometry',len(failures),failures[:3]))
    views=[]
    for i,(name,pose,im) in enumerate(zip(SOURCES,POSES,images)):
        encoded=io.BytesIO();Image.fromarray(im[:H]).save(encoded,'WEBP',quality=97,method=6,exact=True)
        raw=encoded.getvalue();texture=f'view-{i}-{hashlib.sha256(raw).hexdigest()[:12]}.webp';(OUT/texture).write_bytes(raw)
        from build_smooth_field import STUDY
        views.append({'id':i,'name':name,'yaw':float(pose[0]),'pitch':float(pose[1]),'texture':texture,'bytes':len(raw),'source_sha256':hashlib.sha256(SOURCE_PATHS[name].read_bytes()).hexdigest(),'source_path':str(SOURCE_PATHS[name])})
    manifest={'version':5,'revision':'neck-continuity-2026-09-24' if NECK else 'diagonal-repair-2026-09-24','width':1163,'height':H,'views':views,'triangles':VIEW_TRIS,'meshes':meshes,'edges':edges,'floatEncoding':'float32-le-gzip','featherRefinement':False,'fixedBodyBoundary':body_edge.tolist(),'source_role':'17 full source poses plus prior up-right repair; lower body registered, not regenerated' if NECK else '17 original appearance poses plus 2 generated repair crops; no video frames; nominal angles'}
    if NECK:
        Image.fromarray(images[0][H:]).save(OUT/'body.webp','WEBP',lossless=True,method=6,exact=True)
        manifest.update(bodyTexture='/assets/owl/neck-candidate/body.webp',fixedBodyBlendWidth=12)
    tmp=OUT/'manifest.next.json';tmp.write_text(json.dumps(manifest,indent=2));tmp.replace(OUT/'manifest.json')
    print('FINISHED',time.monotonic()-start,flush=True)

if __name__=='__main__':main()
