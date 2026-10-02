"""Lossless format copies of supplied comps; imagery is framed in SVG at runtime.

No owl pixels are regenerated, cut out, repainted or replaced. The only generated
asset is a separate, text-free background inpaint, documented in the manifest.
"""
from pathlib import Path
from PIL import Image
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/ashraf/Downloads/StethoFuse_updated_20')
OUT = ROOT / 'public/assets/reference-match'
ARCHIVE = ROOT / 'assets/reference-match'
OUT.mkdir(parents=True, exist_ok=True)
ARCHIVE.mkdir(parents=True, exist_ok=True)
files = {
    'dashboard': '04_frosted_ensemble_processing_dashboard.png',
    'collection': '06_stethofuse_winter_research_dashboard.png',
    'recording-collection': '05_stethofuse_winter_processing_history.png',
    'ensemble': '09_stethofuse_ensemble_configuration_dashboard.png',
    'assigned': '13_frosted_winter_assignment_dashboard.png',
    'shared': '19_stethofuse_shared_workspace_dashboard.png',
    'settings': '20_stethofuse_winter_appearance_settings.png',
    'utility': '11_stethofuse_frosted_403_private_access_page.png',
}
manifest = {'source': str(SOURCE), 'method': 'Unchanged source pixels in lossless WebP; SVG viewBox framing in ReferenceArt.tsx. Not screenshots used in place of interactive UI.', 'assets': []}
for name, filename in files.items():
    source = SOURCE / filename
    im = Image.open(source).convert('RGB')
    dest = OUT / f'{name}.webp'
    im.save(dest, 'WEBP', lossless=True, method=6)
    reopened = Image.open(dest).convert('RGB')
    assert reopened.tobytes() == im.tobytes(), f'Pixel change: {name}'
    manifest['assets'].append({'name': name, 'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'size': im.size, 'source_bytes': source.stat().st_size, 'output_bytes': dest.stat().st_size, 'pixel_identical': True})
archived_background = ARCHIVE / 'mountain-background-inpaint.png'
background = archived_background if archived_background.exists() else Path('/home/ashraf/.codex/generated_images/01a0a32e-37dc-7190-831f-d5213428fcc5/exec-458a203a-1d5d-4f7d-a641-7e013dfbadeb.png')
if background != archived_background:
    shutil.copy2(background, archived_background)
im = Image.open(background).convert('RGB')
for width in (800, 1536):
    export = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
    export.save(OUT / f'mountains-{width}.webp', 'WEBP', quality=91, method=6)
manifest['background'] = {'source': str(ARCHIVE / 'mountain-background-inpaint.png'), 'role': 'Background reconstruction of scenery obscured by UI; NOT an exact recovered original.', 'tool': 'built-in image_gen', 'reference': files['assigned'], 'prompt': 'Remove interface, text, logo and panels only. Preserve jagged snowy mountain, pine forest, right snowy trees, icy colour and diffuse light. Reconstruct scenery hidden by overlays. No owl, lake, folders or typography.'}
(ARCHIVE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
