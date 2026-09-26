"""Read-only contact sheets of EVERY source and close crops, not a PASS test."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
OUT=ROOT/'evidence/owl-diagonal-repair/source-audit'
OUT.mkdir(parents=True,exist_ok=True)
names=['neutral-original']+sorted(p.stem for p in (STUDY/'assembled').glob('*.png') if p.stem!='neutral-original')
records=[]
for batch in range(3):
 sheet=Image.new('RGB',(1536,1080),'#e8f1f7');d=ImageDraw.Draw(sheet)
 for i,name in enumerate(names[batch*6:(batch+1)*6]):
  im=Image.open(STUDY/'assembled'/f'{name}.png').convert('RGBA')
  crop=im.crop((160,0,900,590));crop.thumbnail((500,470))
  x=(i%3)*512;y=(i//3)*540
  sheet.paste(crop,(x,y+34),crop);d.text((x+8,y+12),name,fill='#263b4a')
  records.append({'name':name,'dimensions':im.size})
 sheet.save(OUT/f'all-sources-{batch}.png')
for name in ['neutral-original','yaw-plus15-pitch-plus9','yaw-plus30-pitch-plus18','yaw-minus15-pitch-minus9','yaw-minus30-pitch-minus18']:
 im=Image.open(STUDY/'assembled'/f'{name}.png').convert('RGBA')
 crop=im.crop((170,0,880,600));bg=Image.new('RGBA',crop.size,'#e8f1f7');bg.alpha_composite(crop);bg.convert('RGB').save(OUT/f'{name}-head.png')
(OUT/'inventory.json').write_text(json.dumps(records,indent=2))
for n in range(2):
 path=ROOT/'evidence/owl-diagonal-repair/native-before'/f'pose-{n:03d}.png'
 if path.exists():Image.open(path).crop((180,0,820,560)).save(OUT/f'repair-target-{n}.png')
Image.open(STUDY/'assembled/neutral-original.png').crop((180,0,820,560)).save(OUT/'original-head-reference.png')
