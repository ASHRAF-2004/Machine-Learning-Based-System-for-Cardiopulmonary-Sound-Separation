# Cardiopulmonary Sound Separation System

Final Year Project implementation for separating mixed cardiopulmonary WAV audio into heart-sound and lung-sound outputs. The system is a local FastAPI web app with SQLite metadata, filesystem audio storage, strategy-based separation methods, browser preview/download, processing history, and evaluation metrics when paired references are available.

This project is for sound separation research/demo use only. It is not a clinical diagnostic system.

## Supported Separation Methods

| Method | Type | Implementation status |
| --- | --- | --- |
| Fixed Filter Baseline | Conventional baseline | Implemented with smooth frequency-domain masks. Useful for validating the full workflow. |
| NMF Decomposition | Decomposition baseline | Implemented as an unsupervised NumPy NMF spectrogram soft-mask baseline. Not a trained ML model. |
| VMD Decomposition | Decomposition baseline | Implemented with `vmdpy`, mode grouping by dominant frequency, and a fast/safe preset for local UI use. Not a trained ML model. |
| NeoSSNet | Deep learning model | Main ML method. Uses PyTorch, `model_best.pt`, and `model.yaml` for real inference. |

The app uses a Strategy + Factory structure:

```text
app/ml/strategies/base.py
app/ml/strategies/fixed_filter_strategy.py
app/ml/strategies/nmf_strategy.py
app/ml/strategies/vmd_strategy.py
app/ml/neossnet_strategy.py
app/ml/strategy_factory.py
app/services/separation_service.py
```

Routers do not hard-code separation algorithms. They call `SeparationService`, which selects a strategy from the database model registry.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/init_db.py
python scripts/prepare_dataset.py
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

If PyTorch installation fails, install the correct CPU build from the official PyTorch instructions for your Python version, then rerun `python -m pip install -r requirements.txt`.

## Database Setup

The project does not commit the runtime SQLite database file because it changes whenever the system is used.

When someone clones this repository, they should run:

```bash
python scripts/init_db.py
```

This command creates a fresh local database:

```text
database/cardiopulmonary.db
```

The repository should keep the database recipe files:

```text
database/schema.sql
database/seed.sql
scripts/init_db.py
```

The project should not rely on committing the local runtime database file:

```text
database/cardiopulmonary.db
```

`cardiopulmonary.db` stores local uploads, separation jobs, output paths, logs, and metrics. It is generated runtime data rather than source code.

## Workflow

1. Upload a mixed `.wav` file.
2. Select a Separation Method.
3. Run separation.
4. Preview heart and lung output WAV files.
5. Download outputs.
6. Review metrics when HLS-CMDS paired references are available.
7. View history.

Generated files are stored under:

```text
storage/uploads/raw/
storage/outputs/heart/
storage/outputs/lung/
```

SQLite stores metadata only. WAV files are not stored as database blobs.

## Dataset Setup

HLS-CMDS is expected under:

```text
datasets/hls_cmds/raw/HS/
datasets/hls_cmds/raw/LS/
datasets/hls_cmds/raw/Mix/
datasets/hls_cmds/metadata/
datasets/hls_cmds/processed/train/
datasets/hls_cmds/processed/val/
datasets/hls_cmds/processed/test/
```

Run:

```powershell
python scripts/prepare_dataset.py
```

The script reads `datasets/hls_cmds/metadata/Mix.csv`, copies paired `M####.wav`, `H####.wav`, and `L####.wav` files from `raw/Mix/`, and writes processed train/val/test folders plus split CSV files. Raw files are not modified.

Dataset source notes:

- HLS-CMDS: Mendeley Data and UCI repository.
- License/access note: CC BY 4.0 according to the public dataset pages.
- Contains mixed audio plus corresponding heart and lung references for paired examples.

## NeoSSNet Checkpoint Setup

NeoSSNet is the main ML/deep-learning method. The runtime registry expects:

```text
storage/ml_models/model_best.pt
storage/ml_models/model.yaml
```

The bundled/reference NeoSSNet code documents:

- input waveform shape: `(1, T)` for helper inference
- direct model input shape: `(B, 1, T)`
- direct model output shape: `(B, 2, T)`
- output channel order: channel 0 heart, channel 1 lung
- pretrained files: `models/model_best.pt` and `models/model.yaml`

NeoSSNet source reference:

```text
external/Neonatal-Chest-Sound-Separation-using-Deep-Learning-main/
```

No fake ML output is used. If the checkpoint/config are missing, NeoSSNet separation fails clearly instead of silently using a placeholder.

### Fine-Tuning NeoSSNet On HLS-CMDS

The project includes a real PyTorch fine-tuning script for the processed HLS-CMDS train/validation split:

