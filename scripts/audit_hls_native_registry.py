"""Metadata-first native HLS registry; never opens T9-associated audio.

The frozen source CSV is read solely for exclusion/fold identity. The optional
header pass can open only the 100 native triplets whose BOTH families are in
the existing 86-source non-test allowlist. No sample decoding occurs here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import wave
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'research/manifests/hls_cmds_split_v1.csv'
ELIGIBLE = ROOT / '.local/training/stethofuse-tcn-v1/t7-small-seed20260928/eligible_split.csv'
FOLDS = ROOT / 'research/manifests/pre_t9_family_cv_v1.csv'
EXPECTED = {
    MANIFEST: '39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4',
    ELIGIBLE: '82e677af9f27256aa163b8aa80ca096874bc5cc37da10f29d029f7fee93999dd',
    FOLDS: '630bb9935f4720fbed66df6f1858d47f0561e89f4894fe7635ed24977e317e58',
}
SEED = 20260928


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def family_id(kind: str, family: str) -> str:
    return kind.lower() + ':' + re.sub(r'[^a-z0-9]+', '-', family.lower()).strip('-')


def canonical_wav_member(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return name.lower().endswith('.wav') and not any(
        x == '__MACOSX' or x.startswith('._') for x in parts)


def correspondence_pairs(hearts: set[str], lungs: set[str]) -> set[tuple[str, str]]:
    """Metadata-only 20% pair holdout, covering all eight heart/five lung families."""
    def key(kind: str, value: str) -> str:
        return hashlib.sha256(f'native-correspondence-v1:{SEED}:{kind}:{value}'.encode()).hexdigest()
    hs = sorted(hearts, key=lambda x: key('HS', x))
    ls = sorted(lungs, key=lambda x: key('LS', x))
    return {(heart, ls[index % len(ls)]) for index, heart in enumerate(hs)}


def build_registry(inspect_eligible_headers: bool = False) -> dict:
    for path, digest in EXPECTED.items():
        if sha256(path) != digest:
            raise ValueError(f'Frozen metadata identity changed: {path.relative_to(ROOT)}')
    frozen = read_csv(MANIFEST)
    allowed = read_csv(ELIGIBLE)
    folds = read_csv(FOLDS)
    if len(frozen) != 100 or len(allowed) != 86 or len(folds) != 86:
        raise ValueError('Unexpected source inventory counts')
    frozen_non_test = {(r['kind'], r['id'], r['sha256']) for r in frozen if r['split'] != 'test'}
    if frozen_non_test != {(r['kind'], r['id'], r['sha256']) for r in allowed}:
        raise ValueError('Non-test allowlist no longer exactly matches frozen partition')
    frozen_lookup = {(r['kind'], r['id']): r for r in frozen if r['split'] != 'test'}
    allowed = [{**frozen_lookup[(r['kind'], r['id'])], **r} for r in allowed]
    reserved = {kind: {r['family'] for r in frozen if r['kind'] == kind and r['split'] == 'test'}
                for kind in ('HS', 'LS')}
    non_test = {kind: {r['family'] for r in allowed if r['kind'] == kind} for kind in ('HS', 'LS')}
    if any(reserved[k] & non_test[k] for k in reserved):
        raise ValueError('A family crosses T9 and non-test partitions')
    fold_family = {(r['kind'], r['family']): r['holdout_fold'] for r in folds}
    if any(fold_family[(r['kind'], r['family'])] != r['holdout_fold'] for r in folds):
        raise ValueError('A family crosses grouped folds')
    pairs_holdout = correspondence_pairs(non_test['HS'], non_test['LS'])
    metadata_dir = ROOT / 'datasets/hls_cmds/metadata'
    mix = read_csv(metadata_dir / 'Mix.csv')
    individual = {kind: read_csv(metadata_dir / f'{kind}.csv') for kind in ('HS', 'LS')}
    archives = {}
    zip_members = {}
    for kind in ('HS', 'LS', 'Mix'):
        archive = ROOT / f'.local/ensemble/sources/{kind}-zenodo15376628.zip'
        with zipfile.ZipFile(archive) as stream:
            entries = {info.filename: info for info in stream.infolist()
                       if canonical_wav_member(info.filename)}
            zip_members[kind] = {name: {'uncompressed_bytes': info.file_size,
                                       'zip_crc32': f'{info.CRC:08x}'}
                                 for name, info in entries.items()}
        local_names = {f'{kind}/{p.name}' for p in (ROOT / f'datasets/hls_cmds/raw/{kind}').glob('*.wav')}
        if local_names != set(entries):
            raise ValueError(f'Local/official archive filename mismatch for {kind}')
        archives[kind] = {
            'path': str(archive.relative_to(ROOT)), 'wav_count': len(entries),
            'uncompressed_wav_bytes': sum(info.file_size for info in entries.values()),
            'local_filename_set_equal': True, 'resource_forks_excluded': True,
            'inspection': 'ZIP central directory only; no excluded audio member read',
        }
    if [archives[k]['wav_count'] for k in ('HS', 'LS', 'Mix')] != [50, 50, 435]:
        raise ValueError('Unexpected official release WAV counts')
    seen = set()
    rows = []
    for source in sorted(mix, key=lambda row: row['Mixed Sound ID']):
        mid, hid, lid = (source[k] for k in ('Mixed Sound ID', 'Heart Sound ID', 'Lung Sound ID'))
        if not re.fullmatch(r'M\d{4}', mid) or hid != 'H' + mid[1:] or lid != 'L' + mid[1:]:
            raise ValueError(f'Unexpected explicit ID mapping: {mid}, {hid}, {lid}')
        if {mid, hid, lid} & seen:
            raise ValueError('Native ID is not unique')
        seen.update((mid, hid, lid))
        hf, lf = source['Heart Sound Type'], source['Lung Sound Type']
        reasons = []
        for kind, family in (('HS', hf), ('LS', lf)):
            if family in reserved[kind]:
                reasons.append(f'T9_RESERVED_{kind}_FAMILY:{family}')
            elif family not in non_test[kind]:
                reasons.append(f'UNKNOWN_NON_TEST_{kind}_FAMILY:{family}')
        eligible = not reasons
        row = {
            'triplet_id': mid, 'mixture_id': mid, 'heart_reference_id': hid, 'lung_reference_id': lid,
            'mixture_file': f'datasets/hls_cmds/raw/Mix/{mid}.wav',
            'heart_reference_file': f'datasets/hls_cmds/raw/Mix/{hid}.wav',
            'lung_reference_file': f'datasets/hls_cmds/raw/Mix/{lid}.wav',
            'heart_family': hf, 'lung_family': lf,
            'heart_family_id': family_id('HS', hf), 'lung_family_id': family_id('LS', lf),
            'family_pair_id': family_id('HS', hf) + '|' + family_id('LS', lf),
            'recording_position': source['Location'], 'manikin_gender_label': source['Gender'],
            'mixture_filter_mode': None, 'heart_filter_mode': None, 'lung_filter_mode': None,
            'filter_mode_provenance': 'Not encoded per recording in release CSV; acquisition paper review required',
            'subject_id': None, 'underlying_playback_waveform_id': None,
            'eligible_non_test': eligible, 'exclusion_reasons': reasons,
            'existing_split_eligibility': 'NON_TEST_FAMILY_ELIGIBLE' if eligible else 'T9_FAMILY_SEALED_EXCLUDED',
            'correspondence_partition': ('heldout_pair' if (hf, lf) in pairs_holdout else 'fit_pair') if eligible else None,
            'eligible_training_folds': [f'f{i}' for i in range(1, 6)
                                       if eligible and fold_family[('HS', hf)] != f'f{i}'
                                       and fold_family[('LS', lf)] != f'f{i}'],
            'withheld_from_training_folds': [f'f{i}' for i in range(1, 6)
                                           if eligible and (fold_family[('HS', hf)] == f'f{i}'
                                                            or fold_family[('LS', lf)] == f'f{i}')],
            'standalone_non_test_same_family_ids': {
                'heart': sorted(r['id'] for r in allowed if r['kind'] == 'HS' and r['family'] == hf) if eligible else [],
                'lung': sorted(r['id'] for r in allowed if r['kind'] == 'LS' and r['family'] == lf) if eligible else [],
            },
            'standalone_non_test_same_family_gender_location_candidates': {
                'heart': sorted(r['id'] for r in allowed if r['kind'] == 'HS' and r['family'] == hf
                                and r['gender'] == source['Gender'] and r['location'] == source['Location']) if eligible else [],
                'lung': sorted(r['id'] for r in allowed if r['kind'] == 'LS' and r['family'] == lf
                               and r['gender'] == source['Gender'] and r['location'] == source['Location']) if eligible else [],
            },
            'files': {},
            'notes': ['CSV is explicit correspondence, not proof of synchronization or additivity.',
                      'Family exclusion is conservative because exact playback identity is unpublished.',
                      'Same-family/site standalone candidates are metadata matches, not waveform identity claims.'],
        }
        for role, ident in (('mixture', mid), ('heart', hid), ('lung', lid)):
            member = f'Mix/{ident}.wav'
            if member not in zip_members['Mix']:
                raise ValueError(f'Missing official archive entry: {member}')
            row['files'][role] = {
                'path': f'datasets/hls_cmds/raw/{member}', 'archive_member': member,
                **zip_members['Mix'][member], 'sha256': None, 'archive_bytes_match': None,
                'sample_rate': None, 'channels': None, 'bits_per_sample': None,
                'frames': None, 'duration_seconds': None, 'encoding': None,
                'audio_bytes_opened': False, 'samples_decoded': False,
            }
        rows.append(row)
    if len(rows) != 145 or sum(r['eligible_non_test'] for r in rows) != 100:
        raise ValueError('Native metadata counts changed')
    if inspect_eligible_headers:
        with zipfile.ZipFile(ROOT / archives['Mix']['path']) as archive:
            for row in rows:
                if not row['eligible_non_test']:
                    continue
                for file in row['files'].values():
                    payload = authorized_native_path(row, file['path']).read_bytes()
                    original = archive.read(file['archive_member'])
                    if original != payload:
                        raise ValueError(f'Eligible local file differs from official archive: {file["path"]}')
                    with wave.open(io.BytesIO(payload), 'rb') as wav:
                        info = {'sha256': hashlib.sha256(payload).hexdigest(), 'archive_bytes_match': True,
                                'sample_rate': wav.getframerate(), 'channels': wav.getnchannels(),
                                'bits_per_sample': 8 * wav.getsampwidth(), 'frames': wav.getnframes(),
                                'duration_seconds': wav.getnframes() / wav.getframerate(),
                                'encoding': wav.getcomptype(), 'audio_bytes_opened': True}
                    file.update(info)
    eligible_rows = [r for r in rows if r['eligible_non_test']]
    pair_counts = Counter(r['family_pair_id'] for r in eligible_rows)
    if len(pair_counts) != 40:
        raise ValueError('Unexpected eligible pair coverage')
    for partition in ('fit_pair', 'heldout_pair'):
        members = [r for r in eligible_rows if r['correspondence_partition'] == partition]
        if {r['heart_family'] for r in members} != non_test['HS'] or {r['lung_family'] for r in members} != non_test['LS']:
            raise ValueError('Correspondence partition does not preserve non-test family coverage')
    return {
        'schema_version': 1, 'dataset': 'HLS-CMDS', 'official_release_record': 'https://zenodo.org/records/15376628',
        'release_version': None, 'version_note': 'Record identity verified locally; official version label awaits original-source audit',
        'status': 'METADATA_AND_ELIGIBLE_HEADER_AUDIT' if inspect_eligible_headers else 'METADATA_ONLY',
        'seed': SEED, 'test_audio_access_allowed': False, 'samples_decoded': False,
        'metadata_inputs': {str(path.relative_to(ROOT)): sha256(path)
                            for path in [*EXPECTED, metadata_dir / 'Mix.csv', metadata_dir / 'HS.csv', metadata_dir / 'LS.csv']},
        'archives': archives,
        'counts': {'standalone_heart': 50, 'standalone_lung': 50, 'native_triplets': 145,
                   'native_mixtures': 145, 'native_heart_references': 145, 'native_lung_references': 145,
                   'all_wavs': 535, 'eligible_triplets': 100, 'excluded_triplets': 45,
                   'eligible_audio_files': 300, 'sealed_native_audio_files_unopened': 135,
                   'eligible_heart_families': 8, 'eligible_lung_families': 5, 'eligible_family_pairs': 40,
                   'unique_eligible_family_pairs_beyond_synthetic_cartesian_pool': 0},
        't9_exclusion': {'reserved_heart_families': sorted(reserved['HS']),
                         'reserved_lung_families': sorted(reserved['LS']),
                         'rule': 'Reject any triplet when EITHER source family is reserved or not in frozen non-test allowlist',
                         'excluded_audio_not_opened': True, 'test_metadata_used_only_for_exclusion': True},
        'correspondence_holdout': {
            'policy': 'Metadata-only SHA256 seed-order heart and lung families; one pair per ordered heart, lung round-robin',
            'hash_key': 'native-correspondence-v1:20260928:{HS_or_LS}:{family}',
            'heldout_pair_count': len(pairs_holdout), 'fit_pair_count': len(pair_counts) - len(pairs_holdout),
            'heldout_pairs': [{'heart_family': h, 'lung_family': l} for h, l in sorted(pairs_holdout)],
            'triplet_counts': dict(Counter(r['correspondence_partition'] for r in eligible_rows)),
            'fit_and_holdout_each_cover_all_8_heart_and_5_lung_families': True,
            'limitation': 'Held-out family pairs, not unseen constituent families or independent patients; acquisition-correction diagnostic only',
            'not_model_selection_fold_assignment': True,
        },
        'eligible_ids': [r['triplet_id'] for r in eligible_rows],
        'eligible_family_pair_counts': dict(sorted(pair_counts.items())),
        'standalone_non_test_family_counts': {kind: dict(sorted(Counter(r['family'] for r in allowed if r['kind'] == kind).items()))
                                             for kind in ('HS', 'LS')},
        'native_non_test_family_counts': {'HS': dict(sorted(Counter(r['heart_family'] for r in eligible_rows).items())),
                                         'LS': dict(sorted(Counter(r['lung_family'] for r in eligible_rows).items()))},
        'eligible_native_training_counts_by_fold': {f'f{i}': sum(f'f{i}' in r['eligible_training_folds'] for r in eligible_rows)
                                                   for i in range(1, 6)},
        'rows': rows,
    }


@lru_cache(maxsize=1)
def metadata_authorization() -> dict:
    """Re-derive the allowlist from pinned source/fold metadata, not caller flags."""
    for path, digest in EXPECTED.items():
        if sha256(path) != digest:
            raise ValueError(f'Frozen metadata changed: {path}')
    allowed = read_csv(ELIGIBLE)
    families = {k: {r['family'] for r in allowed if r['kind'] == k} for k in ('HS', 'LS')}
    fold_family = {(r['kind'], r['family']): r['holdout_fold'] for r in read_csv(FOLDS)}
    result = {}
    for r in read_csv(ROOT / 'datasets/hls_cmds/metadata/Mix.csv'):
        h, l = r['Heart Sound Type'], r['Lung Sound Type']
        if h in families['HS'] and l in families['LS']:
            result[r['Mixed Sound ID']] = (h, l, fold_family[('HS', h)], fold_family[('LS', l)])
    return result


def authorized_native_path(row: dict, path_value: str, fold: str | None = None) -> Path:
    """Reject excluded IDs before touching bytes; exact three-file allowlist only."""
    if row.get('eligible_non_test') is not True or row.get('exclusion_reasons'):
        raise ValueError('Native triplet is excluded by the T9/family seal')
    identity = metadata_authorization().get(row.get('triplet_id'))
    if identity is None or identity[:2] != (row['heart_family'], row['lung_family']):
        raise ValueError('Native triplet ID/families are not in independently verified metadata allowlist')
    if fold is not None:
        if fold not in {'f1', 'f2', 'f3', 'f4', 'f5'} or fold in identity[2:]:
            raise ValueError('Native triplet contains held-out fold family or fold is invalid')
    expected = {f'datasets/hls_cmds/raw/Mix/{prefix}{row["triplet_id"][1:]}.wav' for prefix in 'MHL'}
    if path_value not in expected:
        raise ValueError('Path is outside the explicit eligible triplet')
    path = ROOT / path_value
    if path.resolve() != path.absolute() or path.parent.resolve() != (ROOT / 'datasets/hls_cmds/raw/Mix').resolve():
        raise ValueError('Native path is not the exact local immutable source path')
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-eligible-headers', action='store_true')
    parser.add_argument('--output', default='research/manifests/hls_native_triplets_v1.json')
    parser.add_argument('--exclusions-output', default='research/manifests/hls_native_triplet_exclusions_v1.json')
    args = parser.parse_args()
    registry = build_registry(args.inspect_eligible_headers)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, indent=2, sort_keys=True) + '\n')
    exclusions = {'schema_version': 1, 'registry_path': str(output.relative_to(ROOT)), 'registry_sha256': sha256(output),
                  'test_audio_access_allowed': False, 'audio_bytes_opened': False,
                  'rows': [{key: row[key] for key in ('triplet_id', 'mixture_file', 'heart_reference_file',
                                                     'lung_reference_file', 'heart_family', 'lung_family', 'exclusion_reasons')}
                           for row in registry['rows'] if not row['eligible_non_test']]}
    (ROOT / args.exclusions_output).write_text(json.dumps(exclusions, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'registry': str(output.relative_to(ROOT)), 'sha256': sha256(output),
                      'counts': registry['counts'], 'correspondence_holdout': registry['correspondence_holdout'],
                      'fold_training_counts': registry['eligible_native_training_counts_by_fold']}, indent=2))


if __name__ == '__main__':
    main()
