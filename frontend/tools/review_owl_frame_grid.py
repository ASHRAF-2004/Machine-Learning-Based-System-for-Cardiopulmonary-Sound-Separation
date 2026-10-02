"""Label every sampled rendered pose. Does not infer visual PASS from metrics."""
from pathlib import Path
import sys,json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'evidence/owl-diagonal-repair'/sys.argv[1]
poses=json.loads((folder/'poses.json').read_text())
for batch in range((len(poses)+11)//12):
 sheet=Image.new('RGB',(1600,1320),'#e8f1f7');d=ImageDraw.Draw(sheet)
 for j,(yaw,pitch) in enumerate(poses[batch*12:(batch+1)*12]):
  i=batch*12+j;im=Image.open(folder/f'pose-{i:03d}.png').convert('RGBA').crop((170,0,870,580));im.thumbnail((390,400))
  x=j%4*400;y=j//4*440;sheet.paste(im,(x,y+28),im);d.text((x+8,y+8),f'{i}: yaw {yaw:+.2f} pitch {pitch:+.2f}',fill='#263d49')
 sheet.save(folder/f'study-{batch:02d}.png')
