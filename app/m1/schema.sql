CREATE TABLE m1_meta (version INTEGER PRIMARY KEY CHECK(version=1));
INSERT INTO m1_meta VALUES(1);
CREATE TABLE m1_recording_data (
 recording_id TEXT PRIMARY KEY REFERENCES af_recordings(id),
 title TEXT NOT NULL, original_filename TEXT NOT NULL,
 duration_sec REAL NOT NULL, sample_rate_hz INTEGER NOT NULL,
 channels INTEGER NOT NULL, file_size_bytes INTEGER NOT NULL,
 original_resource_id TEXT NOT NULL REFERENCES af_resources(id)
);
CREATE TABLE m1_files (
 resource_id TEXT PRIMARY KEY REFERENCES af_resources(id),
 relative_path TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL, file_size_bytes INTEGER NOT NULL
);
CREATE TABLE m1_jobs (
 id TEXT PRIMARY KEY, recording_id TEXT NOT NULL REFERENCES af_recordings(id),
 requester_id TEXT NOT NULL REFERENCES af_users(id), status TEXT NOT NULL,
 created_at INTEGER NOT NULL, completed_at INTEGER, error_code TEXT
);
CREATE TABLE m1_results (
 id TEXT PRIMARY KEY REFERENCES af_resources(id),
 recording_id TEXT NOT NULL REFERENCES af_recordings(id), job_id TEXT NOT NULL UNIQUE REFERENCES m1_jobs(id),
 created_at INTEGER NOT NULL, method_label TEXT NOT NULL
);
CREATE TABLE m1_result_files (
 result_id TEXT NOT NULL REFERENCES m1_results(id), resource_id TEXT NOT NULL REFERENCES af_resources(id),
 PRIMARY KEY(result_id,resource_id)
);
CREATE TABLE m1_reviews (
 assignment_id TEXT PRIMARY KEY REFERENCES af_grants(id),
 resource_id TEXT NOT NULL REFERENCES af_resources(id), reviewer_id TEXT NOT NULL REFERENCES af_users(id),
 decision TEXT NOT NULL CHECK(decision IN ('pending','accepted','needs_attention')),
 notes TEXT NOT NULL, updated_at INTEGER NOT NULL
);
CREATE TABLE m1_preferences (
 user_id TEXT PRIMARY KEY REFERENCES af_users(id), preferences_json TEXT NOT NULL
);
