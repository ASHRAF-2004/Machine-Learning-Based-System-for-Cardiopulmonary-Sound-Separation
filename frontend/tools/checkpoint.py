"""Verify existing tracked implementation files remain byte-identical."""
from pathlib import Path
import subprocess,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[2]
FILE=ROOT/'frontend/evidence/implementation-baseline.json'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if '--verify' in sys.argv:
    baseline=json.loads(FILE.read_text());changed=[p for p,h in baseline['files'].items() if not (ROOT/p).exists() or digest(ROOT/p)!=h]
    print(json.dumps({'unchanged':not changed,'checked_files':len(baseline['files']),'changed':changed},indent=2));sys.exit(bool(changed))
else:
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    files={p:digest(ROOT/p) for p in paths if p and (ROOT/p).is_file()}
    FILE.parent.mkdir(parents=True,exist_ok=True);FILE.write_text(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'files':files},indent=2));print('Checkpointed',len(files),'existing tracked files')
