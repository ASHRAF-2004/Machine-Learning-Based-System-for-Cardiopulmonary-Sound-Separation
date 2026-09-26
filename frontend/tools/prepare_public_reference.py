"""Encode the supplied login artwork without changing its pixels or source files."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / 'ChatGPT Image Sep 24, 2026, 01_44_30 PM.png'
OUT = ROOT / 'public/assets/public-reference'
OUT.mkdir(parents=True, exist_ok=True)
image = Image.open(SOURCE).convert('RGB')
image.save(OUT / 'login-reference.webp', lossless=True, method=6)
assert Image.open(OUT / 'login-reference.webp').convert('RGB').tobytes() == image.tobytes()
plate = ROOT / 'assets/public-reference/login-backplate.png'
for width in (800, 1536):
    with Image.open(plate) as im:
        im.convert('RGB').resize((width, round(width * im.height / im.width)), Image.Resampling.LANCZOS).save(OUT / f'lake-{width}.webp', quality=88, method=6)
files = [SOURCE, plate, *sorted(OUT.glob('*.webp'))]
manifest = {
    'reference': str(SOURCE),
    'referencePixels': 'Lossless RGB copy. SVG mask includes only the original owl and a small margin of scenery; all baked UI is excluded. Mask blending ends outside the owl feathers.',
    'backplate': 'Built-in image_gen cleanup of the supplied reference. UI and owl removed; missing scenery reconstructed. Original owl pixels overlay it on authentication pages. Landscape is a close reconstruction, not pixel-identical.',
    'files': [{ 'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'dimensions': list(Image.open(p).size) } for p in files],
}
(ROOT / 'assets/public-reference/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
