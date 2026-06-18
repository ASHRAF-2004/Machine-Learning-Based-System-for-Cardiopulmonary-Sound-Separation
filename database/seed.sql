INSERT INTO model (
    model_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    config_path,
    description
)
SELECT
    'NeoSSNet',
    '1.0',
    'NeoSSNet',
    'PyTorch',
    'storage/ml_models/model_best.pt',
    'storage/ml_models/model.yaml',
    'Cardiopulmonary sound separation model'
WHERE NOT EXISTS (
    SELECT 1
    FROM model
    WHERE model_name = 'NeoSSNet'
      AND version = '1.0'
);

UPDATE model
SET
    checkpoint_path = 'storage/ml_models/model_best.pt',
    config_path = 'storage/ml_models/model.yaml'
WHERE model_name = 'NeoSSNet'
  AND version = '1.0'
  AND (
      checkpoint_path IS NULL
      OR checkpoint_path = ''
      OR checkpoint_path = 'data/ml_models/neossnet.pth'
      OR config_path IS NULL
      OR config_path = ''
  );

UPDATE model
SET is_active = 1
WHERE model_name = 'NeoSSNet'
  AND version = '1.0'
  AND NOT EXISTS (
      SELECT 1
      FROM model
      WHERE is_active = 1
  );
