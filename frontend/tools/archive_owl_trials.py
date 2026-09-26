"""Move unused generated surface outputs out of public; never delete sources."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIELD=ROOT/'public/assets/owl/smooth-field'
ARCHIVE=ROOT/'.cache/owl-smooth-field/retired'
manifest=json.loads((FIELD/'manifest.json').read_text())
used={'manifest.json'}|{v['texture'] for v in manifest['views']}|{e['file'] for e in manifest['edges']}
for mesh in manifest['meshes']:used|={mesh['positions']['file'],mesh['indices']['file']}
ARCHIVE.mkdir(parents=True,exist_ok=True)
rows=[]
for path in sorted(FIELD.iterdir()):
    if not path.is_file() or path.name in used:continue
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    target=ARCHIVE/f'{digest[:12]}-{path.name}'
    attempt=1
    while target.exists():
        target=ARCHIVE/f'{digest[:12]}-{attempt}-{path.name}';attempt+=1
    rows.append({'file':path.name,'sha256':digest,'bytes':path.stat().st_size,'recoverable_at':str(target)})
    path.rename(target)
report=ROOT/'evidence/owl-smooth-v2/retired-assets.json';previous=json.loads(report.read_text()) if report.exists() else [];report.write_text(json.dumps(previous+rows,indent=2))
print(f'Moved {len(rows)} generated trial files ({sum(r["bytes"] for r in rows):,} bytes) to {ARCHIVE}. Nothing deleted.')
