"""Read-only identity/animation verification; writes a fresh report, never sources."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/winter-glass'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
originals = json.loads((ROOT / 'evidence/assets/optimization.json').read_text())['identity_assets']
checks = [{'path': row['source'], 'sha256': sha(Path(row['source'])),
           'unchanged': sha(Path(row['source'])) == row['sha256']} for row in originals]
checks.append({'path': 'public/assets/logo.svg', 'sha256': sha(ROOT / 'public/assets/logo.svg'),
               'unchanged': sha(ROOT / 'public/assets/logo.svg') == originals[2]['sha256']})
with tarfile.open(OUT / 'checkpoint/frontend-before.tar.gz') as archive:
    for name in ['src/components/Owl.tsx', 'src/components/owlCanvasSurface.ts', 'src/brand.ts']:
        before = hashlib.sha256(archive.extractfile(name).read()).hexdigest()
        checks.append({'path': name, 'sha256': sha(ROOT / name), 'unchanged': sha(ROOT / name) == before})
registered = json.loads((ROOT / 'assets/owl-neck-continuity/registered/manifest.json').read_text())
for row in registered['views']:
    checks.append({'path': row['source'], 'sha256': sha(Path(row['source'])),
                   'unchanged': sha(Path(row['source'])) == row['source_sha256']})
field = ROOT / 'public/assets/owl/neck-candidate'
manifest = json.loads((field / 'manifest.json').read_text())
files = [field/'manifest.json', field/'body.webp'] + [field/v['texture'] for v in manifest['views']]
files += [field/e['file'] for e in manifest['edges']]
files += [field/m[k]['file'] for m in manifest['meshes'] for k in ['positions', 'indices']]
record = {'checks': checks, 'allUnchanged': all(x['unchanged'] for x in checks),
          'approvedField': {'views': len(manifest['views']), 'files': len(files),
                            'diskBytesIncludingBody': sum(p.stat().st_size for p in files),
                            'sourceRGBAMemory': len(manifest['views'])*manifest['width']*manifest['height']*4},
          'note': 'Only owlSurface.ts default field selection was promoted; controller, Canvas fallback, artwork and brand configuration unchanged.'}
(OUT / 'preservation.json').write_text(json.dumps(record, indent=2))
print(json.dumps({'allUnchanged': record['allUnchanged'], 'checks': len(checks), 'field': record['approvedField']}, indent=2))
assert record['allUnchanged']
