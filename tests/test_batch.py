from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from app.archive import Archive


def test_parallel_identical_runs_write_one_manifest_and_four_raw_sources(tmp_path, files):
    path = tmp_path / 'parallel.sqlite3'
    archive = Archive(path)
    archive.initialize()
    with ThreadPoolExecutor(max_workers=6) as executor:
        runs = list(executor.map(lambda _: archive.publish(files), range(6)))
    assert [reused for _, reused in runs].count(False) == 1
    assert len({row['manifest']['run_id'] for row, _ in runs}) == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM runs').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM source_files').fetchone() == (4,)


def test_failure_during_raw_source_write_rolls_back_everything(tmp_path, files):
    path = tmp_path / 'fault.sqlite3'
    archive = Archive(path)
    archive.initialize()
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TRIGGER stop_raw BEFORE INSERT ON source_files
            WHEN NEW.name = 'passes.csv'
            BEGIN SELECT RAISE(ABORT, 'simulated disk write failure'); END;
        """)
    with pytest.raises(sqlite3.IntegrityError, match='simulated disk write failure'):
        archive.publish(files)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM runs').fetchone() == (0,)
        assert db.execute('SELECT count(*) FROM source_files').fetchone() == (0,)
        db.execute('DROP TRIGGER stop_raw')
    snapshot, reused = archive.publish(files)
    assert reused is False and snapshot['balance']['totals']['entry'] == 9


def test_changed_bytes_make_new_batch_and_rerun_old_keeps_latest(client, files, upload):
    old = client.post('/api/runs/sample').json()['run_id']
    newest = upload({**files, 'pulses.csv': files['pulses.csv'] + b'\n'})
    new = newest.json()['run_id']
    assert newest.status_code == 201 and old != new
    assert client.post(f'/api/runs/{old}/rerun').json()['run_id'] == old
    assert f'data-run="{new}"' in client.get('/').text


def test_reopen_database_preserves_manifest_and_raw_sources(tmp_path, files):
    path = tmp_path / 'restart.sqlite3'
    archive = Archive(path)
    archive.initialize()
    snapshot, _ = archive.publish(files)
    run_id = snapshot['manifest']['run_id']
    reopened = Archive(path)
    reopened.initialize()
    assert reopened.read(run_id) == snapshot
    assert reopened.sources(run_id) == files
