"""One durable CPU worker. Run explicitly; never launched by an HTTP request."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import stat
import subprocess
import time
from pathlib import Path

from .config import PROJECT_ROOT, Settings
from .ml_contract import ProcessingError, WORKER_VERSION
from .store import M1Store


def code_identity():
    supplied = os.environ.get("STETHOFUSE_CODE_GIT_SHA", "")
    if supplied:
        if not re.fullmatch(r"[0-9a-f]{40}", supplied):
            raise ProcessingError("invalid_code_identity")
        return supplied, False
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=PROJECT_ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        raise ProcessingError("code_identity_unavailable") from None
    return sha, dirty


class Worker:
    def __init__(self, settings: Settings, checkpoint: Path, specification: Path):
        settings.validate()
        self.settings, self.checkpoint, self.specification = settings, checkpoint, specification
        self.store = M1Store(settings.database)
        self.lock_fd = None
        self.separator = None

    def __enter__(self):
        self.settings.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.settings.database.with_suffix(self.settings.database.suffix + ".worker.lock")
        self.lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.lock_fd)
            self.lock_fd = None
            raise ProcessingError("worker_already_running") from None
        try:
            self.settings.private_storage.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.settings.private_storage.is_symlink() or self.settings.private_storage.stat().st_mode & 0o077:
                raise ProcessingError("private_storage_permissions")
            self.store.initialize()
            self.code_sha, self.code_dirty = code_identity()
            # Import PyTorch only in this dedicated worker process.
            from .frozen_model import FrozenSeparator
            self.separator = FrozenSeparator(self.checkpoint, self.specification)
            for job in self.store.interrupted_jobs():
                self.cleanup(job)
                if job["status"] == "processing":
                    self.store.recover_interrupted(job)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None

    def output_path(self, job, kind, temporary=False):
        identity = job[f"{kind}_resource_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise ProcessingError("invalid_artifact_identity")
        return self.settings.private_storage / (identity + (".wav.tmp" if temporary else ".wav"))

    def sync_directory(self):
        fd = os.open(self.settings.private_storage, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def cleanup(self, job):
        # These four exact paths are reserved by this job; never scan/delete uploads.
        for kind in ("heart", "lung"):
            for temporary in (True, False):
                self.output_path(job, kind, temporary).unlink(missing_ok=True)
        self.sync_directory()

    def read_input(self, job):
        info = job["input_file"]
        if not re.fullmatch(r"[0-9a-f]{32}\.wav", info["relative_path"]):
            raise ProcessingError("input_unavailable")
        try:
            fd = os.open(self.settings.private_storage / info["relative_path"], os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > self.settings.max_upload_bytes:
                    raise ProcessingError("invalid_audio")
                payload = stream.read(self.settings.max_upload_bytes + 1)
            if len(payload) != info["file_size_bytes"]:
                raise ProcessingError("input_integrity_mismatch")
        except OSError:
            raise ProcessingError("input_unavailable") from None
        from .frozen_model import digest
        sha = digest(payload)
        if job["input_sha256"] and sha != job["input_sha256"]:
            raise ProcessingError("input_integrity_mismatch")
        return payload, sha

    def write_output(self, job, kind, samples):
        import numpy as np
        from scipy.io import wavfile
        from .frozen_model import digest

        target, temporary = self.output_path(job, kind), self.output_path(job, kind, True)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            wavfile.write(stream, 4000, samples.astype("<f4"))
            stream.flush()
            os.fsync(stream.fileno())
        rate, restored = wavfile.read(temporary)
        if rate != 4000 or restored.dtype != np.float32 or not np.array_equal(restored, samples) or not np.isfinite(restored).all():
            raise ProcessingError("output_integrity_failed")
        # Publish without replacing another file. DB links are committed only after BOTH files verify.
        os.link(temporary, target, follow_symlinks=False)
        temporary.unlink()
        self.sync_directory()
        return {"relative_path": target.name, "size": target.stat().st_size, "sha256": digest(target.read_bytes())}

    def run_once(self):
        if self.lock_fd is None or self.separator is None:
            raise ProcessingError("worker_not_started")
        job = self.store.claim_job()
        if job is None or job["status"] == "failed":
            return job
        stage, started = "input", time.perf_counter()
        try:
            payload, input_sha = self.read_input(job)
            canonical, preprocessing = self.separator.decode(payload)
            stage = "inference"
            separated, runtime = self.separator.separate(canonical)
            stage = "output_storage"
            outputs = {kind: self.write_output(job, kind, separated[index]) for index, kind in enumerate(("heart", "lung"))}
            stage = "result_persistence"
            provenance = {**self.separator.provenance(), **preprocessing,
                          "input_recording_id": job["recording_id"], "input_artifact_sha256": input_sha,
                          "heart_output_artifact_id": job["heart_resource_id"], "lung_output_artifact_id": job["lung_resource_id"],
                          "heart_output_sha256": outputs["heart"]["sha256"], "lung_output_sha256": outputs["lung"]["sha256"],
                          "code_git_sha": self.code_sha, "code_worktree_dirty": self.code_dirty,
                          "worker_version": WORKER_VERSION, "worker_attempt": job["attempts"],
                          "runtime_seconds": runtime, "processing_seconds": time.perf_counter() - started,
                          "output_samples": len(canonical), "started_at": job["started_at"]}
            self.store.complete_job(job, outputs, provenance)
            return {"id": job["id"], "status": "succeeded", "runtime_seconds": runtime}
        except Exception as error:
            code = error.code if isinstance(error, ProcessingError) else {
                "input": "input_unavailable", "inference": "inference_failed",
                "output_storage": "output_storage_failed", "result_persistence": "result_persistence_failed",
            }[stage]
            # Failure is durable even if filesystem cleanup itself is unavailable.
            if not self.store.fail_job(job, code, stage):
                # Never unlink possibly committed result files after an ambiguous finalization.
                raise ProcessingError("job_finalization_state_unknown") from None
            try:
                self.cleanup(job)
            except OSError:
                pass
            return {"id": job["id"], "status": "failed", "error_code": code, "stage": stage}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one queued job and exit")
    args = parser.parse_args()
    settings = Settings.from_environment()
    checkpoint = os.environ.get("STETHOFUSE_MODEL_CHECKPOINT")
    specification = Path(os.environ.get("STETHOFUSE_SEPARATOR_SPEC", PROJECT_ROOT / "research/configs/final_separator_v2.json"))
    if settings is None or not checkpoint or not Path(checkpoint).is_absolute():
        raise SystemExit("worker_configuration_missing")
    stop = False

    def request_stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        with Worker(settings, Path(checkpoint), specification) as worker:
            print(json.dumps({"status": "ready", "model_load_seconds": worker.separator.load_seconds, "worker_version": WORKER_VERSION}), flush=True)
            while not stop:
                result = worker.run_once()
                if result:
                    print(json.dumps(result), flush=True)
                if args.once:
                    break
                if result is None:
                    time.sleep(2)
    except ProcessingError as error:
        raise SystemExit(error.code) from None


if __name__ == "__main__":
    main()
