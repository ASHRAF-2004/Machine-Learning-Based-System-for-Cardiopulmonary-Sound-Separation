  PRAGMA foreign_keys = ON;

  CREATE TABLE IF NOT EXISTS uploaded_audio (
      uploaded_audio_id INTEGER PRIMARY KEY,
      original_filename TEXT NOT NULL,
      stored_path TEXT NOT NULL UNIQUE,
      file_hash TEXT UNIQUE,
      mime_type TEXT NOT NULL DEFAULT 'audio/wav',
      sample_rate_hz INTEGER,
      channels INTEGER CHECK (channels > 0),
      bit_depth INTEGER CHECK (bit_depth > 0),
      duration_sec REAL CHECK (duration_sec >= 0),
      file_size_bytes INTEGER CHECK (file_size_bytes >= 0),
      uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      notes TEXT
  );

  CREATE TABLE IF NOT EXISTS model (
      model_id INTEGER PRIMARY KEY,
      model_name TEXT NOT NULL,
      display_name TEXT,
      version TEXT NOT NULL,
      architecture TEXT NOT NULL DEFAULT 'NeoSSNet',
      framework TEXT NOT NULL DEFAULT 'PyTorch',
      checkpoint_path TEXT NOT NULL UNIQUE,
      config_path TEXT,
      strategy_key TEXT,
      method_type TEXT NOT NULL DEFAULT 'deep_learning' CHECK (
          method_type IN ('baseline', 'decomposition', 'deep_learning')
      ),
      requires_checkpoint INTEGER NOT NULL DEFAULT 1 CHECK (
          requires_checkpoint IN (0, 1)
      ),
      description TEXT,
      is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
      is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE (model_name, version)
  );

  CREATE TABLE IF NOT EXISTS separation_job (
      job_id INTEGER PRIMARY KEY,
      uploaded_audio_id INTEGER NOT NULL,
      model_id INTEGER NOT NULL,
      status TEXT NOT NULL CHECK (
          status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')
      ),
      requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      started_at TEXT,
      completed_at TEXT,
      processing_time_ms INTEGER CHECK (
          processing_time_ms IS NULL OR processing_time_ms >= 0
      ),
      parameters_json TEXT,
      error_message TEXT,
      FOREIGN KEY (uploaded_audio_id)
          REFERENCES uploaded_audio(uploaded_audio_id)
          ON DELETE RESTRICT,
      FOREIGN KEY (model_id)
          REFERENCES model(model_id)
          ON DELETE RESTRICT
  );

  CREATE TABLE IF NOT EXISTS separation_result (
      result_id INTEGER PRIMARY KEY,
      job_id INTEGER NOT NULL UNIQUE,
      heart_file_path TEXT NOT NULL UNIQUE,
      lung_file_path TEXT NOT NULL UNIQUE,
      output_sample_rate_hz INTEGER,
      output_duration_sec REAL CHECK (output_duration_sec >= 0),
      heart_file_size_bytes INTEGER CHECK (heart_file_size_bytes >= 0),
      lung_file_size_bytes INTEGER CHECK (lung_file_size_bytes >= 0),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (job_id)
          REFERENCES separation_job(job_id)
          ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS evaluation_metric (
      metric_id INTEGER PRIMARY KEY,
      result_id INTEGER NOT NULL,
      metric_name TEXT NOT NULL,
      metric_scope TEXT NOT NULL CHECK (
          metric_scope IN ('heart', 'lung', 'overall')
      ),
      metric_value REAL NOT NULL,
      metric_unit TEXT,
      reference_type TEXT,
      recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (result_id)
          REFERENCES separation_result(result_id)
          ON DELETE CASCADE,
      UNIQUE (result_id, metric_name, metric_scope)
  );

  CREATE TABLE IF NOT EXISTS system_log (
      log_id INTEGER PRIMARY KEY,
      job_id INTEGER,
      log_level TEXT NOT NULL CHECK (
          log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR')
      ),
      source_component TEXT NOT NULL CHECK (
          source_component IN ('frontend', 'api', 'ml_model', 'database', 'filesystem', 'system')
      ),
      event_type TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (job_id)
          REFERENCES separation_job(job_id)
          ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS idx_uploaded_audio_uploaded_at
      ON uploaded_audio(uploaded_at DESC);

  CREATE INDEX IF NOT EXISTS idx_separation_job_status_requested
      ON separation_job(status, requested_at DESC);

  CREATE INDEX IF NOT EXISTS idx_separation_job_uploaded_audio
      ON separation_job(uploaded_audio_id);

  CREATE INDEX IF NOT EXISTS idx_separation_job_model
      ON separation_job(model_id);

  CREATE INDEX IF NOT EXISTS idx_separation_result_created_at
      ON separation_result(created_at DESC);

  CREATE INDEX IF NOT EXISTS idx_evaluation_metric_result_name
      ON evaluation_metric(result_id, metric_name);

  CREATE INDEX IF NOT EXISTS idx_system_log_job_created_at
      ON system_log(job_id, created_at DESC);

  CREATE INDEX IF NOT EXISTS idx_system_log_level_created_at
      ON system_log(log_level, created_at DESC);
