from app.settings import BYTE_LIMIT


def test_bom_ticket_zeroes_and_multiline_note(sample):
    """TRAP-02 TRAP-03 TRAP-08"""
    record = next(row for row in sample['intake'] if row['pulse'] == 'TR-OUT-B')
    assert (record['ticket'], record['line'], record['last_line']) == ('00017', 2, 3)
    assert record['raw'][-1] == '北站手工补单\n闸机右侧出站'


def test_extra_column_retained_and_segment_headers_are_skipped(sample):
    """TRAP-04 TRAP-05"""
    record = next(row for row in sample['isolated'] if row['key'] == 'EXTRA')
    assert record['code'] == 'BAD_COLUMNS' and record['detail'] == {'expected': 7, 'actual': 8}
    stats = sample['balance']['sources'][0]
    assert (stats['headers'], stats['blanks'], stats['logical_rows']) == (2, 1, 45)


def test_equal_pulse_in_utc_is_a_retransmission(sample):
    """TRAP-11"""
    kept = next(row for row in sample['intake'] if row['pulse'] == 'TR-OUT-B')
    other, = sample['duplicates']
    assert other['raw'][4].endswith('Z') and kept['raw'][4].endswith('+08:00')
    assert other['device_ms'] == kept['device_ms']
    assert other['retained_line'] == 2


def test_same_pulse_with_two_different_beams_is_excluded(sample):
    """TRAP-14"""
    conflicts = [row for row in sample['isolated'] if row['code'] == 'PULSE_CONFLICT']
    assert {row['raw'][3] for row in conflicts} == {'A', 'B'}
    assert len(conflicts) == 2 and all(row['code'] == 'PULSE_CONFLICT' for row in conflicts)
    assert all(row['pulse'] != 'CONFLICT' for row in sample['intake'])


def test_missing_ticket_sentinels_are_null_and_remain_traceable(sample):
    """TRAP-07"""
    records = {row['pulse']: row for row in sample['intake']}
    assert records['TAIL-A2']['ticket'] is None and records['TAIL-A2']['raw'][5] == 'N/A'
    assert records['AN-R-A1']['ticket'] is None and records['AN-R-A1']['raw'][5] == '未知'


def test_intake_endpoint_exposes_the_kept_source_line(client):
    result = client.get('/api/intake/sample', params={'view': 'repeat', 'q': 'TR-OUT-B'}).json()
    assert result['total'] == 1
    assert result['items'][0]['retained_line'] == 2


def test_invalid_device_time_and_beam_each_have_a_reason(sample):
    records = {row['key']: row for row in sample['isolated']}
    assert records['BAD-TIME']['code'] == 'BAD_TIME'
    assert records['BAD-BEAM']['code'] == 'BAD_BEAM'


def test_empty_blank_truncated_and_overlong_uploads_have_distinct_results(upload, files):
    for payload, status, code in [(b'', 422, 'EMPTY_FILE'), (b'\n\n', 422, 'ONLY_BLANK'),
                                   (files['pulses.csv'] + b'"unfinished', 422, 'BAD_CSV'),
                                   (b'x' * (BYTE_LIMIT + 1), 413, 'FILE_LIMIT')]:
        response = upload({**files, 'pulses.csv': payload})
        assert (response.status_code, response.json()['code']) == (status, code)
