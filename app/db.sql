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
