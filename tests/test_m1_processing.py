"""Focused LOCAL acceptance: generated PCM only, fictional identities, real frozen weights.

Set STETHOFUSE_TEST_CHECKPOINT explicitly. Never reads dataset or T9 artifacts.
"""
import io
import json
import os
import resource
import sqlite3
import time
import wave
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.m1.api import create_app
from app.m1.config import PROJECT_ROOT
from app.m1.ml_contract import CHECKPOINT_SHA256, SPEC_SHA256, ProcessingError
from app.m1.store import M1Store
from app.m1.worker import Worker
from test_m1_api import env, auth, grant

CHECKPOINT = os.environ.get("STETHOFUSE_TEST_CHECKPOINT")
SPEC = PROJECT_ROOT / "research/configs/final_separator_v2.json"
requires_model = pytest.mark.skipif(not CHECKPOINT, reason="Explicit local frozen-artifact acceptance only")


def synthetic_wav(rate=4000, seconds=15, channels=1, silence=False):
    import numpy as np
    t = np.arange(int(rate * seconds), dtype=np.float64) / rate
    x = (0.18 * np.sin(2*np.pi*75*t) * (0.5+0.5*np.sin(2*np.pi*1.3*t)**2)
         + 0.06 * np.sin(2*np.pi*430*t) * (0.65+0.35*np.cos(2*np.pi*0.3*t)))
    if silence:
        x[:] = 0
    samples = np.repeat(x[:, None], channels, axis=1)
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes((samples*32767).astype("<i2").tobytes())
    return stream.getvalue()


def add(env, client, **audio):
    r = client.post("/api/recordings", headers=auth(), files={"file": ("generated.wav", synthetic_wav(**audio), "audio/wav")})
    assert r.status_code == 201, r.text
    return r.json()


def enqueue(client, recording):
    r = client.post(f"/api/recordings/{recording['id']}/jobs", json={}, headers=auth())
    assert r.status_code == 202, r.text
    return r.json()


def worker(env):
    return Worker(env.settings, Path(CHECKPOINT), SPEC)


