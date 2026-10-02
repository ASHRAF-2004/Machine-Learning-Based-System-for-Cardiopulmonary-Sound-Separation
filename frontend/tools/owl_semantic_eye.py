"""Socket contours parameterized by lid arclength, not rays from the pupil.

The far eye's partly hidden pupil must not be the origin of a radial fan:
that fan turns the barely visible nasal edge into a large grey wedge.
All pixels still come from the complete source head; no eye overlays.
"""
import cv2
import numpy as np

def pupil_ring(image,center,inner):
    """Observed dark-pupil extent; constrained within the visible aperture.

    These are correspondence vertices on the full photograph, not eye art.
    There is no attempt to recover a pupil hidden by feathers.
    """
    center=np.asarray(center,dtype=float);inner=np.asarray(inner,dtype=float)
    points=[]
    for angle in np.arange(8)*np.pi/4+np.pi:
        direction=np.array([np.cos(angle),np.sin(angle)]);hits=[]
        for a,b in zip(inner,np.roll(inner,-1,axis=0)):
            m=np.column_stack([direction,a-b])
            if abs(np.linalg.det(m))<1e-7:continue
            radius,t=np.linalg.solve(m,a-center)
            if radius>0 and 0<=t<=1:hits.append(radius)
        limit=min(hits) if hits else 2
        radii=np.linspace(.1,max(.2,limit*.92),40)
        q=center[None,:]+radii[:,None]*direction
        xy=np.rint(q).astype(int);values=image[xy[:,1],xy[:,0],:3].max(axis=1)
        bright=np.where(values>100)[0]
        radius=radii[max(0,bright[0]-1)] if len(bright) else radii[-1]
        radius=np.clip(radius,limit*.12,limit*.92)
        points.append((center+direction*radius).tolist())
    return points

def contour_points(image,box,pupil=None,manual=None):
    if manual:
        # Fully occluded pupils provide no pupil correspondence. Use an
        # interior aperture vertex in that case, not an invented black disc.
        center=manual['pupil']['center']
        if center is None:center=np.mean(manual['inner'],axis=0).tolist()
        ring=manual.get('pupilRing8')
        if ring is None:ring=pupil_ring(image,center,manual['inner'])
        return [center]+manual['outer']+manual['inner']+ring
    x0,y0,x1,y1=box;left,top=max(0,x0-7),max(0,y0-7)
    rgb=image[top:y1+8,left:x1+8,:3].astype(np.float32)
    blue=(rgb[:,:,2]>rgb[:,:,0]*1.16)&(rgb[:,:,1]>rgb[:,:,0]*1.1)
    mask=np.uint8(blue|(rgb.max(axis=2)<105))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    selected=max(range(1,count),key=lambda k:np.sum(blue&(labels==k)))
    contour=max(cv2.findContours(np.uint8(labels==selected),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0],key=cv2.contourArea)
    poly=cv2.convexHull(contour)[:,0,:].astype(np.float64)+[left,top]
    # The upper and lower lid each get equal semantic sample counts from the
    # nasal to temporal corner; an occluded pupil cannot pull the samples away.
    # Use horizontal chords for all view orientations, not global pupil rays.
    xs=np.linspace(poly[:,0].min()+.4,poly[:,0].max()-.4,5)
    upper=[];lower=[]
    for x in xs:
        hits=[]
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if min(a[0],b[0])<=x<=max(a[0],b[0]) and abs(b[0]-a[0])>1e-6:
                hits.append(a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1]))
        upper.append([x,min(hits)]);lower.append([x,max(hits)])
    ring=np.array([np.mean([upper[0],lower[0]],axis=0),*upper[1:4],np.mean([upper[4],lower[4]],axis=0),*lower[3:0:-1]])
    # One pupil landmark, only when it is visible. Put it on the detected pupil,
    # never on a hard-coded iris-opening centre.
    if pupil is None:
        yy,xx=np.mgrid[:rgb.shape[0],:rgb.shape[1]]
        distance=cv2.distanceTransform(np.uint8(rgb.max(axis=2)<75),cv2.DIST_L2,5)
        ex,ey=(x0+x1)/2-left,(y0+y1)/2-top
        distance*=((xx-ex)/max(1,(x1-x0)*.40))**2+((yy-ey)/max(1,(y1-y0)*.36))**2<1
        if distance.max()>3:
            cy,cx=np.mean(np.argwhere(distance>distance.max()*.72),axis=0);pupil=np.array([cx+left,cy+top])
        else:pupil=ring.mean(axis=0)
    # Eight stable lid-arc landmarks on each side of the rim, matching the
    # manually inspected controls used for the two difficult diagonals.
    blue_xy=np.column_stack(np.where(blue)[::-1]).astype(np.int32)
    iris=cv2.convexHull(blue_xy)[:,0,:].astype(float)+[left,top]
    iris_center=iris.mean(axis=0);inner=[]
    for q in ring:
        direction=q-iris_center;hits=[]
        for a,b in zip(iris,np.roll(iris,-1,axis=0)):
            m=np.column_stack([direction,a-b])
            if abs(np.linalg.det(m))<1e-7:continue
            radius,t=np.linalg.solve(m,a-iris_center)
            if radius>0 and 0<=t<=1:hits.append(radius)
        inner.append(iris_center+direction*np.clip(min(hits) if hits else .82,.3,.96))
    return np.vstack([pupil,ring,inner,pupil_ring(image,pupil,inner)]).tolist()
