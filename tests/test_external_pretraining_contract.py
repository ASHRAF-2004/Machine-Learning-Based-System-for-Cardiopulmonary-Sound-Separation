"""One bounded synthetic schedule/mixing test, with no training or real audio."""
import hashlib

import numpy as np

from scripts.train_external_pretraining import (
    AudioCache, external_holdout, hierarchy, materialize, normalize_registry, recipe_schedule,
)


def test_age_subject_schedule_valid_crop_and_shared_mix(tmp_path) -> None:
    rows = []
    for age in ("Infant", "Child"):
        for source in ("heart", "lung"):
            for subject_index in range(2):
                subject = f"{age}-{source}-{subject_index}"
                row = {"dataset_id": source + "-fixture", "dataset_group": source + "-fixture",
                       "subject_id": subject, "source_type": source}
                while external_holdout(row):
                    row["subject_id"] += "x"
                key = row["subject_id"]
                t = np.arange(40000, dtype=np.float32) / 4000
                frequency = 60 + subject_index if source == "heart" else 340 + subject_index
                data = ((.05 if age == "Infant" else .07) * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
                path = tmp_path / f"{key}.npy"
                np.save(path, data, allow_pickle=False)
                row.update({"recording_id": key, "age_group": age, "family_id": "synthetic_label",
                            "canonical_sample_rate": 4000, "canonical_channel_count": 1,
                            "canonical_samples": len(data), "derived_path": str(path),
                            "derived_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "valid_intervals_4k": [[1000, 39000]], "source_purity_tier": "B",
                            "source_purity_evidence": "synthetic fixture, not a clinical purity claim",
                            "source_purity_confidence": "synthetic", "purity_reviewer": "test"})
                rows.append(row)
    normalized = normalize_registry({"recordings": rows})
    ages, _, used = hierarchy(normalized)
    assert ages == ["Child", "Infant"] and len(used) == 8
    recipes = recipe_schedule(normalized, 64, 20260928)
    assert recipes == recipe_schedule(normalized, 64, 20260928)
    by_key = {r["registry_key"]: r for r in normalized}
    for recipe in recipes:
        assert 1000 <= recipe["heart_start"] <= 7000 and 1000 <= recipe["lung_start"] <= 7000
        assert by_key[recipe["heart_registry_key"]]["age_group"] == by_key[recipe["lung_registry_key"]]["age_group"]
    x, target, receipt = materialize(recipes[0], AudioCache(used, capacity=2))
    assert x.shape == (32000,) and target.shape == (2, 32000)
    assert np.max(np.abs(x - target.sum(0))) < 1e-6
    measured = 20 * np.log10(np.sqrt(np.mean(target[1].astype(float) ** 2)) /
                            np.sqrt(np.mean(target[0].astype(float) ** 2)))
    assert abs(measured - receipt["relative_lung_to_heart_db"]) < 1e-5
    assert np.max(np.abs(x)) <= 1.000001 and receipt["network_shared_peak_scale"] > 0
