import csv
import io
import json
from zipfile import ZipFile

from app.manifest import sha
from app.modules.m7_report.serializers import tabular


def export(client):
    identity = client.post('/api/runs/sample').json()['run_id']
    response = client.get(f'/api/report/{identity}/export')
    return identity, response, ZipFile(io.BytesIO(response.content))


def rows(bundle, name):
    return list(csv.DictReader(io.StringIO(bundle.read(f'evidence/{name}.csv').decode('utf-8-sig'))))


def test_published_manifest_names_inputs_parameters_and_run(client, files):
    run_id, response, bundle = export(client)
    with bundle:
        data = json.loads(bundle.read('manifest.json'))
        assert response.headers['content-disposition'] == f'attachment; filename="shift-{run_id}.zip"'
        assert data['run_id'] == run_id
        assert data['parameters'] == {'pair_ms': 900, 'return_ms': 250, 'shift_hours': [6, 14, 22]}
        assert {row['source']: row['sha256'] for row in data['inputs']} == {name: sha(raw) for name, raw in files.items()}


def test_zip_verification_covers_every_non_manifest_member(client):
    _, _, bundle = export(client)
    with bundle:
        data = json.loads(bundle.read('manifest.json'))
        entries = set(bundle.namelist()) - {'manifest.json'}
        assert set(data['member_sha256']) == entries and len(entries) == 13
        assert all(data['member_sha256'][name] == sha(bundle.read(name)) for name in entries)


def test_transfer_export_keeps_text_ticket_and_exit_trace(client):
    _, _, bundle = export(client)
    with bundle:
        moved = next(row for row in rows(bundle, 'transfers') if row['code'] == 'TRANSFER')
        assert (moved['ticket'], moved['anchor'], moved['gap_ms']) == ('00017', 'E-TR-OUT-B', '90100')
        assert moved['link_line'] == '2' and moved['anchor_line'] == '6'


def test_evidence_keeps_raw_bytes_and_bad_value(client, files):
    _, _, bundle = export(client)
    with bundle:
        assert all(bundle.read(f'input/{name}') == value for name, value in files.items())
        issue = next(row for row in rows(bundle, 'isolated') if row['code'] == 'BAD_INTEGER')
        assert json.loads(issue['raw'])[-1] == '待校'


def test_exported_direction_and_rollup_are_consistent(client):
    _, _, bundle = export(client)
    with bundle:
        shift_rows = rows(bundle, 'shifts')
        assert sum(int(row['unique_entries']) for row in shift_rows) == 8
        by_kind = rows(bundle, 'direction')
        assert [x['pattern'] for x in by_kind if x['direction'] == 'return'] == ['B→A→B']
        assert all(int(row['pulse_difference']) == 0 for row in shift_rows)


def test_report_json_filters_published_quarantine_without_preview_export(client):
    response = client.get('/api/report/sample', params={'view': 'isolated', 'q': 'CLOCK-MISSING'})
    row, = response.json()['items']
    assert (row['code'], row['stage']) == ('CLOCK_GAP', 'clock')
    unavailable = client.get('/api/report/sample/export')
    assert (unavailable.status_code, unavailable.json()['code']) == (404, 'RUN_NOT_FOUND')


def test_csv_formula_cells_are_text_and_negative_offsets_stay_numeric():
    raw = tabular([{'note': ' @CMD', 'offset_ms': -200}], ('note', 'offset_ms'))
    row, = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    assert row == {'note': "' @CMD", 'offset_ms': '-200'}
