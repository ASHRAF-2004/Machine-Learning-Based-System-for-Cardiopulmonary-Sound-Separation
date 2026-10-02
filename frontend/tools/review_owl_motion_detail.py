"""Consecutive, un-interpolated frames from the real browser canvas recording."""
from pathlib import Path
import json,cv2,numpy as np,sys
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]/'evidence/owl-smooth-v2'/(sys.argv[1] if len(sys.argv)>1 else 'browser-review')
samples=json.loads((ROOT/'actual-draw-samples.json').read_text())
cap=cv2.VideoCapture(str(ROOT/'actual-canvas-motion.webm'));fps=cap.get(cv2.CAP_PROP_FPS)
targets=[(9,5),(-10,-7)]
chosen=[]
for target in targets:
 candidates=[(abs(s['yaw']-target[0])+abs(s['pitch']-target[1]),i,s) for i,s in enumerate(samples) if i>100 and abs(s['yaw']-samples[i-1]['yaw'])>.08]
 _,index,s=min(candidates);chosen.append((round((s['time']-samples[0]['time'])/1000*fps),target))
frames={};k=0
while True:
 ok,f=cap.read()
 if not ok:break
 if any(start<=k<start+12 for start,_ in chosen):frames[k]=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB))
 k+=1
cap.release()
for start,target in chosen:
 sheet=Image.new('RGB',(4*330,3*285),'#e8f1f7');d=ImageDraw.Draw(sheet)
 for n in range(12):
  im=frames[start+n].crop((115,15,435,265));x=(n%4)*330;y=(n//4)*285;sheet.paste(im,(x,y+25));d.text((x+5,y+7),f'Frame {start+n} / {(start+n)/fps:.3f}s',fill='#223b50')
 sheet.save(ROOT/f'consecutive-{target[0]}-{target[1]}.png')
print('Decoded actual recording:',k,'frames;',fps,'fps. No synthesized frames.')
