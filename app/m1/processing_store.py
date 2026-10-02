"""Durable job transitions in the existing M1 SQLite transaction domain."""
from __future__ import annotations

import json
import time
from uuid import uuid4

from app.access_foundation import AccessDenied
from .ml_contract import MODEL_VERSION, ProcessingError


class ProcessingStore:
    @staticmethod
    def _public_job(row):
        keys = ("id", "public_id", "recording_id", "requester_id", "status", "created_at", "started_at",
                "completed_at", "error_code", "stage", "attempts", "model_version")
        result = {k: row[k] for k in keys}
        result["result_id"] = row["result_id"] if row["status"] == "succeeded" else None
        return result

    def request_separation(self, identity, recording_id):
        with self._connection(write=True) as db:
            actor = self._actor(db, identity)
            self._owner(db, actor, recording_id)
            row = db.execute("SELECT * FROM m1_jobs WHERE recording_id=? AND model_version=?",
                             (recording_id, MODEL_VERSION)).fetchone()
            if row is None:
                original = db.execute("SELECT f.sha256 FROM m1_recording_data d JOIN m1_files f "
                                      "ON d.original_resource_id=f.resource_id WHERE d.recording_id=?",
                                      (recording_id,)).fetchone()
                if original is None:
                    raise AccessDenied("Access denied.")
                job_id = uuid4().hex
                public_id = self._new_public_id(db, "m1_jobs", "JOB")
                db.execute("INSERT INTO m1_jobs(id,public_id,recording_id,requester_id,status,created_at,model_version,"
                           "stage,result_id,heart_resource_id,lung_resource_id,input_sha256) "
                           "VALUES (?,?,?,?,'queued',?,?,'queued',?,?,?,?)",
                           (job_id, public_id, recording_id, actor["id"], int(time.time()), MODEL_VERSION,
                            uuid4().hex, uuid4().hex, uuid4().hex, original[0]))
                self._audit(db, actor["id"], "separation.requested", job_id)
                row = db.execute("SELECT * FROM m1_jobs WHERE id=?", (job_id,)).fetchone()
            return self._public_job(row)

    def claim_job(self):
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM m1_jobs WHERE status='queued' AND model_version=? "
                             "ORDER BY created_at,id LIMIT 1", (MODEL_VERSION,)).fetchone()
            if row is None:
                return None
            job = dict(row)
            try:
                self._active_user(db, row["requester_id"])
                owner = db.execute("SELECT owner_id FROM af_recordings WHERE id=?", (row["recording_id"],)).fetchone()
                if owner is None or owner[0] != row["requester_id"]:
                    raise AccessDenied("Access denied.")
            except AccessDenied:
                db.execute("UPDATE m1_jobs SET status='failed',completed_at=?,stage='authorization',"
                           "error_code='owner_unavailable' WHERE id=?", (int(time.time()), row["id"]))
                self._audit(db, row["requester_id"], "separation.failed", row["id"])
                return {**job, "status": "failed"}
            token, now = uuid4().hex, int(time.time())
            db.execute("UPDATE m1_jobs SET status='processing',started_at=?,attempts=attempts+1,"
                       "claim_token=?,stage='input',error_code=NULL WHERE id=? AND status='queued'",
                       (now, token, row["id"]))
            self._audit(db, row["requester_id"], "separation.started", row["id"])
            source = db.execute("SELECT f.* FROM m1_recording_data d JOIN m1_files f "
                                "ON f.resource_id=d.original_resource_id WHERE d.recording_id=?",
                                (row["recording_id"],)).fetchone()
            if source is None:
                raise ProcessingError("input_unavailable")
            return {**job, "status": "processing", "started_at": now, "attempts": row["attempts"] + 1,
                    "claim_token": token, "input_file": dict(source)}

    def interrupted_jobs(self):
        with self._connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM m1_jobs j WHERE status IN ('processing','failed') AND model_version=? "
                                                  "AND NOT EXISTS(SELECT 1 FROM m1_results r WHERE r.job_id=j.id)", (MODEL_VERSION,))]

    def recover_interrupted(self, job):
        # Called only while holding the process-lifetime exclusive worker lock.
        with self._connection(write=True) as db:
            row = db.execute("SELECT * FROM m1_jobs WHERE id=? AND status='processing' AND claim_token=?",
                             (job["id"], job["claim_token"])).fetchone()
            if row is None:
                return
            if db.execute("SELECT 1 FROM m1_results WHERE job_id=?", (job["id"],)).fetchone():
                raise ProcessingError("inconsistent_job_state")
            retry = row["attempts"] < 2
            db.execute("UPDATE m1_jobs SET status=?,stage='recovery',claim_token=NULL,error_code=?,completed_at=? WHERE id=?",
                       ("queued" if retry else "failed", None if retry else "worker_interrupted",
                        None if retry else int(time.time()), job["id"]))
            self._audit(db, row["requester_id"], "separation.requeued" if retry else "separation.failed", job["id"])

    def fail_job(self, job, code, stage):
        with self._connection(write=True) as db:
            changed = db.execute("UPDATE m1_jobs SET status='failed',completed_at=?,stage=?,error_code=?,claim_token=NULL "
                                 "WHERE id=? AND status='processing' AND claim_token=?",
                                 (int(time.time()), stage, code, job["id"], job["claim_token"])).rowcount
            if changed:
                self._audit(db, job["requester_id"], "separation.failed", job["id"])
            return bool(changed)

    def complete_job(self, job, outputs, provenance):
        with self._connection(write=True) as db:
            current = db.execute("SELECT 1 FROM m1_jobs WHERE id=? AND status='processing' AND claim_token=?",
                                 (job["id"], job["claim_token"])).fetchone()
            if current is None:
                raise ProcessingError("job_claim_lost")
            self._active_user(db, job["requester_id"])
            now = int(time.time())
            provenance = {**provenance, "created_at": job["created_at"], "completed_at": now}
            db.execute("INSERT INTO af_resources(id,recording_id,kind) VALUES (?,?, 'result')", (job["result_id"], job["recording_id"]))
            db.execute("INSERT INTO m1_results(id,recording_id,job_id,created_at,method_label,provenance_json) VALUES (?,?,?,?,?,?)",
                       (job["result_id"], job["recording_id"], job["id"], now, "Heart and lung separation",
                        json.dumps(provenance, sort_keys=True)))
            for kind, info in outputs.items():
                resource_id = job[f"{kind}_resource_id"]
                db.execute("INSERT INTO af_resources(id,recording_id,kind) VALUES (?,?,?)", (resource_id, job["recording_id"], f"{kind}_audio"))
                db.execute("INSERT INTO m1_files(resource_id,relative_path,media_type,file_size_bytes,sha256) VALUES (?,?, 'audio/wav',?,?)",
                           (resource_id, info["relative_path"], info["size"], info["sha256"]))
                db.execute("INSERT INTO m1_result_files VALUES (?,?)", (job["result_id"], resource_id))
            db.execute("UPDATE m1_jobs SET status='succeeded',completed_at=?,stage='complete',claim_token=NULL,input_sha256=? WHERE id=?",
                       (now, provenance["input_artifact_sha256"], job["id"]))
            self._audit(db, job["requester_id"], "separation.succeeded", job["id"])
