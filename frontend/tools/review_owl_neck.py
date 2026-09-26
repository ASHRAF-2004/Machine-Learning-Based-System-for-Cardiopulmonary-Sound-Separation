"""Contact sheets from actual browser captures; never synthetic pose frames."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/owl-neck-continuity'
for group,ids in [('sweep',range(6)),('diagonals',[6,7,8,9])]:
    sheet=Image.new('RGB',(1200,350*len(ids)),'#eaf1f6');d=ImageDraw.Draw(sheet)
    for row,i in enumerate(ids):
        for col,variant in enumerate(['before','after']):
            im=Image.open(OUT/variant/f'pose-{i:02d}.png').convert('RGBA')
            native=im.resize((1163,1353),Image.Resampling.LANCZOS)
            crop=native.crop((150,220,950,870));crop.thumbnail((570,315))
            x=col*600;y=row*350;sheet.paste(crop,(x,y+30),crop)
            pose=json.loads((OUT/variant/'results.json').read_text())['holds'][i]['pose']
            d.text((x+12,y+10),f'{variant.upper()} {pose} - same browser scale',fill='#172e42')
    sheet.save(OUT/f'{group}-before-after.png')
# Direct pixel evidence for the constant lower body in the new renderer.
lower=[]
for p in sorted((OUT/'after').glob('pose-*.png')):
    a=np.array(Image.open(p).convert('RGBA'));start=int(np.ceil(a.shape[0]*920/1353))
    assert np.count_nonzero(a[:,:,3]>240)>100000, f'Blank or invalid capture: {p}'
    lower.append(a[start:])
diff=[int(np.max(np.abs(a.astype(int)-lower[0].astype(int)))) for a in lower]
(OUT/'body-pixel-check.json').write_text(json.dumps({'crop_from_native_y':920,'max_channel_delta_per_pose':diff,'all_identical':all(v==0 for v in diff)},indent=2))
print('saved sheets; body identical',all(v==0 for v in diff))
