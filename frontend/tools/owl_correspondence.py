"""Pixel correspondences for the existing owl source poses.

These are image-space constraints, not a recovered 3D model. Pairwise topology
and the actual browser output must be inspected before accepting a new source.
"""
from pathlib import Path
import json
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/"StethoFuse-codex-package/owl-3d-lab/frame-study"
W,H=1163,600
SILHOUETTE_FRACTIONS=np.linspace(.025,1,24)
ANNOTATIONS={r["pose"]:r for r in json.loads((STUDY/"evidence/landmarks.json").read_text())["poses"]}

def eye_contour(image,box,pupil=None):
    """Observed pupil centre + outer socket rim, not an iris bounding ellipse.

    Dark lids remain part of the same complete head image. This only locates
    corresponding geometry; it neither pastes in an eye nor erases its rim.
    """
    x0,y0,x1,y1=box
    left,top=max(0,x0-9),max(0,y0-9)
    rgb=image[top:y1+10,left:x1+10,:3].astype(np.float32)
    yy,xx=np.mgrid[:rgb.shape[0],:rgb.shape[1]]
    blue=(rgb[:,:,2]>rgb[:,:,0]*1.16)&(rgb[:,:,1]>rgb[:,:,0]*1.1)
    dark=rgb.max(axis=2)<115
    mask=np.uint8(blue|dark)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    selected=max(range(1,count),key=lambda k:np.sum(blue&(labels==k)))
    contour=max(cv2.findContours(np.uint8(labels==selected),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],key=cv2.contourArea)
    hull=cv2.convexHull(contour);opening=np.zeros_like(mask);cv2.fillConvexPoly(opening,hull,1)
    # Rim shadows are excluded from the pupil-centre estimate. In a heavily
    # occluded far eye use the visible opening's centre instead of inventing
    # a hidden round pupil.
    distance=cv2.distanceTransform(np.uint8((rgb.max(axis=2)<80)&(opening>0)),cv2.DIST_L2,5)
    ex,ey=(x0+x1)/2-left,(y0+y1)/2-top
    interior=((xx-ex)/max(1,(x1-x0)*.36))**2+((yy-ey)/max(1,(y1-y0)*.30))**2<1
    distance*=interior
    if distance.max()>4 and (x1-x0)>28:
        cy,cx=np.mean(np.argwhere(distance>distance.max()*.72),axis=0)
    else:
        moments=cv2.moments(hull);cx=moments['m10']/moments['m00'];cy=moments['m01']/moments['m00']
    if pupil is not None:cx,cy=pupil[0]-left,pupil[1]-top
    points=[[cx+left,cy+top]]
    polygon=hull[:,0,:].astype(np.float64)
    blue_points=np.column_stack(np.where(blue&(opening>0)&(rgb[:,:,2]>75)&((rgb[:,:,2]-rgb[:,:,0])>25))[::-1]).astype(np.int32)
    iris=cv2.convexHull(blue_points)[:,0,:].astype(np.float64)
    def radius_at(poly,direction):
        hits=[]
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            mat=np.column_stack([direction,a-b])
            if abs(np.linalg.det(mat))<1e-8:continue
            radius,t=np.linalg.solve(mat,a-[cx,cy])
            if radius>0 and -.0001<=t<=1.0001:hits.append(radius)
        return min(hits) if hits else None
    inner=[]
    for angle in np.linspace(0,2*np.pi,16,endpoint=False):
        direction=np.array([np.cos(angle),np.sin(angle)])
        radius=radius_at(polygon,direction)
        if radius is None:raise ValueError(('Eye contour intersection',box,angle))
        q=np.array([cx,cy])+direction*radius
        points.append([q[0]+left,q[1]+top])
        # Constrain both sides of the dark rim. Matching only its outer hull
        # let differently thick lids create a second crescent during blending.
        inner_radius=radius_at(iris,direction)
        inner_radius=np.clip(inner_radius if inner_radius is not None else radius*.82,radius*.30,max(radius*.31,radius-.8))
        q=np.array([cx,cy])+direction*inner_radius
        inner.append([q[0]+left,q[1]+top])
    points.extend(inner)
    return points

