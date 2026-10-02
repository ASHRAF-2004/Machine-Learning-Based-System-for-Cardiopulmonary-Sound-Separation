"""Offline, manifest-first data contracts for StethoFuse TCN training.

This module intentionally has no application/database imports. Test audio is
never decoded by the training/validation helpers.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import wave
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "research/manifests/hls_cmds_split_v1.csv"
DATA_ROOT = ROOT / "datasets/hls_cmds/raw"
SAMPLE_RATE = 4000
CROP_SAMPLES = 32000
MANIFEST_SHA256 = "39d5456477b07772bdc24b86ee73dee17c44fd1e0837b62b96eab8c19a1b65e4"


@dataclass(frozen=True)
class Source:
    kind: str
    id: str
    family: str
    split: str
    sha256: str
    path: Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(path: Path = DEFAULT_MANIFEST) -> list[Source]:
    # Metadata is parsed and the requested split filtered before any WAV opens.
    rows = list(csv.DictReader(path.open(newline="")))
    required = {"kind", "id", "family", "sha256", "split"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Training manifest is empty or missing required columns")
    return [Source(row["kind"], row["id"], row["family"], row["split"],
                   row["sha256"], DATA_ROOT / row["kind"] / f"{row['id']}.wav")
            for row in rows]


def audit_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, object]:
    sources = read_manifest(path)
    manifest_hash = sha256_file(path)
    if manifest_hash != MANIFEST_SHA256:
        raise ValueError(f"Frozen source manifest hash changed: {manifest_hash}")
    if len(sources) != 100 or len({(s.kind, s.id) for s in sources}) != 100:
        raise ValueError("Expected 100 unique frozen source IDs")
    if len({s.sha256 for s in sources}) != 100:
        raise ValueError("Exact duplicate source hashes detected")
    family_splits: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        family_splits[f"{source.kind}:{source.family}"].add(source.split)
    if any(len(splits) != 1 for splits in family_splits.values()):
        raise ValueError("A source family crosses frozen partitions")
    counts = Counter((s.kind, s.split) for s in sources)
    expected = {("HS", "development"): 36, ("HS", "validation"): 9,
                ("HS", "test"): 5, ("LS", "development"): 36,
                ("LS", "validation"): 5, ("LS", "test"): 9}
    if dict(counts) != expected:
        raise ValueError(f"Frozen split counts differ: {dict(counts)}")
    # Hash and inspect WAV headers in all splits; do not decode test samples.
    headers: dict[str, dict[str, object]] = {}
    for source in sources:
        if not source.path.is_file() or sha256_file(source.path) != source.sha256:
            raise ValueError(f"Missing or changed source bytes: {source.kind}/{source.id}")
        with wave.open(str(source.path), "rb") as wav:
            header = {"sample_rate_hz": wav.getframerate(), "channels": wav.getnchannels(),
                      "sample_width_bytes": wav.getsampwidth(), "frames": wav.getnframes()}
        if header != {"sample_rate_hz": SAMPLE_RATE, "channels": 1,
                      "sample_width_bytes": 2, "frames": 60000}:
            raise ValueError(f"Unexpected source format: {source.kind}/{source.id} {header}")
        headers[f"{source.kind}/{source.id}"] = header
        # Development and validation PCM are decoded to establish finite samples;
        # test remains locked and is not waveform-inspected.
        if source.split != "test":
            audio = read_source(source)
            if audio.size != 60000 or not np.isfinite(audio).all():
                raise ValueError(f"Invalid waveform: {source.kind}/{source.id}")
            if audio.size < CROP_SAMPLES:
                raise ValueError(f"Source too short for crop: {source.kind}/{source.id}")
    return {"schema_version": 1, "manifest_sha256": manifest_hash,
            "source_count": len(sources), "split_counts":
            {f"{kind}_{split}": count for (kind, split), count in sorted(counts.items())},
            "family_count": len(family_splits), "family_split_leakage": 0,
            "exact_duplicate_hashes": 0, "sample_rate_hz": SAMPLE_RATE,
            "test_audio_decoded": False, "headers": headers}


def read_source(source: Source) -> np.ndarray:
    if source.split == "test":
        raise ValueError("Locked test audio cannot be decoded in T0-T8")
    with wave.open(str(source.path), "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"Expected mono 4-kHz PCM16: {source.kind}/{source.id}")
        raw = wav.readframes(wav.getnframes())
    values = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if not np.isfinite(values).all():
        raise ValueError(f"Nonfinite decoded waveform: {source.kind}/{source.id}")
    return values


def make_mixture(heart: np.ndarray, lung: np.ndarray, relative_db: float,
                 heart_start: int = 0, lung_start: int = 0,
                 crop_samples: int = CROP_SAMPLES) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Mix at requested lung-to-heart power level, then apply one shared gain."""
    h0 = np.asarray(heart[heart_start:heart_start + crop_samples], dtype=np.float32)
    l0 = np.asarray(lung[lung_start:lung_start + crop_samples], dtype=np.float32)
    if h0.shape != (crop_samples,) or l0.shape != (crop_samples,):
        raise ValueError("Requested crop is outside source bounds")
    rms_h = float(np.sqrt(np.mean(h0.astype(np.float64) ** 2)))
    rms_l = float(np.sqrt(np.mean(l0.astype(np.float64) ** 2)))
    if min(rms_h, rms_l) < 1e-6 or not (-10 <= relative_db <= 10):
        raise ValueError("Invalid/silent source or relative level outside frozen range")
    lung_gain = rms_h / rms_l * 10 ** (relative_db / 20)
    l_scaled = l0 * np.float32(lung_gain)
    preliminary = h0 + l_scaled
    peak = max(float(np.max(np.abs(h0))), float(np.max(np.abs(l_scaled))),
               float(np.max(np.abs(preliminary))))
    if not math.isfinite(peak) or peak <= 0:
        raise ValueError("Invalid mixture peak")
    common = np.float32(0.95 / peak)
    targets = np.stack((h0 * common, l_scaled * common)).astype(np.float32)
    mixture = targets.sum(axis=0, dtype=np.float32)
    if not np.isfinite(targets).all() or np.max(np.abs(targets).max(axis=0)) > 0.950001:
        raise ValueError("Shared scaling failed finite/peak contract")
    if not np.allclose(mixture, targets[0] + targets[1], rtol=0, atol=1e-6):
        raise ValueError("Mixture additivity contract failed")
    return mixture, targets, {"relative_lung_to_heart_db": float(relative_db),
                              "lung_gain": float(lung_gain), "shared_gain": float(common),
                              "mixture_peak": float(np.max(np.abs(mixture)))}


