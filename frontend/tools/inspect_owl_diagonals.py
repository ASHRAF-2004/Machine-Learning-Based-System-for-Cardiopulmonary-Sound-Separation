"""Evidence only: source landmarks and real-browser diagonal captures."""
import sys,json
from pathlib import Path
from PIL import Image,ImageDraw
from owl_correspondence import STUDY,ANNOTATIONS,controls
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/owl-smooth-v2'/ (sys.argv[1] if len(sys.argv)>1 else 'diagonal-before')
OUT.mkdir(parents=True,exist_ok=True)
names=['neutral-original','yaw-plus15-pitch0','yaw-plus15-pitch-plus9','yaw-plus30-pitch-plus18','yaw0-pitch-plus9','yaw-minus15-pitch-minus9','yaw-minus30-pitch-minus18','yaw0-pitch-minus9']
sheet=Image.new('RGB',(1280,len(names)*200),'#dce7ef');d=ImageDraw.Draw(sheet)
for n,name in enumerate(names):
 im=Image.open(STUDY/'assembled'/f'{name}.png').convert('RGBA');p=controls(name,np.asarray(im)[:600]);q=im.copy();dr=ImageDraw.Draw(q)
 for x,y in p:dr.ellipse((x-2,y-2,x+2,y+2),fill='red')
 boxes=ANNOTATIONS[name]['detection_evidence']['blue_iris_boxes_xyxy']
 for eye,(x0,y0,x1,y1) in enumerate(boxes):
  cx,cy=(x0+x1)//2,(y0+y1)//2
  for anno,img in enumerate([im,q]):
   crop=img.crop((cx-65,cy-50,cx+65,cy+50)).resize((260,200))
   sheet.paste(crop,((eye*2+anno)*280,n*200),crop)
 d.text((1120,n*200+8),name.replace('-','\n'),fill='#263b4a')
sheet.save(OUT/'source-eye-landmarks.png')
files=sorted(OUT.glob('pose-*-all.png'))
if files:
 sheet=Image.new('RGB',(1320,((len(files)+2)//3)*430),'#e8f1f7');d=ImageDraw.Draw(sheet)
 for i,f in enumerate(files):
  im=Image.open(f).crop((260,0,940,540));im.thumbnail((435,390))
  x,y=(i%3)*440,(i//3)*430;sheet.paste(im,(x,y+25));d.text((x+8,y+7),f.stem,fill='#203d50')
 sheet.save(OUT/'diagonals.png')
