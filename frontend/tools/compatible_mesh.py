"""Find a common, non-folding triangulation for corresponding source views."""
import numpy as np
def area(p):
    a,b=p[1]-p[0],p[2]-p[0]
    return a[0]*b[1]-a[1]*b[0]
def compatible(tris,target,sources):
    tris=[t if area(target[t])>0 else [t[0],t[2],t[1]] for t in tris]
    def bad(t):return sum(area(s[t])<.01 for s in sources)
    for _ in range(300):
        edges={}
        for i,t in enumerate(tris):
            for a,b in zip(t,t[1:]+t[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append(i)
        options=[]
        for (a,b),ids in edges.items():
            if len(ids)!=2:continue
            i,j=ids;c=next(v for v in tris[i] if v not in [a,b]);d=next(v for v in tris[j] if v not in [a,b])
            if c==d:continue
            ta=[c,d,a];tb=[d,c,b]
            if area(target[ta])<0:ta=ta[::-1];tb=tb[::-1]
            if min(area(target[ta]),area(target[tb]))<=.01:continue
            change=bad(tris[i])+bad(tris[j])-bad(ta)-bad(tb)
            if change>0:options.append((change,i,j,ta,tb))
        if not options:break
        _,i,j,ta,tb=max(options);tris[i],tris[j]=ta,tb
    return tris,sum(bad(t) for t in tris)
