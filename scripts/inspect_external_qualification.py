"""Bounded external-only signal review; descriptive, not automated purity approval."""
import json
from pathlib import Path

import subprocess
import numpy as np
from scipy.signal import spectrogram

from acquire_external_qualification import DATA, rank, save_json

base = DATA / 'qualification-v1'
rows = json.loads((base / 'registry-v2.json').read_text())
chosen = []
for kind in ('heart', 'lung'):
    candidates = sorted((r for r in rows if r['source_type'] == kind and not r['exclusion_reasons']),
                        key=lambda r: rank(r['recording_id']))
    chosen.extend(candidates[:3])
    controls = sorted((r for r in rows if r['source_type'] == kind and r['exclusion_reasons']),
                      key=lambda r: rank(r['recording_id']))
    chosen.extend(controls[:1])
images = []
for index, row in enumerate(chosen):
    path = Path(row['derived_path']).resolve()
    if not path.is_relative_to(DATA.resolve()) or row['dataset_id'].startswith('hls'):
        raise RuntimeError('Only explicit external sample derivations may be inspected')
    x = np.load(path, allow_pickle=False)
    start = row['valid_intervals_4k'][0][0] if row['valid_intervals_4k'] else 0
    x = x[start:start + 32000]
    f, t, p = spectrogram(x, 4000, nperseg=256, noverlap=192)
    db = 10*np.log10(p + 1e-14)
    pixels = (np.clip((db - db.max() + 60) / 60, 0, 1) * 255).astype(np.uint8)[::-1]
    ppm = base / f'spectrum-{index}.pgm'
    ppm.write_bytes(f'P5\n{pixels.shape[1]} {pixels.shape[0]}\n255\n'.encode() + pixels.tobytes())
    out = base / f'spectrum-{index}.png'
    label = f"{index}: {row['source_type']} | {row['recording_id']} | {row['family_id']} | 0-8s, top=2kHz bottom=0Hz"
    subprocess.run(['convert', str(ppm), '-resize', '960x160!', '-background', 'white',
                    '-fill', 'black', '-font', 'DejaVu-Sans', '-pointsize', '14',
                    '-gravity', 'South', '-splice', '0x25', '-annotate', '0', label, str(out)], check=True)
    images.append(str(out))
subprocess.run(['convert', *images, '-append', str(base / 'source_review.png')], check=True)
save_json(base / 'source_review_selection.json', [{'recording_id': r['recording_id'],
    'original_sha256': r['original_sha256'], 'exclusions': r['exclusion_reasons']} for r in chosen])
print(base / 'source_review.png')
