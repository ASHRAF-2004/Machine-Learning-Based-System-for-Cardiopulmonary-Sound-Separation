"""Reproducible, copy-only optimization of the supplied identity and existing frames.
No new artwork, feather editing, frame generation, model inference or source mutation.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import argparse, hashlib, json, shutil, subprocess, concurrent.futures, io, math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parents[1]
SOURCE=WORKSPACE/'StethoFuse-codex-package'
SITE=SOURCE/'website'
STUDY=SOURCE/'owl-3d-lab/frame-study'
SEQUENCE=STUDY/'feather-continuity/rife-exports/sequence.json'
DEST=ROOT/'public/assets'
EVIDENCE=ROOT/'evidence/assets'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def optimize_frame(row):
    src=STUDY/'feather-continuity'/row['file']
    out=DEST/'owl/frames'/f"head-{row['frame']:04d}.webp"
    if not out.exists():
        with Image.open(src) as im: im.save(out,'WEBP',quality=94,method=6,exact=True)
    return {'frame':row['frame'],'bytes':out.stat().st_size,'source_sha256':row['sha256'],'sha256':sha(out)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--samples-only',action='store_true');args=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True);(DEST/'owl/frames').mkdir(parents=True,exist_ok=True)
    manifest=json.loads(SEQUENCE.read_text())
    shutil.copy2(SITE/'StethoFuse_owl_logo.svg',DEST/'logo.svg')
    original=Image.open(SITE/'Owl.png').convert('RGBA')
    for width in [420,720,1163]:
        im=original.resize((width,round(original.height*width/original.width)),Image.Resampling.LANCZOS)
        im.save(DEST/f'owl-poster-{width}.webp',quality=94,method=6,exact=True)
    bg=Image.open(SITE/'Background.png').convert('RGB')
    for width in [800,1200,1800]:
        im=bg.resize((width,round(bg.height*width/bg.width)),Image.Resampling.LANCZOS)
        im.save(DEST/f'background-{width}.webp',quality=88,method=6)
    Image.open(STUDY/'exports/body-from-row600.png').save(DEST/'owl/body.webp',quality=94,method=6,exact=True)
    samples=[0,36,74,101,199,224,349,424,549,674,824,974,1124]
    rows=[manifest['rows'][n] for n in samples] if args.samples_only else manifest['rows']
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        stats=list(pool.map(optimize_frame,rows))
    checks=[]
    sheet=Image.new('RGB',(1200,len(samples)*155),'#eaf1f6');draw=ImageDraw.Draw(sheet)
    for i,n in enumerate(samples):
        row=manifest['rows'][n];src=Image.open(STUDY/'feather-continuity'/row['file']).convert('RGBA');dst=Image.open(DEST/'owl/frames'/f'head-{n:04d}.webp').convert('RGBA')
        a=np.asarray(src);b=np.asarray(dst);mask=a[:,:,3]>200;diff=(a[:,:,:3].astype(float)-b[:,:,:3].astype(float))[mask];mse=float(np.mean(diff**2));psnr=10*math.log10(255**2/mse) if mse else 100
        checks.append({'frame':n,'psnr_visible_rgb':round(psnr,2),'alpha_identical':bool(np.array_equal(a[:,:,3],b[:,:,3])),'before_bytes':row['bytes'],'after_bytes':(DEST/'owl/frames'/f'head-{n:04d}.webp').stat().st_size})
        for k,im in enumerate([src,dst]):
            crop=im.crop((255,20,780,150));sheet.paste(crop,(k*600+15,i*155+22),crop);draw.text((k*600+15,i*155+3),f"Frame {n} · {'SOURCE' if k==0 else 'WEBP Q94 · same native resolution'}",fill='#26394b')
    sheet.save(EVIDENCE/'frame-quality-comparison.jpg',quality=97)
    report={'source_sequence':str(SEQUENCE),'source_sequence_sha256':sha(SEQUENCE),'source_frames':1200,'source_frame_bytes':manifest['head_files_total_bytes'],'optimized_frames':len(stats),'optimized_frame_bytes':sum(s['bytes'] for s in stats),'dimensions':[1163,600],'quality':94,'checks':checks,'identity_assets':[{'source':str(SITE/name),'sha256':sha(SITE/name),'bytes':(SITE/name).stat().st_size} for name in ['Owl.png','Background.png','StethoFuse_owl_logo.svg']],'derivatives':[{'name':p.name,'bytes':p.stat().st_size} for p in DEST.glob('*.webp')]}
    (EVIDENCE/'optimization.json').write_text(json.dumps(report,indent=2))
    if not args.samples_only:
        # Small manifest; omit analysis payloads and paths into the source lab.
        (DEST/'owl/sequence.json').write_text(json.dumps({'width':1163,'height':1353,'headHeight':600,'count':1200,'routes':[r['label'] for r in manifest['routes']],'frameBytes':report['optimized_frame_bytes'],'frames':stats},separators=(',',':')))
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','identity_assets','derivatives']},indent=2))

if __name__=='__main__': main()
