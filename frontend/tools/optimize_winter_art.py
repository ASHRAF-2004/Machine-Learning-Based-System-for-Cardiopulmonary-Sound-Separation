"""Create separate display-sized WebP copies, retaining generated RGBA originals."""
from pathlib import Path
import json, hashlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public/assets/winter'
OUT.mkdir(parents=True, exist_ok=True)
entries = []
for name, widths in [('feather', [240, 480]), ('collection', [360, 720])]:
    source = ROOT / f'assets/winter-glass/{name}-source.png'
    image = Image.open(source).convert('RGBA')
    for width in widths:
        copy = image.copy()
        copy.thumbnail((width, width * image.height // image.width), Image.Resampling.LANCZOS)
        target = OUT / f'{name}-{width}.webp'
        copy.save(target, 'WEBP', quality=90, method=6, alpha_quality=100)
        entries.append({'source': str(source.relative_to(ROOT)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'source_size': image.size, 'source_bytes': source.stat().st_size, 'source_alpha': image.getchannel('A').getextrema(), 'output': str(target.relative_to(ROOT)), 'size': copy.size, 'bytes': target.stat().st_size, 'decoded_rgba_bytes': copy.width * copy.height * 4})
(OUT / 'manifest.json').write_text(json.dumps(entries, indent=2))
print(json.dumps(entries, indent=2))
