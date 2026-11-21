import json
import sqlite3
from contextlib import closing
from pathlib import Path

from app.manifest import describe, fingerprint, json_bytes
from app.pipeline import calculate
from app.problems import Problem

SCHEMA = Path(__file__).with_name('db.sql').read_text(encoding='utf-8')


class Archive:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA foreign_keys = ON')
        return db

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute('PRAGMA journal_mode = WAL')
            db.executescript(SCHEMA)

    def latest(self):
        with closing(self.connect()) as db:
            row = db.execute('SELECT snapshot FROM runs ORDER BY sequence DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else None

    def read(self, run_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT snapshot FROM runs WHERE id = ?', (run_id,)).fetchone()
        if not row:
            raise Problem('RUN_NOT_FOUND', 404, {'run_id': run_id})
        return json.loads(row[0])

    def sources(self, run_id):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT name, content FROM source_files WHERE run_id = ?', (run_id,)).fetchall()
        if not rows:
            raise Problem('RUN_NOT_FOUND', 404, {'run_id': run_id})
        return dict(rows)

    def publish(self, files):
        run_id = fingerprint(describe(files))
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT snapshot FROM runs WHERE id = ?', (run_id,)).fetchone()
            if existing:
                return json.loads(existing[0]), True
            snapshot = calculate(run_id, files)
            db.execute('INSERT INTO runs (id, snapshot) VALUES (?, ?)', (run_id, json_bytes(snapshot)))
            db.executemany('INSERT INTO source_files VALUES (?, ?, ?)', [(run_id, name, data) for name, data in files.items()])
        return snapshot, False
