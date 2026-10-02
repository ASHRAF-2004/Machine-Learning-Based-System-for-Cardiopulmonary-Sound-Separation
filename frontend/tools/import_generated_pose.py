"""Non-destructively assemble one generated pose onto the approved fixed body."""
from pathlib import Path
import argparse,hashlib,json,sys
from datetime import datetime,timezone
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
sys.path.insert(0,str(STUDY/'tools'))
from assemble_poses import read_rgba,estimate_translation,assemble,sha256,SOURCE,SOURCE_SHA256

def main():
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('name');args=p.parse_args()
    source_path=Path(args.input).resolve();source=read_rgba(SOURCE);raw=read_rgba(source_path)
    if sha256(SOURCE)!=SOURCE_SHA256:raise ValueError('Approved source changed')
    size_adjustment=None
    if raw.shape!=source.shape:
        # Image editing can return a canvas that is one transparent edge pixel
        # short. Preserve every source pixel and centre-pad only that harmless
        # one-pixel discrepancy; never rescale photographic detail.
        dh=source.shape[0]-raw.shape[0];dw=source.shape[1]-raw.shape[1]
        if abs(dh)>1 or abs(dw)>1 or dh<0 or dw<0:
            raise ValueError(f'Expected {source.shape}, got {raw.shape}')
        canvas=np.zeros_like(source)
        top=dh//2;left=dw//2
        canvas[top:top+raw.shape[0],left:left+raw.shape[1]]=raw
        size_adjustment={'method':'transparent centre padding; no resampling','source_shape':list(raw.shape),'target_shape':list(source.shape),'top':top,'left':left}
        raw=canvas
    aligned,registration=estimate_translation(source,raw);result=assemble(source,aligned)
    out=ROOT/'evidence/owl-continuous-atlas/generated';out.mkdir(parents=True,exist_ok=True)
    raw_out=out/f'{args.name}-raw.png';assembled_out=out/f'{args.name}.png'
    Image.fromarray(raw).save(raw_out);Image.fromarray(result).save(assembled_out)
    assert np.array_equal(result[600:],source[600:])
    record={'created_utc':datetime.now(timezone.utc).isoformat(),'name':args.name,'nominal_angles':'prompt targets, not measured 3D angles','generated_source':str(source_path),'generated_sha256':sha256(source_path),'approved_reference':str(SOURCE),'approved_sha256':SOURCE_SHA256,'raw_copy':str(raw_out),'assembled':str(assembled_out),'assembled_sha256':sha256(assembled_out),'fixed_body_from_row':600,'body_pixel_identical':True,'size_adjustment':size_adjustment,'registration':registration,'visual_acceptance':'requires inspection'}
    (out/f'{args.name}.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if __name__=='__main__':main()
