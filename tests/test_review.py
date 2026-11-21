import sqlite3

import pytest


@pytest.fixture
def shared_ticket_run(client, csv_builder):
    pulses = []
    beams = {
        'T01-O1': ('NTH', 'B', 'A', '2026-11-20T07:10:00'),
        'T01-I1': ('STH', 'A', 'B', '2026-11-20T07:13:00'),
        'T01-O2': ('NTH', 'B', 'A', '2026-11-20T07:30:00'),
        'T01-I2': ('STH', 'A', 'B', '2026-11-20T07:34:00'),
        'T02-O': ('NTH', 'B', 'A', '2026-11-20T08:00:00'),
        'T02-I': ('STH', 'A', 'B', '2026-11-20T08:05:00'),
    }
    lines = []
    for prefix, (station, first, second, stamp) in beams.items():
        ticket = prefix.split('-')[0]
        lines.append([f'{prefix}-{first}', station, 'G1', first, f'{stamp}.000+08:00', ticket, ''])
        lines.append([f'{prefix}-{second}', station, 'G1', second, f'{stamp}.200+08:00', ticket, ''])
    files = {
        'pulses.csv': csv_builder('pulses.csv', lines),
        'offsets.csv': csv_builder('offsets.csv', [
            ['NTH', 'G1', '2026-11-20T06:00:00+08:00', '2026-11-20T10:00:00+08:00', '0'],
            ['STH', 'G1', '2026-11-20T06:00:00+08:00', '2026-11-20T10:00:00+08:00', '0'],
        ]),
        'passes.csv': csv_builder('passes.csv', [
            ['T01', '2026-11-20T06:00:00+08:00', '2026-11-20T10:00:00+08:00', 'yes'],
            ['T02', '2026-11-20T06:00:00+08:00', '2026-11-20T10:00:00+08:00', 'yes'],
        ]),
        'links.csv': csv_builder('links.csv', [['NTH', 'STH', '60', '1800']]),
    }
    response = client.post('/api/runs', files=[('files', (name, data, 'text/csv')) for name, data in files.items()])
    assert response.status_code == 201
    return response.json()['run_id']


@pytest.fixture
def review_payload(client, shared_ticket_run):
    run_id = shared_ticket_run
    group = client.get(f'/api/review/{run_id}').json()['items'][0]
    return run_id, group, {
        'ticket': 'T01', 'kept_anchor': group['legs'][0]['anchor'],
        'period_start_ms': group['period_start_ms'], 'period_end_ms': group['period_end_ms'],
        'reason': '早高峰两名乘客借用同一张票，按现场实际两人交班',
    }


def test_groups_list_only_tickets_with_multiple_transfers(client, shared_ticket_run):
    data = client.get(f'/api/review/{shared_ticket_run}').json()
    assert data['total'] == 1
    group = data['items'][0]
    assert group['ticket'] == 'T01' and len(group['legs']) == 2
    assert [leg['anchor'] for leg in group['legs']] == ['E-T01-O1-B', 'E-T01-O2-B']
    assert all(leg['review_status'] == '' for leg in group['legs'])
    assert client.get(f'/api/review/{shared_ticket_run}', params={'view': 'notes'}).json()['total'] == 0


def test_review_keeps_one_transfer_and_downgrades_other_to_independent(client, review_payload):
    run_id, group, payload = review_payload
    before = client.get(f'/api/balance/{run_id}').json()['totals']
    assert (before['entry'], before['exit'], before['transfer_in'], before['transfer_out'],
            before['unique_entries']) == (3, 3, 3, 3, 0)

    response = client.post(f'/api/review/{run_id}/notes', json=payload)
    assert response.status_code == 201 and response.json()['reused'] is False
    after = response.json()['totals']
    assert (after['entry'], after['exit'], after['transfer_in'], after['transfer_out'],
            after['unique_entries'], after['transfer_net']) == (3, 3, 2, 2, 1, 0)

    rows = client.get(f'/api/transfer/{run_id}').json()['items']
    t01 = {row['encounter']: row for row in rows if row['ticket'] == 'T01'}
    kept, downgraded = t01['E-T01-I1-A'], t01['E-T01-I2-A']
    assert kept['is_transfer'] is True and kept['code'] == 'TRANSFER' and kept['review_status'] == 'kept'
    assert (downgraded['is_transfer'], downgraded['unique_entry'], downgraded['anchor']) == (False, 1, None)
    assert downgraded['code'] == 'REVIEW_DOWNGRADED' and downgraded['review_status'] == 'REVIEW_DOWNGRADED'
    # 对照票 T02 的单段换乘不受影响
    t02 = next(row for row in rows if row['ticket'] == 'T02')
    assert t02['is_transfer'] is True

    balance = client.get(f'/api/balance/{run_id}').json()
    assert balance['balanced'] is True and balance['checks'] == {
        'sources': True, 'pulse_ids': True, 'shifts': True, 'transfers': True}


