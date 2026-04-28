"""Standalone NeoSSNet inference smoke test.

This script intentionally does not import or modify the FastAPI app. It uses the
external NeoSSNet source in external/neossnet_source to load model_best.pt and
model.yaml, run real CPU inference on sample_inputs/H0001.wav, and save the two
separated output WAV files.
"""

from __future__ import annotations

import importlib.util
import sys
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEOSSNET_SOURCE_DIR = PROJECT_ROOT / "external" / "neossnet_source"
MODEL_PATH = PROJECT_ROOT / "storage" / "ml_models" / "model_best.pt"
MODEL_CONFIG_PATH = PROJECT_ROOT / "storage" / "ml_models" / "model.yaml"
INPUT_WAV_PATH = PROJECT_ROOT / "sample_inputs" / "H0001.wav"
HEART_OUTPUT_PATH = PROJECT_ROOT / "storage" / "outputs" / "heart" / "test_heart.wav"
LUNG_OUTPUT_PATH = PROJECT_ROOT / "storage" / "outputs" / "lung" / "test_lung.wav"
MODEL_SAMPLE_RATE = 4000

REQUIRED_PACKAGES = {
    "torch": "torch",
    "torchaudio": "torchaudio",
    "yaml": "pyyaml",
    "ptwt": "ptwt",
    "prettytable": "prettytable",
    "numpy": "numpy",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_dependencies() -> None:
    missing = [
        pip_name
        for import_name, pip_name in REQUIRED_PACKAGES.items()
        if importlib.util.find_spec(import_name) is None
    ]
    if not missing:
        return

    unique_missing = sorted(set(missing))
    print("Missing Python dependencies:")
    for package_name in unique_missing:
        print(f"- {package_name}")
    print()
    print("Install command:")
    print(f"pip install {' '.join(unique_missing)}")
    fail("Install the missing dependencies and run this script again.")


def check_required_files() -> None:
    required_paths = [
        NEOSSNET_SOURCE_DIR / "README.md",
        NEOSSNET_SOURCE_DIR / "utils" / "__init__.py",
        NEOSSNET_SOURCE_DIR / "models" / "__init__.py",
        MODEL_PATH,
        MODEL_CONFIG_PATH,
        INPUT_WAV_PATH,
    ]
    for path in required_paths:
        if not path.exists():
            fail(f"Required file or folder is missing: {path.relative_to(PROJECT_ROOT)}")

    if MODEL_PATH.stat().st_size == 0:
        fail(f"Model checkpoint is empty: {MODEL_PATH.relative_to(PROJECT_ROOT)}")


def add_neossnet_to_path() -> None:
    source_dir = str(NEOSSNET_SOURCE_DIR)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)


def load_input_audio():
    import numpy as np
    import torch

    with wave.open(str(INPUT_WAV_PATH), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_audio = wav_file.readframes(frame_count)

    if sample_width == 1:
        audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0
    elif sample_width == 3:
        audio_bytes = np.frombuffer(raw_audio, dtype=np.uint8).reshape(-1, 3)
        sign_byte = (audio_bytes[:, 2] >= 128).astype(np.uint8) * 255
        audio_32 = np.column_stack([audio_bytes, sign_byte]).reshape(-1, 4)
        audio = audio_32.view(np.int32).reshape(-1).astype(np.float32)
        audio = audio / 8388608.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_audio, dtype=np.int32).astype(np.float32)
        audio = audio / 2147483648.0
    else:
        fail(f"Unsupported WAV sample width: {sample_width} bytes")

    waveform = torch.from_numpy(audio.reshape(-1, channels).T.copy())

    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    if sample_rate != MODEL_SAMPLE_RATE:
        target_length = round(waveform.shape[-1] * MODEL_SAMPLE_RATE / sample_rate)
        waveform = torch.nn.functional.interpolate(
            waveform.unsqueeze(0),
            size=target_length,
            mode="linear",
            align_corners=False,
        ).squeeze(0)
        sample_rate = MODEL_SAMPLE_RATE

    max_abs = torch.max(torch.abs(waveform))
    if max_abs > 0:
        waveform = waveform / max_abs

    return waveform.to(dtype=torch.float32), sample_rate


def save_output_audio(path: Path, waveform, sample_rate: int) -> None:
    import numpy as np
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    waveform = waveform.detach().cpu().to(dtype=torch.float32)
    waveform = torch.clamp(waveform, min=-1.0, max=1.0)

    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)

    audio = waveform.squeeze(0).numpy()
    audio_i16 = (audio * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_i16.tobytes())


def main() -> int:
    check_dependencies()
    check_required_files()
    add_neossnet_to_path()

    import torch
    from utils import generate_output

    device = torch.device("cpu")
    input_wav, sample_rate = load_input_audio()

    print(f"Sample rate: {sample_rate}")
    print(f"Input shape before batch dimension: {tuple(input_wav.shape)}")

    with torch.inference_mode():
        heart_wav, lung_wav = generate_output(
            input_wav=input_wav,
            model_path=str(MODEL_PATH),
            model_config=str(MODEL_CONFIG_PATH),
            device=device,
        )

    output_shape = (1, 2, heart_wav.numel())
    print(f"Output shape: {output_shape}")

    save_output_audio(HEART_OUTPUT_PATH, heart_wav, sample_rate)
    save_output_audio(LUNG_OUTPUT_PATH, lung_wav, sample_rate)

    print(f"Heart output saved: {HEART_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Lung output saved: {LUNG_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print("PASS: NeoSSNet inference completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