def _rng(*key: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(list(key))))


def training_epoch(sources: list[Source], epoch: int, seed: int = 20260928) -> list[dict[str, object]]:
    development = [s for s in sources if s.split == "development"]
    families: dict[str, dict[str, list[Source]]] = {"HS": defaultdict(list), "LS": defaultdict(list)}
    for source in development:
        families[source.kind][source.family].append(source)
    for by_family in families.values():
        for items in by_family.values():
            items.sort(key=lambda s: s.id)
    pairs = [(h, l) for h in sorted(families["HS"]) for l in sorted(families["LS"])]
    schedule = [pair for pair in pairs for _ in range(24)]
    _rng(seed, epoch, 0).shuffle(schedule)
    queues: dict[tuple[str, str], deque[Source]] = {}
    for kind_index, kind in enumerate(("HS", "LS")):
        for family_index, family in enumerate(sorted(families[kind])):
            rows = families[kind][family].copy()
            _rng(seed, epoch, kind_index, family_index, 2).shuffle(rows)
            queues[(kind, family)] = deque(rows)
    consumed = Counter()
    recipes = []
    for draw_index, (hf, lf) in enumerate(schedule):
        selected = []
        for kind, family in (("HS", hf), ("LS", lf)):
            queue = queues[(kind, family)]
            if not queue:
                rows = families[kind][family].copy()
                _rng(seed, epoch, 0 if kind == "HS" else 1,
                     sorted(families[kind]).index(family), 2 + consumed[(kind, family)]).shuffle(rows)
                queue.extend(rows)
            selected.append(queue.popleft())
            consumed[(kind, family)] += 1
        rng = _rng(seed, epoch, draw_index, 1)
        hstart, lstart = (int(rng.integers(0, 28001)), int(rng.integers(0, 28001)))
        level = float(rng.uniform(-10.0, 10.0))
        recipes.append({"draw_index": draw_index, "heart_id": selected[0].id,
                        "heart_family": hf, "lung_id": selected[1].id,
                        "heart_sha256": selected[0].sha256,
                        "lung_sha256": selected[1].sha256,
                        "lung_family": lf, "heart_start": hstart,
                        "lung_start": lstart, "relative_lung_to_heart_db": level,
                        "seed_key": [seed, epoch, draw_index, 1]})
    return recipes