def test_review_shift_comparison_reports_before_after_and_delta(client, review_payload):
    run_id, _, payload = review_payload
    client.post(f'/api/review/{run_id}/notes', json=payload)
    diffs = client.get(f'/api/review/{run_id}', params={'view': 'shifts'}).json()['items']
    changed = {(row['station'], field): row[field] for row in diffs if row['changed'] for field in
               ('transfer_in', 'transfer_out', 'transfer_net', 'unique_entries', 'physical_net', 'nontransfer_net')}
    nth_out, sth_in = changed[('NTH', 'transfer_out')], changed[('STH', 'transfer_in')]
    assert (nth_out['before'], nth_out['after'], nth_out['delta']) == (3, 2, -1)
    assert (sth_in['before'], sth_in['after'], sth_in['delta']) == (3, 2, -1)
    assert changed[('STH', 'unique_entries')]['delta'] == 1
    assert changed[('NTH', 'physical_net')]['delta'] == 0
    assert changed[('NTH', 'transfer_net')]['delta'] == 1 and changed[('STH', 'transfer_net')]['delta'] == -1


def test_same_note_resubmission_is_idempotent_and_rerun_never_double_adjusts(client, review_payload):
    run_id, _, payload = review_payload
    first = client.post(f'/api/review/{run_id}/notes', json=payload)
    second = client.post(f'/api/review/{run_id}/notes', json=payload)
    assert second.status_code == 200 and second.json()['reused'] is True
    assert second.json()['totals'] == first.json()['totals']

    rerun = client.post(f'/api/runs/{run_id}/rerun')
    assert rerun.status_code == 200 and rerun.json()['reused'] is True
    assert rerun.json()['totals']['transfer_in'] == 2
    notes = client.get(f'/api/review/{run_id}', params={'view': 'notes'}).json()['items']
    assert len(notes) == 1 and notes[0]['status'] == 'confirmed'


def test_conflicting_note_for_same_ticket_is_rejected_without_changing_report(client, review_payload):
    run_id, group, payload = review_payload
    client.post(f'/api/review/{run_id}/notes', json=payload)
    conflict = client.post(f'/api/review/{run_id}/notes',
                           json={**payload, 'kept_anchor': group['legs'][1]['anchor'], 'reason': '想改认第二段'})
    assert conflict.status_code == 409 and conflict.json()['code'] == 'REVIEW_CONFLICT'
    totals = client.get(f'/api/balance/{run_id}').json()['totals']
    assert totals['transfer_in'] == 2
    assert len(client.get(f'/api/review/{run_id}', params={'view': 'notes'}).json()['items']) == 1


def test_invalid_target_anchor_and_period_are_refused(client, review_payload):
    run_id, group, payload = review_payload
    bad_anchor = client.post(f'/api/review/{run_id}/notes', json={**payload, 'kept_anchor': 'E-T02-O-B'})
    assert bad_anchor.status_code == 422 and bad_anchor.json()['code'] == 'REVIEW_ANCHOR'
    bad_period = client.post(f'/api/review/{run_id}/notes',
                             json={**payload, 'period_end_ms': group['period_start_ms']})
    assert bad_period.status_code == 422 and bad_period.json()['code'] == 'REVIEW_PERIOD'
    empty_reason = client.post(f'/api/review/{run_id}/notes', json={**payload, 'reason': '   '})
    assert empty_reason.status_code == 422 and empty_reason.json()['code'] == 'REVIEW_REASON'
    # 全部被拒，班报维持原始口径
    assert client.get(f'/api/balance/{run_id}').json()['totals']['transfer_in'] == 3


