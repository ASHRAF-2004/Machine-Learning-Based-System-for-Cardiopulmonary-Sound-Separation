-- Isolated DEVELOPMENT harness only. Never execute against cardiopulmonary.db.
CREATE TABLE af_meta (version INTEGER PRIMARY KEY CHECK (version = 1));
INSERT INTO af_meta VALUES (1);
CREATE TABLE af_users (
    id TEXT PRIMARY KEY,
    provider_uid TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('healthcare_staff','audio_analyst','admin')),
    status TEXT NOT NULL CHECK (status IN ('active','suspended','disabled')),
    email_verified INTEGER NOT NULL CHECK (email_verified IN (0,1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE af_recordings (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES af_users(id),
    created_at INTEGER NOT NULL
);
CREATE TABLE af_resources (
    id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL REFERENCES af_recordings(id),
    kind TEXT NOT NULL CHECK (kind IN
      ('original_audio','heart_audio','lung_audio','waveform','spectrogram','context','result')),
    UNIQUE (id, recording_id)
);
CREATE TABLE af_grants (
    id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL REFERENCES af_recordings(id),
    resource_id TEXT,
    grantor_id TEXT NOT NULL REFERENCES af_users(id),
    recipient_id TEXT NOT NULL REFERENCES af_users(id),
    permission TEXT NOT NULL CHECK (permission IN ('read','review')),
    status TEXT NOT NULL CHECK (status IN ('active','revoked')),
    expires_at INTEGER,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER,
    CHECK (grantor_id <> recipient_id),
    CHECK (permission <> 'review' OR resource_id IS NOT NULL),
    FOREIGN KEY (resource_id, recording_id) REFERENCES af_resources(id, recording_id)
);
CREATE INDEX af_grant_lookup ON af_grants(recipient_id, recording_id, status);
CREATE TABLE af_bootstrap (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    user_id TEXT NOT NULL UNIQUE REFERENCES af_users(id),
    created_at INTEGER NOT NULL
);
CREATE TABLE af_audit (
    id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