def controls(name,image,semantic=False):
    r=ANNOTATIONS[name];p=[]
    manual=json.loads((Path(__file__).with_name('owl_manual_features.json')).read_text())['poses'] if semantic else {}
    # The full image boundary and the lower neck never move.
    for x in np.linspace(0,W-1,9):p.extend([[x,0],[x,H-1],[x,560]])
    for y in [90,210,350,460]:p.extend([[0,y],[W-1,y]])
    # Corresponding silhouette samples anchor width without cropping feather tips.
    top=int(np.where((image[:,:,3]>160).any(axis=1))[0][0])
    xs=np.where(image[top+2,:,3]>160)[0]
    p.append([float((xs[0]+xs[-1])/2),top+2])
    for f in (SILHOUETTE_FRACTIONS if semantic else [.06,.14,.27,.42,.63,.82,1]):
        y=round(top+(500-top)*f)
        xs=np.where(image[y,:,3]>160)[0]
        p.extend([[float(xs[0]),y],[float(xs[-1]),y]])
    # In these two oblique up-right views the visible pupil is partly hidden
    # behind the facial disc. Opening centroid != pupil centre. These observed
    # pixel landmarks were checked on enlarged source crops, not invented eyes.
    pupil_overrides={'yaw-plus15-pitch-plus9':(641.5,140.),'yaw-plus30-pitch-plus18':(646.,132.)}
    for eye,box in enumerate(r['detection_evidence']['blue_iris_boxes_xyxy']):
        if semantic:
            from owl_semantic_eye import contour_points
            annotated=manual.get(name,{}).get('eyes')
            p.extend(contour_points(image,box,pupil_overrides.get(name) if eye==1 else None,annotated[eye] if annotated else None))
        else:p.extend(eye_contour(image,box,pupil_overrides.get(name) if eye==1 else None))
    bx0,by0,bx1,by1=r['detection_evidence']['dark_beak_box_xyxy']
    dark=np.uint8(np.max(image[by0:by1,bx0:bx1,:3],axis=2)<155)
    count,labels,stats,_=cv2.connectedComponentsWithStats(dark)
    mask=np.uint8(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA])))
    # A shadow on a neighbouring feather can be connected to the beak mask
    # elsewhere yet separated by pale feathers on this scanline. Follow the
    # connected beak run upward from its tip instead of taking the rightmost
    # shadow pixel across that gap (which used to drag neck vertices sideways).
    previous=None
    for row in range(mask.shape[0]-1,round(mask.shape[0]*.55)-1,-1):
        xs=np.where(mask[row]>0)[0]
        if not len(xs):continue
        runs=np.split(xs,np.where(np.diff(xs)>1)[0]+1)
        if previous is None:chosen=max(runs,key=len)
        else:chosen=min(runs,key=lambda q:max(0,previous[0]-q[-1],q[0]-previous[-1])+.02*abs(q.mean()-previous.mean()))
        mask[row]=0;mask[row,chosen]=1;previous=chosen
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
    if semantic:
        manual=json.loads((Path(__file__).with_name('owl_manual_features.json')).read_text())['poses']
        feature=manual.get(name,{})
        if 'beak' in feature:
            b=feature['beak'];p[-19:]=[b['base'],b['tip']]+[v for pair in zip(b['left'],b['right']) for v in pair]+b['axis']
        neutral=np.float32(manual['neutral-original']['throat'])
        if 'throat' in feature:collar=np.float32(feature['throat'])
        else:
            # Broad anatomical bands; no individual feather identity inferred.
            # Jaw movement dissipates through the collar before the shoulder.
            tip=np.float32(r['landmarks_xy']['beak_tip'])
            delta=tip-np.float32(ANNOTATIONS['neutral-original']['landmarks_xy']['beak_tip'])
            collar=neutral.copy();factor=np.r_[np.exp(-((neutral[:5,0]-498)/115)**2)*.8+.12,np.exp(-((neutral[5:,0]-498)/150)**2)*.10]
            collar+=delta[None,:]*factor[:,None]
        # A bowed head brings its chin close to the breast. The second band
        # must remain below the ruff, rather than crossing it during pitch.
        for k in range(1,5):collar[k,0]=max(collar[k,0],collar[k-1,0]+18)
        collar[5:,1]=np.maximum(collar[5:,1],np.interp(collar[5:,0],collar[:5,0],collar[:5,1])+24)
        p.extend(collar.tolist())
    return np.float32(p)

def triangulate(points):
    sub=cv2.Subdiv2D((0,0,W,H))
    for point in points:sub.insert(tuple(map(float,point)))
    tris=[]
    for tri in sub.getTriangleList().reshape(-1,3,2):
        ids=[int(np.argmin(np.sum((points-p)**2,axis=1))) for p in tri]
        if len(set(ids))==3 and all(np.linalg.norm(points[i]-p)<.1 for i,p in zip(ids,tri)):tris.append(ids)
    return tris
