"""Verify originals, default-field isolation and the candidate payload."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/owl-neck-continuity'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'assets/owl-neck-continuity/registered/manifest.json').read_text())
source_checks=[{'name':v['name'],'unchanged':sha(Path(v['source']))==v['source_sha256']} for v in m['views']]
field=ROOT/'public/assets/owl/neck-candidate';f=json.loads((field/'manifest.json').read_text())
files=[field/'manifest.json',field/'body.webp']+[field/v['texture'] for v in f['views']]+[field/v['file'] for v in f['edges']]+[field/v[k]['file'] for v in f['meshes'] for k in ['positions','indices']]
record={'sourceChecks':source_checks,'normalFieldManifestUnchanged':sha(ROOT/'public/assets/owl/smooth-field/manifest.json')==sha(OUT/'checkpoint/manifest.json'),'originalBodyUnchanged':sha(ROOT/'public/assets/owl/body.webp')=='20daac5bc64d22d4e833756eacb69be4ee101bf8df03d969689cc1ff57909a47','posterUnchanged':sha(ROOT/'public/assets/owl-poster-720.webp')=='03fe188788f1b6fb7309cc1b73b68d6f6f134f15397ed572f91bb52dc34096f8','pointerControllerUnchanged':sha(ROOT/'src/components/Owl.tsx')=='a09b65352eaec52064f840d46eb1a9fdf86d95489d3b36a9254972ac44ae3480','candidateViews':len(f['views']),'surfaceHeight':f['height'],'bytesIncludingBody':sum(p.stat().st_size for p in files),'decodedSourceRGBABytes':len(f['views'])*f['width']*f['height']*4}
assert all(v['unchanged'] for v in source_checks)
assert all(record[k] for k in ['normalFieldManifestUnchanged','originalBodyUnchanged','posterUnchanged','pointerControllerUnchanged'])
generated=ROOT/'assets/owl-neck-continuity/generated-full-down-left.png';im=Image.open(generated)
record['generatedValidationOnly']={'path':str(generated),'sha256':sha(generated),'size':im.size,'mode':im.mode,'usedInRenderer':False}
(OUT/'verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