def test_ticket_without_multiple_transfers_cannot_be_reviewed(client, review_payload):
    run_id, _, payload = review_payload
    response = client.post(f'/api/review/{run_id}/notes', json={**payload, 'ticket': 'T02'})
    assert response.status_code == 422 and response.json()['code'] == 'REVIEW_TARGET'


def test_confirmation_failure_restores_old_report_but_keeps_note_record(client, review_payload, tmp_path):
    run_id, _, payload = review_payload
    db_path = tmp_path / 'fault.sqlite3'
    # 客户端与服务端共用同一个 sqlite 文件，直接在文件上加触发器。
    fetched = client.app.state.archive
    target = fetched.path
    with sqlite3.connect(target) as db:
        db.executescript("""
            CREATE TRIGGER stop_review BEFORE UPDATE OF snapshot ON runs
            BEGIN SELECT RAISE(ABORT, 'simulated snapshot write failure'); END;
        """)
    failed = client.post(f'/api/review/{run_id}/notes', json=payload)
    assert failed.status_code == 409 and failed.json()['code'] == 'REVIEW_NOTE_FAILED'
    assert client.get(f'/api/balance/{run_id}').json()['totals']['transfer_in'] == 3
    notes = client.get(f'/api/review/{run_id}', params={'view': 'notes'}).json()['items']
    assert len(notes) == 1 and notes[0]['status'] == 'rejected'
    assert notes[0]['reject_reason'] == 'simulated snapshot write failure'
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT count(*) FROM run_revisions WHERE kind = 'review'").fetchone()[0] == 0
        db.execute('DROP TRIGGER stop_review')
    retry = client.post(f'/api/review/{run_id}/notes', json={**payload, 'reason': '故障恢复后重新复核'})
    assert retry.status_code == 201 and retry.json()['totals']['transfer_in'] == 2
    statuses = [row['status'] for row in client.get(f'/api/review/{run_id}', params={'view': 'notes'}).json()['items']]
    assert statuses == ['rejected', 'confirmed']


def test_preview_snapshot_refuses_review(client, review_payload):
    _, _, payload = review_payload
    response = client.post('/api/review/sample/notes', json=payload)
    assert response.status_code == 409 and response.json()['code'] == 'REVIEW_PREVIEW'
    groups = client.get('/api/review/sample').json()
    assert groups['total'] == 0 and groups['review'] is None


def test_export_zip_contains_review_evidence_and_manifest_hash(client, review_payload):
    import io
    import csv
    from zipfile import ZipFile
    run_id, _, payload = review_payload
    client.post(f'/api/review/{run_id}/notes', json=payload)
    response = client.get(f'/api/report/{run_id}/export')
    with ZipFile(io.BytesIO(response.content)) as bundle:
        names = set(bundle.namelist())
        assert {'evidence/review-notes.csv', 'evidence/shift-review-diff.csv'} <= names
        diff_rows = list(csv.DictReader(io.StringIO(
            bundle.read('evidence/shift-review-diff.csv').decode('utf-8-sig'))))
        transfer_in = next(row for row in diff_rows if row['station'] == 'STH' and row['metric'] == 'transfer_in')
        assert (transfer_in['before'], transfer_in['after'], transfer_in['delta']) == ('3', '2', '-1')
        note_rows = list(csv.DictReader(io.StringIO(
            bundle.read('evidence/review-notes.csv').decode('utf-8-sig'))))
        assert note_rows[0]['ticket'] == 'T01' and note_rows[0]['status'] == 'confirmed'
        transfer_rows = list(csv.DictReader(io.StringIO(
            bundle.read('evidence/transfers.csv').decode('utf-8-sig'))))
        downgraded = next(row for row in transfer_rows if row['code'] == 'REVIEW_DOWNGRADED')
        assert downgraded['is_transfer'] == 'False' and downgraded['unique_entry'] == '1'


def test_home_page_renders_review_panel_and_ticket_conclusions(client, review_payload):
    run_id, _, payload = review_payload
    pending = client.get(f'/?run={run_id}').text
    assert '票号复核' in pending and 'T01' in pending and '待复核' in pending
    client.post(f'/api/review/{run_id}/notes', json=payload)
    confirmed = client.get(f'/?run={run_id}').text
    assert '认换乘（保留段）' in confirmed and '独立进出交班' in confirmed
    assert '重算前换乘进 / 出' in confirmed and '已生效复核' in confirmed
