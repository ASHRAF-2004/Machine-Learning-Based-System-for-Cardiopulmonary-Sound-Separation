INSERT INTO model (
    model_name,
    display_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    config_path,
    strategy_key,
    method_type,
    requires_checkpoint,
    is_active,
    is_default,
    description
)
SELECT
    'Fixed Filter Baseline',
    'Fixed Filter Baseline',
    '1.0',
    'FixedFilter',
    'Signal Processing',
    'builtin://fixed_filter',
    NULL,
    'fixed_filter',
    'baseline',
    0,
    1,
    0,
    'Conventional frequency-mask baseline for workflow testing and comparison.'
WHERE NOT EXISTS (
    SELECT 1
    FROM model
    WHERE strategy_key = 'fixed_filter'
       OR checkpoint_path = 'builtin://fixed_filter'
);

INSERT INTO model (
    model_name,
    display_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    config_path,
    strategy_key,
    method_type,
    requires_checkpoint,
    is_active,
    is_default,
    description
)
SELECT
    'NMF Decomposition',
    'NMF Decomposition',
    '1.0',
    'NMF',
    'NumPy',
    'builtin://nmf',
    NULL,
    'nmf',
    'decomposition',
    0,
    1,
    0,
    'Unsupervised NMF spectrogram decomposition baseline; not a trained ML model.'
WHERE NOT EXISTS (
    SELECT 1
    FROM model
    WHERE strategy_key = 'nmf'
       OR checkpoint_path = 'builtin://nmf'
);

INSERT INTO model (
    model_name,
    display_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    config_path,
    strategy_key,
    method_type,
    requires_checkpoint,
    is_active,
    is_default,
    description
)
SELECT
    'VMD Decomposition',
    'VMD Decomposition',
    '1.0',
    'VMD',
    'vmdpy',
    'builtin://vmd',
    NULL,
    'vmd',
    'decomposition',
    0,
    1,
    0,
    'Variational mode decomposition baseline using vmdpy; not a trained ML model.'
WHERE NOT EXISTS (
    SELECT 1
    FROM model
    WHERE strategy_key = 'vmd'
       OR checkpoint_path = 'builtin://vmd'
);

INSERT INTO model (
    model_name,
    display_name,
    version,
    architecture,
    framework,
    checkpoint_path,
    config_path,
    strategy_key,
    method_type,
    requires_checkpoint,
    is_active,
    is_default,
    description
)
SELECT
    'NeoSSNet',
    'NeoSSNet',
    '1.0',
    'NeoSSNet',
    'PyTorch',
    'storage/ml_models/model_best.pt',
    'storage/ml_models/model.yaml',
    'neossnet',
    'deep_learning',
    1,
    1,
    1,
    'Cardiopulmonary sound separation model'
WHERE NOT EXISTS (
    SELECT 1
    FROM model
    WHERE model_name = 'NeoSSNet'
      AND version = '1.0'
);

UPDATE model
SET
    display_name = COALESCE(display_name, 'NeoSSNet'),
    checkpoint_path = 'storage/ml_models/model_best.pt',
    config_path = 'storage/ml_models/model.yaml',
    strategy_key = 'neossnet',
    method_type = 'deep_learning',
    requires_checkpoint = 1,
    is_default = 1
WHERE model_name = 'NeoSSNet'
  AND version = '1.0'
  AND (
      checkpoint_path IS NULL
      OR checkpoint_path = ''
      OR checkpoint_path = 'data/ml_models/neossnet.pth'
      OR config_path IS NULL
      OR config_path = ''
      OR strategy_key IS NULL
      OR strategy_key = ''
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

UPDATE model
SET is_default = CASE
    WHEN model_name = 'NeoSSNet' AND version = '1.0' THEN 1
    ELSE 0
END
WHERE strategy_key IN ('fixed_filter', 'nmf', 'vmd', 'neossnet')
   OR (model_name = 'NeoSSNet' AND version = '1.0');

UPDATE model
SET is_default = 0
WHERE strategy_key <> 'neossnet'
  AND EXISTS (
      SELECT 1
      FROM model
      WHERE strategy_key = 'neossnet'
        AND is_default = 1
  );