@requires_model
def test_real_frozen_flow_privacy_provenance_restart(env, record_property):
    import numpy as np
    from scipy.io import wavfile

    enabled = replace(env.settings, separation_enabled=True)
    with TestClient(create_app(enabled, verifier=env.verifier)) as client:
        recording = add(env, client)
        for outsider in ("other", "admin", "analyst"):
            assert client.post(f"/api/recordings/{recording['id']}/jobs", json={}, headers=auth(outsider)).status_code == 403
        before = time.perf_counter()
        job = enqueue(client, recording)
        request_time = time.perf_counter()-before
        assert job["status"] == "queued" and request_time < 1.0
        assert enqueue(client, recording)["id"] == job["id"]
        assert "claim_token" not in job and job["result_id"] is None
        startup = time.perf_counter()
        cpu_start = time.process_time()
        with worker(env) as w:
            record_property("worker_startup_seconds", time.perf_counter()-startup)
            started = time.perf_counter()
            result = w.run_once()
            assert result["status"] == "succeeded"
            assert w.run_once() is None
            record_property("worker_load_seconds", w.separator.load_seconds)
            record_property("inference_seconds_15s", result["runtime_seconds"])
            record_property("whole_job_seconds", time.perf_counter()-started)
            record_property("startup_and_job_cpu_seconds", time.process_time()-cpu_start)
            record_property("request_seconds", request_time)
            record_property("peak_rss_mib", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
            record_property("environment", json.dumps(w.separator.environment))
            record_property("parameter_count", w.separator.model.parameter_count)
            assert w.separator.load_count == 1
        job = client.get(f"/api/jobs/{job['id']}", headers=auth()).json()
        assert job["status"] == "succeeded" and job["attempts"] == 1
        result_id = job["result_id"]
        result = client.get(f"/api/results/{result_id}", headers=auth()).json()
        assert {r["kind"] for r in result["resources"]} == {"heart_audio", "lung_audio"}
        provenance = result["provenance"]
        assert provenance["checkpoint_sha256"] == CHECKPOINT_SHA256
        assert provenance["separator_spec_sha256"] == SPEC_SHA256
        assert provenance["output_semantic_order"] == ["heart", "lung"]
        assert provenance["output_samples"] == 60000 and provenance["sample_rate"] == 4000
        assert len(provenance["input_artifact_sha256"]) == len(provenance["code_git_sha"]) + 24 == 64
        audio = []
        for info in result["resources"]:
            response = client.get(info["url"], headers=auth())
            assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
            rate, samples = wavfile.read(io.BytesIO(response.content))
            assert rate == 4000 and len(samples) == 60000 and samples.dtype == np.float32
            assert np.isfinite(samples).all()
            audio.append(samples)
            assert client.get(info["url"]).status_code == 401
            for outsider in ("other", "admin", "analyst"):
                assert client.get(info["url"], headers=auth(outsider)).status_code == 403
        canonical, _ = w.separator.decode(synthetic_wav())
        assert np.max(np.abs(audio[0]+audio[1]-canonical)) < 1e-6
        # Preserve exact-resource semantics: a result review grant does NOT grant audio.
        g = grant(env, recording, permission="review", resource_id=result_id)
        assert client.get(f"/api/results/{result_id}", headers=auth("analyst")).json()["resources"] == []
        for info in result["resources"]:
            grant(env, recording, permission="read", resource_id=info["id"])
            assert client.get(info["url"], headers=auth("analyst")).status_code == 200
        assert client.get(recording["resources"][0]["url"], headers=auth("analyst")).status_code == 403
        review = client.put(f"/api/assignments/{g['id']}/review", headers=auth("analyst"), json={"decision":"accepted","notes":"Synthetic local acceptance"})
        assert review.status_code == 200
        assert client.get(f"/api/results/{result_id}", headers=auth("other")).status_code == 403
        client.post(f"/api/recordings/{recording['id']}/revoke-access", headers=auth(),
                    json={"recipient_id":env.users["analyst"]["id"],"confirmed_recording_id":recording["id"]})
        assert client.get(f"/api/results/{result_id}", headers=auth("analyst")).status_code == 403
        for info in result["resources"]:
            assert client.get(info["url"], headers=auth("analyst")).status_code == 403
        assert client.get(f"/api/assignments/{g['id']}/review", headers=auth("analyst")).status_code == 403
        # API restart + new identity sync uses the same persisted result.
        with TestClient(create_app(enabled, verifier=env.verifier)) as restarted:
            assert restarted.post("/api/auth/session", headers=auth(), json={}).status_code == 200
            assert restarted.get(f"/api/results/{result_id}", headers=auth()).json()["provenance"] == provenance
            assert enqueue(restarted, recording)["id"] == job["id"]
        actions = [r["action"] for r in env.store.audit(env.verifier.identities["admin"])]
        assert {"separation.requested", "separation.started", "separation.succeeded"} <= set(actions)


@requires_model
def test_bounded_recovery_exclusive_worker_and_once_only_result(env):
    with TestClient(create_app(replace(env.settings,separation_enabled=True),verifier=env.verifier)) as client:
        recording=add(env,client)
        job=enqueue(client,recording)
        with worker(env) as first:
            claimed=first.store.claim_job()
            assert claimed["id"]==job["id"] and first.store.claim_job() is None
            with pytest.raises(ProcessingError,match="worker_already_running"):
                with worker(env):
                    pass
            first.output_path(claimed,"heart",True).write_bytes(b"interrupted private output")
            # Exit without completing the claim: same durable state as a killed worker.
        with worker(env) as restarted:
            assert not restarted.output_path(claimed,"heart",True).exists()
            assert restarted.run_once()["status"]=="succeeded"
            assert restarted.separator.load_count==1
        saved=client.get(f"/api/jobs/{job['id']}",headers=auth()).json()
        assert saved["status"]=="succeeded" and saved["attempts"]==2
        assert len(client.get("/api/results",headers=auth()).json()["items"])==1
        second=enqueue(client,add(env,client,seconds=1))
        for _ in range(2):
            with worker(env) as w:
                assert w.store.claim_job()["id"]==second["id"]
        with worker(env) as w:
            assert w.run_once() is None
        saved=client.get(f"/api/jobs/{second['id']}",headers=auth()).json()
        assert saved["status"]=="failed" and saved["error_code"]=="worker_interrupted"


@requires_model
def test_hash_missing_inference_and_storage_fail_closed(env,tmp_path):
    bad=tmp_path/"bad.pt";bad.write_bytes(b"not approved weights")
    for path,code in ((bad,"model_artifact_hash_mismatch"),(tmp_path/"missing.pt","model_artifact_unavailable")):
        with pytest.raises(ProcessingError,match=code):
            with Worker(env.settings,path,SPEC):
                pass
    with TestClient(create_app(replace(env.settings,separation_enabled=True),verifier=env.verifier)) as client, worker(env) as w:
        for stage in ("inference", "output_storage"):
            recording=add(env,client,seconds=1)
            job=enqueue(client,recording)
            if stage=="inference":
                with patch.object(w.separator,"separate",side_effect=ProcessingError("inference_failed")):
                    assert w.run_once()["status"]=="failed"
            else:
                real_write=w.write_output
                def fail_lung(job,kind,samples):
                    if kind=="lung":raise OSError("private path must never reach API")
                    return real_write(job,kind,samples)
                with patch.object(w,"write_output",side_effect=fail_lung):
                    assert w.run_once()["status"]=="failed"
            saved=client.get(f"/api/jobs/{job['id']}",headers=auth()).json()
            assert saved["status"]=="failed" and saved["result_id"] is None and saved["stage"]==stage
            assert "private path" not in str(saved)
            assert enqueue(client,recording)["id"]==job["id"]
        assert client.get("/api/results",headers=auth()).json()=={"items":[]}
        assert len(list(env.settings.private_storage.glob("*.wav")))==2  # originals only
        assert not list(env.settings.private_storage.glob("*.tmp"))


@requires_model
def test_canonicalization_exact_helper_zero_and_model_reuse(env):
    import numpy as np
    from app.ml.ensemble_v1 import canonicalize
    from app.ml.audio_utils import _decode_pcm
    with worker(env) as w:
        source=synthetic_wav(rate=44100,seconds=1.137,channels=2)
        canonical,info=w.separator.decode(source)
        with wave.open(io.BytesIO(source)) as wav:
            expected=canonicalize(_decode_pcm(wav.readframes(wav.getnframes()),2).reshape(-1,2).T,44100)
        assert np.array_equal(canonical,expected)
        output,_=w.separator.separate(canonical)
        assert output.shape==(2,len(canonical)) and np.isfinite(output).all()
        assert np.max(np.abs(output.sum(axis=0)-canonical))<1e-6
        zero,_=w.separator.decode(synthetic_wav(seconds=0.7,silence=True))
        outputs,_=w.separator.separate(zero)
        assert not np.any(outputs) and w.separator.load_count==1


def test_v1_migration_is_transactional_and_preserves_existing_data(tmp_path):
    path=tmp_path/"existing.sqlite3"
    with sqlite3.connect(path) as db:
        for schema in (PROJECT_ROOT/"app/access_foundation/schema.sql",PROJECT_ROOT/"app/m1/schema.sql"):
            db.executescript(schema.read_text())
        db.execute("INSERT INTO af_users VALUES ('existing','existing-uid','existing@example.invalid','Preserve me','healthcare_staff','active',1,1,1)")
        db.execute("INSERT INTO m1_preferences VALUES ('existing',?)", ('{"appearance":{"snow":false}}',))
    store=M1Store(path);store.initialize();store.initialize()
    with store._connection() as db:
        assert db.execute("SELECT version FROM m1_meta").fetchone()[0]==2
        assert "provenance_json" in {r[1] for r in db.execute("PRAGMA table_info(m1_results)")}
        assert db.execute("SELECT display_name FROM af_users WHERE id='existing'").fetchone()[0]=='Preserve me'
        assert db.execute("SELECT preferences_json FROM m1_preferences WHERE user_id='existing'").fetchone()[0]=='{"appearance":{"snow":false}}'
