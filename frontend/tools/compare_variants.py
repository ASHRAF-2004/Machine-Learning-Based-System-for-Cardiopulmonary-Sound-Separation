"""Evaluate 480/720/native frame resolution, WebP and AVIF; preserve source files."""
from pathlib import Path
from PIL import Image,ImageDraw
import io,json,time
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study/feather-continuity'
manifest=json.loads((STUDY/'rife-exports/sequence.json').read_text())
out=ROOT/'evidence/assets';out.mkdir(parents=True,exist_ok=True)
sheet=Image.new('RGB',(1240,810),'#ecf3f8');draw=ImageDraw.Draw(sheet);stats=[]
for row_index,frame in enumerate([36,199,549]):
    original=Image.open(STUDY/manifest['rows'][frame]['file']).convert('RGBA')
    for col,(width,fmt) in enumerate([(480,'WEBP'),(720,'WEBP'),(1163,'WEBP'),(1163,'AVIF')]):
        im=original.resize((width,round(600*width/1163)),Image.Resampling.LANCZOS)
        encoded=io.BytesIO();started=time.perf_counter()
        try:im.save(encoded,fmt,quality=94 if fmt=='WEBP' else 90,method=6)
        except Exception as error:stats.append({'frame':frame,'width':width,'format':fmt,'unavailable':str(error)});continue
        elapsed=time.perf_counter()-started;encoded.seek(0);decoded=Image.open(encoded).convert('RGBA').resize((1163,600),Image.Resampling.LANCZOS)
        crop=decoded.crop((280,30,590,250));sheet.paste(crop,(col*310,row_index*270+34),crop)
        draw.text((col*310+7,row_index*270+8),f'{frame} · {width}px {fmt} · {len(encoded.getvalue())//1024}KB',fill='#294052')
        stats.append({'frame':frame,'width':width,'format':fmt,'bytes':len(encoded.getvalue()),'encode_seconds':round(elapsed,3)})
sheet.save(out/'resolution-format-comparison.png');(out/'resolution-format-comparison.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
