"""Bounded public metadata-first acquisition; never imports or opens HLS data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.local/datasets'
SPR_COMMIT = 'bca1e51422a42a042441010081519610ef3845d0'
SEED = 20260928


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rank(value: str) -> str:
    return digest(f'{SEED}:{value}'.encode())


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f'Refusing to overwrite frozen metadata: {path}')
    if not path.exists():
        path.write_bytes(payload)


def fetch(url: str, path: Path, expected: str | None = None,
          git_blob: bool = False) -> dict:
    if urllib.parse.urlparse(url).hostname not in {'physionet.org', 'raw.githubusercontent.com'}:
        raise ValueError('Only explicitly approved official public download hosts')
    if not path.resolve().is_relative_to(DATA.resolve()):
        raise ValueError('Download destination must remain in ignored external data root')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        payload = path.read_bytes()
    else:
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'StethoFuse-public-data-audit/1'})
            with urllib.request.urlopen(request, timeout=60) as response:
                if any(x in response.url.lower() for x in ('login', 'signin', 'authorize')):
                    raise RuntimeError(f'AUTHENTICATION REQUIRED: {response.url}')
                payload = response.read(25_000_001)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise RuntimeError(f'AUTH/ACCESS CHECK REQUIRED: {url} HTTP{error.code}') from error
            raise
        if len(payload) > 25_000_000:
            raise RuntimeError('Bounded acquisition exceeded per-file limit')
    actual = (hashlib.sha1(f'blob {len(payload)}\0'.encode() + payload).hexdigest()
              if git_blob else digest(payload))
    if expected and actual != expected:
        raise RuntimeError(f'Official content digest mismatch: {url}')
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.part')
        temporary.write_bytes(payload)
        temporary.replace(path)
    return {'url': url, 'path': str(path.relative_to(ROOT)),
            'sha256': digest(payload), 'bytes': len(payload),
            'official_digest': expected, 'official_digest_kind': 'git_blob_sha1' if git_blob else 'sha256'}


def round_robin(groups: dict, n: int) -> list:
    queues = [deque(sorted(items, key=lambda x: rank(str(x))))
              for key, items in sorted(groups.items())]
    chosen = []
    while len(chosen) < n and any(queues):
        for queue in queues:
            if queue and len(chosen) < n:
                chosen.append(queue.popleft())
    return chosen


def circor_sample(pilot: bool = False) -> tuple[list[dict], dict]:
    base = DATA / 'circor-1.0.3/original'
    checks = dict((line.split()[1], line.split()[0])
                  for line in (base / 'SHA256SUMS.txt').read_text().splitlines())
    for filename in ('training_data.csv', 'LICENSE.txt'):
        if digest((base / filename).read_bytes()) != checks[filename]:
            raise RuntimeError('CirCor metadata checksum mismatch')
    rows = list(csv.DictReader((base / 'training_data.csv').open()))
    parents = {}

    def find(key):
        parents.setdefault(key, key)
        if parents[key] != key:
            parents[key] = find(parents[key])
        return parents[key]

    for row in rows:
        a = find(row['Patient ID'])
        other = row['Additional ID']
        if other not in ('', 'nan'):
            b = find(str(int(float(other))))
            parents[max(a, b)] = min(a, b)
    components = defaultdict(list)
    for row in rows:
        components[find(row['Patient ID'])].append(row)
    strata = defaultdict(list)
    for component, entries in components.items():
        row = min(entries, key=lambda r: rank(r['Patient ID']))
        strata[(row['Age'], row['Murmur'], row['Campaign'])].append(component)
    # Guarantee eight Unknown controls, then 32 known-status groups.
    unknown = {k: v for k, v in strata.items() if k[1] == 'Unknown'}
    known = {k: v for k, v in strata.items() if k[1] != 'Unknown'}
    selected = round_robin(known, 160) if pilot else round_robin(unknown, 8) + round_robin(known, 32)
    records = []
    for component in selected:
        entries = components[component]
        subject_ids = {r['Patient ID'] for r in entries}
        files = [p for p in checks if p.endswith('.wav') and Path(p).name.split('_')[0] in subject_ids]
        files.sort(key=rank)
        picked = []
        sites = set()
        for name in files:
            site = Path(name).stem.split('_')[1]
            if site not in sites:
                picked.append(name)
                sites.add(site)
            if len(picked) == 2:
                break
        for name in picked:
            row = next(r for r in entries if r['Patient ID'] == Path(name).stem.split('_')[0])
            metadata = {k: (None if v == 'nan' else v) for k, v in row.items()}
            records.append({'dataset_id': 'circor-1.0.3', 'subject_id': component,
                            'recording_id': Path(name).stem, 'metadata': metadata,
                            'remote_path': name, 'official_sha256': checks[name]})
    return records, checks


def spr_sample(pilot: bool = False) -> tuple[list[dict], dict]:
    tree = json.loads((DATA / 'sprsound/metadata/tree.json').read_text())
    if tree['sha'] != SPR_COMMIT or tree['truncated']:
        raise RuntimeError('Unexpected or truncated SPRSound pinned tree')
    files = {r['path']: r for r in tree['tree'] if r['type'] == 'blob'}
    subjects = defaultdict(list)
    for name, item in files.items():
        if not (name.startswith('BioCAS2022/train2022_wav/') and name.endswith('.wav')):
            continue
        subject, age, sex, site, number = Path(name).stem.split('_')
        if not subject:
            continue
        subjects[subject].append((name, float(age), sex, site))
    strata = defaultdict(list)
    for subject, items in subjects.items():
        age, sex = items[0][1:3]
        # Historical acquisition strata were frozen before waveform inspection.
        # Pairing/registry uses the corrected CirCor boundary (age12=Adolescent);
        # do not retrospectively redraw this candidate sample at that boundary.
        domain = 'Infant' if age <= 1 else ('Child' if age <= 12 else 'Adolescent')
        strata[(domain, sex)].append(subject)
    selected = round_robin(strata, 160 if pilot else 40)
    records = []
    for subject in selected:
        picked = []
        sites = set()
        for name, age, sex, site in sorted(subjects[subject], key=lambda r: rank(r[0])):
            if site in sites:
                continue
            picked.append((name, age, sex, site)); sites.add(site)
            if len(picked) == 2:
                break
        for name, age, sex, site in picked:
            records.append({'dataset_id': 'sprsound-biocas2022', 'subject_id': subject,
                            'recording_id': Path(name).stem,
                            'metadata': {'age_years': age, 'sex': 'Male' if sex == '0' else 'Female', 'site': site},
                            'remote_path': name, 'official_git_blob': files[name]['sha']})
    return records, files


def acquire(audio: bool, pilot: bool = False) -> None:
    hearts, checks = circor_sample(pilot)
    lungs, files = spr_sample(pilot)
    selected = hearts + lungs
    phase = 'pilot-acquisition-v1' if pilot else 'qualification-v1'
    plan_path = DATA / phase / 'sample_manifest.json'
    save_json(plan_path, {'seed': SEED, 'phase': phase if pilot else 'qualification_not_training',
                         'selection_before_audio_inspection': True, 'records': selected})
    tasks = []
    for row in selected:
        name = row['remote_path']
        if row['dataset_id'].startswith('circor'):
            extensions = ('.hea', '.tsv', '.wav') if audio else ('.hea', '.tsv')
            for suffix in extensions:
                path = str(Path(name).with_suffix(suffix))
                if path not in checks:
                    continue
                tasks.append(('https://physionet.org/files/circor-heart-sound/1.0.3/' + path,
                              DATA / 'circor-1.0.3/original' / path, checks[path], False))
        else:
            annotations = name.replace('train2022_wav', 'train2022_json').replace('.wav', '.json')
            paths = (annotations, name) if audio else (annotations,)
            for path in paths:
                tasks.append((f'https://raw.githubusercontent.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound/{SPR_COMMIT}/{path}',
                              DATA / 'sprsound/original' / path, files[path]['sha'], True))
    # Bound connections; on any access/auth failure terminate before project work resumes.
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda args: fetch(*args), tasks))
    save_json(DATA / phase / ('audio_receipts.json' if audio else 'metadata_receipts.json'), receipts)
    print(json.dumps({'heart_recordings': len(hearts), 'lung_recordings': len(lungs),
                      'download_files': len(receipts), 'bytes': sum(r['bytes'] for r in receipts),
                      'sample_manifest_sha256': digest(plan_path.read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', action='store_true', help='Explicit bounded audio acquisition')
    parser.add_argument('--pilot', action='store_true', help='Metadata-stratified 160-group candidate acquisition, not training')
    args = parser.parse_args()
    acquire(args.audio, args.pilot)
