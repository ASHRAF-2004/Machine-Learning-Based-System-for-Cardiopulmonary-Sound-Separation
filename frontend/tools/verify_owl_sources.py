"""Verify original identities and account for only currently used surface data."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parents[1]/'StethoFuse-codex-package/owl-3d-lab/frame-study'
FIELD=ROOT/'public/assets/owl/smooth-field'
m=json.loads((FIELD/'manifest.json').read_text())
sources=[]
checkpoint=ROOT/'evidence/owl-diagonal-repair/checkpoint/manifest.json'
original={v['name']:v['source_sha256'] for v in json.loads(checkpoint.read_text())['views']} if checkpoint.exists() else {}
for v in m['views']:
    p=Path(v['source_path']) if v.get('source_path') else STUDY/'assembled'/f'{v["name"]}.png';digest=hashlib.sha256(p.read_bytes()).hexdigest()
    sources.append({'path':str(p),'sha256':digest,'unchanged':digest==v['source_sha256'],'matchesPreRepairCheckpoint':digest==original[v['name']] if v['name'] in original else None})
assert all(s['unchanged'] for s in sources)
assert all(s['matchesPreRepairCheckpoint'] is not False for s in sources)
files=[FIELD/'manifest.json']+[FIELD/v['texture'] for v in m['views']]+[FIELD/e['file'] for e in m['edges']]
for mesh in m['meshes']:files.extend([FIELD/mesh['positions']['file'],FIELD/mesh['indices']['file']])
record={'sources':sources,'manifestVersion':m['version'],'requiredSurfaceFiles':len(files),'requiredSurfaceDiskBytes':sum(p.stat().st_size for p in files),'rgbaSourceTextureBytes':len(m['views'])*1163*600*4,'decodedFlowBytes':sum(e['decodedBytes'] for e in m['edges']),'decodedGeometryBytes':sum(x['positions']['decodedBytes']+x['indices']['decodedBytes'] for x in m['meshes']),'protected':[]}
for p,expected in [(ROOT/'public/assets/owl/body.webp','20daac5bc64d22d4e833756eacb69be4ee101bf8df03d969689cc1ff57909a47'),(ROOT/'public/assets/owl-poster-720.webp','03fe188788f1b6fb7309cc1b73b68d6f6f134f15397ed572f91bb52dc34096f8')]:
    digest=hashlib.sha256(p.read_bytes()).hexdigest();record['protected'].append({'path':str(p),'sha256':digest,'expected':expected,'unchanged':digest==expected})
assert all(p['unchanged'] for p in record['protected'])
(ROOT/'evidence/owl-diagonal-repair/source-verification.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2))