def frozen_validation_recipes(sources: list[Source]) -> list[dict[str, object]]:
    validation = [s for s in sources if s.split == "validation"]
    hearts = sorted((s for s in validation if s.kind == "HS"), key=lambda s: s.id)
    lungs = sorted((s for s in validation if s.kind == "LS"), key=lambda s: s.id)
    recipes = []
    for hi, heart in enumerate(hearts):
        h = read_source(heart)
        for li, lung in enumerate(lungs):
            l = read_source(lung)
            for level in (-10, -5, 0, 5, 10):
                _, _, gains = make_mixture(h, l, level, crop_samples=60000)
                recipe = {"heart_id": heart.id, "heart_sha256": heart.sha256,
                          "heart_family": heart.family, "lung_id": lung.id,
                          "lung_sha256": lung.sha256, "lung_family": lung.family,
                          "heart_start": 0, "lung_start": 0,
                          "relative_lung_to_heart_db": level,
                          "seed_key": [20260928, hi, li, level], **gains}
                recipe["network_shared_peak_scale"] = recipe["mixture_peak"]
                recipe["network_normalization"] = "divide mixture and both targets by mixture peak"
                recipe["mixture_id"] = hashlib.sha256(
                    json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
                recipes.append(recipe)
    return recipes


def materialize_recipe(recipe: dict[str, object], sources: list[Source],
                       cache: dict[tuple[str, str], np.ndarray] | None = None
                       ) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Create one permitted train/development or validation sample and receipt."""
    cache = cache if cache is not None else {}
    ids = (("HS", str(recipe["heart_id"])), ("LS", str(recipe["lung_id"])))
    selected = []
    for kind, source_id in ids:
        source = next((s for s in sources if s.kind == kind and s.id == source_id), None)
        if source is None or source.split == "test":
            raise ValueError("Recipe references an absent or locked test source")
        key = (kind, source_id)
        if key not in cache:
            cache[key] = read_source(source)
        selected.append(cache[key])
    mixture, targets, gains = make_mixture(
        selected[0], selected[1], float(recipe["relative_lung_to_heart_db"]),
        int(recipe["heart_start"]), int(recipe["lung_start"]),
        int(recipe.get("crop_samples", CROP_SAMPLES)))
    details = {**recipe, **gains}
    details["network_shared_peak_scale"] = float(np.max(np.abs(mixture)))
    details["network_normalization"] = "divide mixture and both targets by mixture peak"
    details["mixture_sha256"] = hashlib.sha256(
        mixture.astype("<f4", copy=False).tobytes()).hexdigest()
    details["mixture_id"] = hashlib.sha256(
        json.dumps(details, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    return mixture, targets, details


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
