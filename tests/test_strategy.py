from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.ml import neossnet_strategy as neossnet_strategy_module
from app.ml.neossnet_strategy import NeoSSNetStrategy
from app.ml.separation_algorithm import SeparationAlgorithmResult
from app.ml.separation_engine import SeparationEngine
from app.models.db_models import Model
from app.services.separation_algorithm_factory import SeparationAlgorithmFactory


class RecordingAlgorithm:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        self.calls.append(
            {
                "input_wav_path": input_wav_path,
                "model_path": model_path,
                "model_config_path": model_config_path,
                "heart_output_path": heart_output_path,
                "lung_output_path": lung_output_path,
                "device_name": device_name,
            }
        )
        return SeparationAlgorithmResult(
            heart_file_path=heart_output_path,
            lung_file_path=lung_output_path,
            sample_rate_hz=4000,
            duration_sec=1.0,
            heart_file_size_bytes=12,
            lung_file_size_bytes=12,
            input_shape=(1, 4000),
            output_shape=(1, 2, 4000),
        )


def test_separation_engine_uses_algorithm_interface() -> None:
    algorithm = RecordingAlgorithm()
    engine = SeparationEngine(algorithm=algorithm, device_name="cpu")

    result = engine.separate(
        input_wav_path=Path("input.wav"),
        model_path=Path("model.pth"),
        model_config_path=Path("model.yaml"),
        heart_output_path=Path("heart.wav"),
        lung_output_path=Path("lung.wav"),
    )

    assert result.heart_file_path == Path("heart.wav")
    assert algorithm.calls == [
        {
            "input_wav_path": Path("input.wav"),
            "model_path": Path("model.pth"),
            "model_config_path": Path("model.yaml"),
            "heart_output_path": Path("heart.wav"),
            "lung_output_path": Path("lung.wav"),
            "device_name": "cpu",
        }
    ]


def test_neossnet_strategy_wraps_real_inference_boundary(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_run_neossnet_inference(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(
            heart_file_path=kwargs["heart_output_path"],
            lung_file_path=kwargs["lung_output_path"],
            sample_rate_hz=4000,
            duration_sec=1.0,
            heart_file_size_bytes=16,
            lung_file_size_bytes=16,
            input_shape=(1, 4000),
            output_shape=(1, 2, 4000),
        )

    monkeypatch.setattr(
        neossnet_strategy_module,
        "run_neossnet_inference",
        fake_run_neossnet_inference,
    )

    result = NeoSSNetStrategy().separate(
        input_wav_path=Path("mixed.wav"),
        model_path=Path("neossnet.pth"),
        model_config_path=Path("neossnet.yaml"),
        heart_output_path=Path("heart.wav"),
        lung_output_path=Path("lung.wav"),
        device_name="cpu",
    )

    assert calls["input_wav_path"] == Path("mixed.wav")
    assert calls["model_path"] == Path("neossnet.pth")
    assert calls["model_config_path"] == Path("neossnet.yaml")
    assert result.output_shape == (1, 2, 4000)


def test_separation_algorithm_factory_creates_neossnet_strategy() -> None:
    model = Model(
        model_name="NeoSSNet",
        version="1.0",
        architecture="NeoSSNet",
        framework="PyTorch",
        checkpoint_path="storage/ml_models/model_best.pt",
        config_path="storage/ml_models/model.yaml",
    )

    algorithm = SeparationAlgorithmFactory.create_algorithm(model)

    assert isinstance(algorithm, NeoSSNetStrategy)
