"""Immutable application identity for the selected T8 v2; no ML imports."""
MODEL_VERSION = "stethofuse-tcn-small-hls-refit-waveform-v2"
ARCHITECTURE_VERSION = "stethofuse-convtasnet-4k-small-v1"
PARAMETER_COUNT = 171313
CHECKPOINT_SHA256 = "1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658"
SPEC_SHA256 = "2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b"
WORKER_VERSION = "stethofuse-local-cpu-worker-v1"


class ProcessingError(RuntimeError):
    """Safe stable code only; never a source path, token, or raw model exception."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
