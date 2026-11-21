from app.fields import timestamp


def test_gb18030_fallback_preserves_dirty_calibration_value(sample):
    """TRAP-01"""
    info = sample['balance']['sources'][1]
    row = next(row for row in sample['isolated'] if row['code'] == 'BAD_INTEGER')
    assert info['encoding'] == 'gb18030'
    assert row['raw'][-1] == '待校'


def test_offset_signs_restore_utc_across_dates(sample):
    aligned = {item['pulse']: item for item in sample['aligned']}
    north = aligned['TR-OUT-B']
    south = aligned['TR-IN-A']
    assert north['device_ms'] - north['corrected_ms'] == 120
    assert south['device_ms'] - south['corrected_ms'] == -200
    assert south['corrected_ms'] == timestamp('2026-11-20T00:00:00.200+08:00')


def test_end_of_old_clock_interval_is_start_of_new_clock_version(sample):
    """TRAP-23"""
    row = next(item for item in sample['aligned'] if item['pulse'] == 'IN-N-A')
    assert row['device_ms'] == timestamp('2026-11-20T00:00:00+08:00')
    assert (row['offset_line'], row['offset_ms']) == (3, -80)
    assert row['corrected_ms'] == row['device_ms'] + 80


def test_intersecting_clock_versions_quarantine_only_overlap(sample):
    """TRAP-25"""
    assert 'WEST-OK-A' in {row['pulse'] for row in sample['aligned']}
    rejected = next(row for row in sample['isolated'] if row['key'] == 'WEST-OVERLAP')
    assert rejected['code'] == 'CLOCK_OVERLAP'
    assert set(rejected['detail']['offset_lines']) == {6, 7}
    region = next(row for row in sample['overlaps'] if row['station'] == 'WST')
    assert region['end_ms'] - region['start_ms'] == 180_000


def test_conflicting_same_window_does_not_fall_back_to_broader_version(sample):
    row = next(row for row in sample['isolated'] if row['key'] == 'CLOCK-CLASH')
    assert row['code'] == 'CLOCK_OVERLAP'
    assert set(row['detail']['offset_lines']) == {8, 9, 10}
    assert 'CLOCK-CLASH' not in {item['pulse'] for item in sample['aligned']}


def test_missing_version_never_assumes_zero_drift(sample):
    row = next(row for row in sample['isolated'] if row['key'] == 'CLOCK-MISSING')
    assert (row['stage'], row['code'], row['detail']) == ('clock', 'CLOCK_GAP', {'offset_lines': []})


def test_clock_endpoint_shows_joined_source_and_offset_line(client):
    result = client.get('/api/clock/sample', params={'q': 'TR-OUT-B'}).json()
    assert result['total'] == 1
    row, = result['items']
    assert (row['line'], row['offset_line'], row['offset_ms']) == (2, 2, 120)


def test_empty_clock_table_fails_without_manufacturing_direction(files, csv_builder, upload):
    response = upload({**files, 'offsets.csv': csv_builder('offsets.csv', [])})
    assert (response.status_code, response.json()['code']) == (422, 'NO_CLOCKED')
