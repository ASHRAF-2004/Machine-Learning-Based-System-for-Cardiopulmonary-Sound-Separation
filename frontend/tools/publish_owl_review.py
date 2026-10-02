"""Promote only the validated candidate's referenced files; preserve old assets.

No source image or page files are changed. The old manifest is checkpointed
once; the new manifest is atomically published after its files are copied.
"""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'public/assets/owl/diagonal-candidate'
target=ROOT/'public/assets/owl/smooth-field'
manifest=json.loads((source/'manifest.json').read_text())
assert manifest['version']==5 and len(manifest['views'])==19
files=[v['texture'] for v in manifest['views']]+[e['file'] for e in manifest['edges']]
files += [m[k]['file'] for m in manifest['meshes'] for k in ['positions','indices']]
backup=ROOT/'evidence/owl-diagonal-repair/checkpoint/manifest-before-publish.json'
if not backup.exists():shutil.copy2(target/'manifest.json',backup)
for name in files:
    assert Path(name).name==name
    data=(source/name).read_bytes()
    if (target/name).exists():assert (target/name).read_bytes()==data
    else:shutil.copy2(source/name,target/name)
    assert hashlib.sha256((target/name).read_bytes()).digest()==hashlib.sha256(data).digest()
tmp=target/'manifest.next.json';shutil.copy2(source/'manifest.json',tmp);tmp.replace(target/'manifest.json')
print(f'Published {len(files)} files + manifest; previous manifest and all old files retained.')
