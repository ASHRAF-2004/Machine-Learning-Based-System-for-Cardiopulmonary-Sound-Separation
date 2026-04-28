INSERT INTO model (
    model_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    description
)
VALUES (
    'NeoSSNet',
    '1.0',
    'NeoSSNet',
    'PyTorch',
    'data/ml_models/neossnet.pth',
    'Cardiopulmonary sound separation model'
);