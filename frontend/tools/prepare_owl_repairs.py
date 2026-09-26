"""Register two built-in image-edit results; preserve original body/source files.

Generated crops use the exact (180,0,820,560) edit-target framing. They are
resampled once to that crop and padded on a transparent native canvas, then
the existing renderer's original-body boundary owns the shoulder and feet.
"""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
sys.path.insert(0,str(STUDY/'tools'))
from annotate_pose_landmarks import estimate
OUT=ROOT/'assets/owl-repairs/2026-09-24'
original=Image.open(STUDY/'assembled/neutral-original.png').convert('RGBA')
records=[]
for name,file,yaw,pitch in [('repair-up-right','up-right-generated.png',7.5,4.5),('repair-down-left','down-left-generated.png',-7.5,-4.5)]:
    path=OUT/file;crop=Image.open(path).convert('RGBA').resize((640,560),Image.Resampling.LANCZOS)
    image=original.copy();image.paste((0,0,0,0),(0,0,1163,560));image.paste(crop,(180,0))
    dest=OUT/f'{name}.png';image.save(dest)
    landmarks,evidence=estimate(image)
    records.append({'name':name,'yaw':yaw,'pitch':pitch,'file':dest.name,'source':file,'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'crop':[180,0,820,560],'generatedSize':Image.open(path).size,'landmarks_xy':landmarks,'detection_evidence':evidence,'role':'built-in imagegen corrected intermediate head; original remains identity reference','approval':'candidate, pending assembled visual review'})
(OUT/'manifest.json').write_text(json.dumps({'views':records},indent=2))
print(json.dumps(records,indent=2))