```powershell
python scripts/train_neossnet_hls.py --quick-test --epochs 1
python scripts/train_neossnet_hls.py --epochs 10 --batch-size 4
```

The loader uses:

- `datasets/hls_cmds/processed/train/` for training
- `datasets/hls_cmds/processed/val/` for validation checkpoint selection
- `datasets/hls_cmds/processed/test/` only for final evaluation

The fine-tuned files are saved to:

```text
storage/ml_models/neossnet_hls_finetuned.pt
storage/ml_models/neossnet_hls_finetuned.yaml
```

When those files exist, `python scripts/init_db.py` registers `NeoSSNet HLS Fine-tuned` as an active method while keeping the original NeoSSNet checkpoint available. The fine-tuned model is not made the default automatically; final claims should be based on evaluation CSV results.

NeoSSNet remains a Python/PyTorch model. The training script uses 4000 Hz mono audio, 60000-sample segments, `(B, 1, T)` mixed inputs, and `(B, 2, T)` heart/lung targets.

## Evaluation Metrics

When uploaded audio exposes an HLS-CMDS ID such as `M0001.wav`, the service looks for:

```text
datasets/hls_cmds/raw/Mix/H0001.wav
datasets/hls_cmds/raw/Mix/L0001.wav
```

Then it stores real metrics in `evaluation_metric`:

- SDR
- SI-SDR
- SNR improvement
- MSE
- MAE
- correlation
- alignment lag in samples

Processing time, sample rate, duration, selected method, output paths, and job status are stored with each run.

SI-SDR is reported in dB, and higher values are better. Evaluation claims should be based on the generated CSV files, not on a single run or a single audio sample. The metric calculation uses a bounded alignment search for paired references so small timing offsets do not dominate the score.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Browser interface |
| `GET` | `/health` | Health check |
| `GET` | `/methods` | List separation methods |
| `GET` | `/models` | Backward-compatible alias for method registry |
| `POST` | `/upload` | Upload and store a WAV file |
| `POST` | `/separate/{audio_id}?model_id={id}` | Run selected separation method |
| `GET` | `/result/{job_id}` | Job, method, output, and metric details |
| `GET` | `/download/{job_id}/heart` | Download heart output WAV |
| `GET` | `/download/{job_id}/lung` | Download lung output WAV |
| `GET` | `/history` | Recent processing jobs |

## Testing

```powershell
pytest -q
python scripts/check_project.py
python scripts/test_neossnet_inference.py
python scripts/evaluate_strategies.py --max-samples 20
```

`scripts/test_neossnet_inference.py` runs a standalone NeoSSNet validation test through the same backend wrapper used by FastAPI. It prints sample rate, duration, tensor shapes, checkpoint/config paths, input/output min/max/RMS values, channel-order evidence, and paired-reference metrics when an HLS-CMDS test pair is available. It writes:

```text
storage/outputs/heart/test_heart.wav
storage/outputs/lung/test_lung.wav
```

`scripts/evaluate_strategies.py` compares selected methods on paired HLS-CMDS test samples and writes:

```text
evaluation/results_strategy_comparison.csv
evaluation/summary_strategy_comparison.csv
```

Useful evaluation commands:

```powershell
python scripts/evaluate_strategies.py --max-samples 20
python scripts/evaluate_strategies.py --max-samples 20 --strategies fixed_filter,nmf,vmd,neossnet
python scripts/evaluate_strategies.py --max-samples 20 --skip-slow
python scripts/evaluate_strategies.py --max-samples 20 --output-dir evaluation
```

After fine-tuning, rerun:

```powershell
python scripts/init_db.py
python scripts/evaluate_strategies.py --max-samples 23
```

The evaluator will list both `NeoSSNet Original` and `NeoSSNet HLS Fine-tuned` when the fine-tuned checkpoint/config are available.

The default VMD method uses the fast preset for the local web workflow. A quality preset is available in code as `vmd_quality` for experiments, but it is slower. Optional C++ acceleration was not added because profiling showed the Python fast preset reduced 15-second VMD processing from about 12 seconds to well under 1 second on the local machine. NeoSSNet remains Python/PyTorch.

## External Algorithm Notes

- NeoSSNet GitHub reference: `yangyipoh/Neonatal-Chest-Sound-Separation-using-Deep-Learning`. No explicit license file was found in the local/reference copy, so keep attribution and avoid redistributing it outside the project without checking.
- `vmdpy` is MIT licensed and is used for the VMD decomposition baseline.
- The NMF strategy is a practical NumPy implementation using standard multiplicative-update NMF on the magnitude spectrogram. It is not the MATLAB NMF/NMCF method from the NeoSSNet reference repository.
- Fixed Filter, NMF, and VMD are baseline/decomposition methods, not trained ML models.
