from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/owl-diagonal-repair'
sheet=Image.new('RGB',(1600,1400),'#e8f1f7');d=ImageDraw.Draw(sheet)
for row,(pose,box) in enumerate([(1,(325,105,715,295)),(2,(360,90,750,280)),(6,(205,270,810,550)),(7,(205,280,810,560))]):
 for col,layer in enumerate(['all','0','1','2']):
  path=OUT/'before'/f'pose-{pose:02d}-{layer}.png'
  if not path.exists():continue
  im=Image.open(path).crop(box);im.thumbnail((395,290))
  x=col*400;y=row*350;sheet.paste(im,(x,y+35));d.text((x+8,y+12),f'pose {pose} / contributor {layer}',fill='#243b49')
sheet.save(OUT/'donors.png')
