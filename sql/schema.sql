CREATE TABLE recordings (id TEXT PRIMARY KEY, filepath TEXT, sample_rate INT, duration FLOAT);
CREATE TABLE results (id TEXT PRIMARY KEY, recording_id TEXT, heart_path TEXT, lung_path TEXT, sdr FLOAT);
CREATE TABLE model_configs (id TEXT PRIMARY KEY, name TEXT, version TEXT, onnx_path TEXT);
