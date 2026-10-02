"""Conservative sampled text contrast against actual glyph-hidden browser pixels.
This is a bounded inspection, not a complete WCAG/accessibility certification.
"""
import json,re
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]/'evidence/winter-glass/quality'
data=json.loads((ROOT/'metrics.json').read_text())
def luminance(rgb):
    rgb=np.asarray(rgb)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    return np.sum(linear*np.array([.2126,.7152,.0722]),axis=-1)
results=[]
for page in data['contrast']:
    pixels=np.asarray(Image.open(ROOT/(page['name']+'-background.png')).convert('RGB'))
    for row in page['text']:
        x,y,w,h=[row['rect'][k] for k in ['x','y','width','height']]
        bg=pixels[max(0,int(y)):min(pixels.shape[0],int(y+h)+1),max(0,int(x)):min(pixels.shape[1],int(x+w)+1)]
        if not bg.size:continue
        color=[float(v) for v in re.findall(r'[\d.]+',row['color'])]
        fg=np.array(color[:3]);alpha=color[3] if len(color)>3 else 1
        a=luminance(bg);b=luminance(fg*alpha+bg*(1-alpha));ratio=(np.maximum(a,b)+.05)/(np.minimum(a,b)+.05)
        threshold=3 if row['fontSize']>=24 or row['fontSize']>=18.667 and row['fontWeight']>=700 else 4.5
        results.append({'page':page['name'],**row,'minimumRatio':round(float(ratio.min()),3),'threshold':threshold,'status':'PASS' if ratio.min()>=threshold else 'FAIL'})
report={'method':'Minimum contrast across glyph-hidden screenshot pixels inside visible text Range rectangles at DPR1. Composited backgrounds include actual gradients/art/glass; no certification of unmeasured routes, states, placeholders, focus indicators or icon contrast.', 'results':results,'failures':[r for r in results if r['status']=='FAIL']}
(ROOT/'contrast.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'measurements':len(results),'failures':report['failures']},indent=2))
