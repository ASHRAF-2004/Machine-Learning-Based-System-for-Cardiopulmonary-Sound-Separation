"""One bounded local interpolation check; no weights installed or downloaded."""
from pathlib import Path
import subprocess,os,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
OUT=ROOT/'evidence/owl-smooth-v2/neural-check';OUT.mkdir(parents=True,exist_ok=True)
vendor=STUDY/'feather-continuity/vendor/rife'
for name in ['neutral-original','yaw-minus15-pitch-plus9']:
    im=np.array(Image.open(STUDY/'assembled'/f'{name}.png').convert('RGBA'))[:600,128:896]
    a=im[:,:,3:]/255;rgb=np.uint8(im[:,:,:3]*a+np.array([228,237,245])*(1-a))
    rgb=np.pad(rgb,((0,8),(0,0),(0,0)),mode='edge');Image.fromarray(rgb).save(OUT/f'{name}.png')
start=time.monotonic()
cmd=[str(vendor/'rife-ncnn-vulkan'),'-0',str(OUT/'neutral-original.png'),'-1',str(OUT/'yaw-minus15-pitch-plus9.png'),'-o',str(OUT/'middle.png'),'-s','0.35','-m',str(vendor/'models/rife-v4.6'),'-g','0','-j','1:2:1']
result=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'OMP_NUM_THREADS':'2'},timeout=90)
(OUT/'run.log').write_text(result.stdout+result.stderr);print(result.returncode,time.monotonic()-start)
if result.returncode:raise SystemExit(result.returncode)
