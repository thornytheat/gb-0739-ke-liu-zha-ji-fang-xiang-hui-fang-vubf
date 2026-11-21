import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from app.manifest import describe, fingerprint, json_bytes, sha
from app.modules.m8_review.service import REVIEW_DOWNGRADE_CODE, apply_review, shift_diff
from app.pipeline import calculate
from app.problems import MESSAGES, Problem

SCHEMA = Path(__file__).with_name('db.sql').read_text(encoding='utf-8')


def stamp():
    return datetime.now(UTC).isoformat(timespec='seconds')


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
            named = db.execute('SELECT name, content FROM source_files WHERE run_id = ?', (run_id,)).fetchall()
        if not named:
            raise Problem('RUN_NOT_FOUND', 404, {'run_id': run_id})
        return dict(named)

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
            db.execute('INSERT INTO run_revisions (run_id, revision_id, kind, snapshot, created_at) VALUES (?, ?, ?, ?, ?)',
                       (run_id, run_id, 'base', json_bytes(snapshot), stamp()))
        return snapshot, False

    def base_snapshot(self, db, run_id):
        row = db.execute(
            "SELECT snapshot FROM run_revisions WHERE run_id = ? AND kind = 'base' ORDER BY sequence LIMIT 1",
            (run_id,)).fetchone()
        if not row:
            raise Problem('RUN_NOT_FOUND', 404, {'run_id': run_id})
        return json.loads(row[0])

    def base_totals(self, run_id):
        with closing(self.connect()) as db:
            return self.base_snapshot(db, run_id)['balance']['totals']

    def active_note(self, db, run_id, ticket):
        row = db.execute(
            "SELECT note_id, kept_anchor, reason, status, period_start_ms, period_end_ms, revision_id "
            "FROM review_notes WHERE run_id = ? AND ticket = ? AND status IN ('recorded', 'confirmed')",
            (run_id, ticket)).fetchone()
        return row

    def review_notes(self, run_id):
        with closing(self.connect()) as db:
            rows = db.execute(
                'SELECT note_id, ticket, kept_anchor, period_start_ms, period_end_ms, reason, status, '
                'reject_reason, revision_id, created_at FROM review_notes WHERE run_id = ? ORDER BY sequence',
                (run_id,)).fetchall()
        keys = ('note_id', 'ticket', 'kept_anchor', 'period_start_ms', 'period_end_ms', 'reason', 'status',
                'reject_reason', 'revision_id', 'created_at')
        return [dict(zip(keys, row)) for row in rows]

    def shift_comparison(self, run_id):
        with closing(self.connect()) as db:
            base = self.base_snapshot(db, run_id)
            current = json.loads(db.execute('SELECT snapshot FROM runs WHERE id = ?', (run_id,)).fetchone()[0])
        return shift_diff(base['balance'], current['balance'])

    def submit_review(self, run_id, ticket, kept_anchor, period_start_ms, period_end_ms, reason):
        reason = reason.strip()
        if not reason:
            raise Problem('REVIEW_REASON')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            base = self.base_snapshot(db, run_id)
            legs = [row for row in base['transfers'] if row['is_transfer'] and row['ticket'] == ticket]
            if len(legs) < 2:
                raise Problem('REVIEW_TARGET')
            if not any(row['anchor'] == kept_anchor for row in legs):
                raise Problem('REVIEW_ANCHOR')
            span_start = min(row['anchor_ms'] for row in legs)
            span_end = max(row['at_ms'] for row in legs)
            if period_start_ms > span_start or period_end_ms < span_end:
                raise Problem('REVIEW_PERIOD', detail={'required_start_ms': span_start, 'required_end_ms': span_end})
            active = self.active_note(db, run_id, ticket)
            if active:
                if active[1] == kept_anchor and active[2] == reason:
                    return json.loads(db.execute('SELECT snapshot FROM runs WHERE id = ?', (run_id,)).fetchone()[0]), True
                raise Problem('REVIEW_CONFLICT', 409, {'note_id': active[0]})
            note_id = 'note_' + sha(json_bytes([run_id, ticket, kept_anchor, reason, period_start_ms, period_end_ms]))[:20]
            created = stamp()
            # 第一步：同票说明先独立落库并提交，后续确认失败也不丢记录。
            db.execute(
                'INSERT INTO review_notes (note_id, run_id, ticket, kept_anchor, period_start_ms, period_end_ms, '
                'reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (note_id, run_id, ticket, kept_anchor, period_start_ms, period_end_ms, reason, 'recorded', created))

        # 第二步：在独立事务里重算并发布新版班报；任何失败都回滚到旧版班报。
        try:
            with closing(self.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                transfers, balance, downgraded = apply_review(base, ticket, kept_anchor)
                adjusted = json.loads(json_bytes(base).decode())
                adjusted['transfers'] = transfers
                adjusted['balance'] = balance
                revision_id = 'rev_' + sha(json_bytes([run_id, note_id, created]))[:20]
                adjusted['manifest'] = {**base['manifest'], 'run_id': run_id, 'base_run_id': base['manifest']['run_id'],
                                        'revision_id': revision_id, 'reviewed_from': base['manifest']['run_id'],
                                        'reviewed_at': created}
                adjusted['review'] = {
                    'revision_id': revision_id, 'note_id': note_id, 'base_run_id': base['manifest']['run_id'],
                    'ticket': ticket, 'kept_anchor': kept_anchor, 'reason': reason, 'status': 'confirmed',
                    'confirmed_at': created, 'downgraded': downgraded,
                    'period': {'start_ms': period_start_ms, 'period_end_ms': period_end_ms},
                    'shift_diff': shift_diff(base['balance'], balance),
                }
                adjusted['reason_counts'] = {**base.get('reason_counts', {}),
                                             REVIEW_DOWNGRADE_CODE: len(downgraded)}
                snapshot_bytes = json_bytes(adjusted)
                db.execute('UPDATE runs SET snapshot = ? WHERE id = ?', (snapshot_bytes, run_id))
                db.execute('INSERT INTO run_revisions (run_id, revision_id, kind, snapshot, created_at) VALUES (?, ?, ?, ?, ?)',
                           (run_id, revision_id, 'review', snapshot_bytes, created))
                db.execute("UPDATE review_notes SET status = 'confirmed', revision_id = ? WHERE note_id = ?",
                           (revision_id, note_id))
        except Exception as exc:
            # 旧版班报由事务回滚保留；说明记录改写为驳回并留原因，记录本身不删除。
            message = MESSAGES.get(exc.code, str(exc)) if isinstance(exc, Problem) else str(exc)
            with closing(self.connect()) as db, db:
                db.execute("UPDATE review_notes SET status = 'rejected', reject_reason = ? WHERE note_id = ?",
                           (message, note_id))
            raise Problem('REVIEW_NOTE_FAILED', 409, {'note_id': note_id, 'reason': message})
        return adjusted, False
