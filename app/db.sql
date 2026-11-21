CREATE TABLE IF NOT EXISTS runs (
    sequence INTEGER PRIMARY KEY,
    id TEXT UNIQUE NOT NULL,
    snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_files (
    run_id TEXT NOT NULL REFERENCES runs(id),
    name TEXT NOT NULL,
    content BLOB NOT NULL,
    PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS run_revisions (
    sequence INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    revision_id TEXT UNIQUE NOT NULL,
    kind TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_notes (
    sequence INTEGER PRIMARY KEY,
    note_id TEXT UNIQUE NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(id),
    ticket TEXT NOT NULL,
    kept_anchor TEXT NOT NULL,
    period_start_ms INTEGER NOT NULL,
    period_end_ms INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    reject_reason TEXT,
    revision_id TEXT,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS review_active_note
    ON review_notes(run_id, ticket) WHERE status IN ('recorded', 'confirmed');
