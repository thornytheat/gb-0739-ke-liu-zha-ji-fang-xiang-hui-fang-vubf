from app.modules.m3_pairing.service import pair


def pulse_ids(encounter):
    return [row['pulse'] for row in encounter['pulses']]


def test_out_of_order_source_uses_corrected_time_and_keeps_each_source_line(sample):
    """TRAP-13"""
    first = next(item for item in sample['pairs'] if item['encounter'] == 'E-TR-IN-A')
    assert pulse_ids(first) == ['TR-IN-A', 'TR-IN-B']
    assert [row['line'] for row in first['pulses']] == [5, 4]


def test_tailgating_uses_fifo_instead_of_the_closest_beam(sample):
    one, two = [row for row in sample['pairs'] if row['encounter'].startswith('E-TAIL')]
    assert pulse_ids(one) == ['TAIL-A1', 'TAIL-B1']
    assert pulse_ids(two) == ['TAIL-A2', 'TAIL-B2']
    assert one['end_ms'] - one['start_ms'] == 190
    assert two['end_ms'] - two['start_ms'] == 230


def test_pairing_honors_maximum_inclusive_gap(pulses):
    encounters = pair(pulses([('A', 100, '1'), ('B', 1000, '1'), ('A', 2100, '2'), ('B', 3001, '2')]))
    assert [(row['kind'], pulse_ids(row)) for row in encounters] == [('pair', ['P0', 'P1']), ('orphan', ['P2']), ('orphan', ['P3'])]
    assert encounters[1]['code'] == 'ORPHAN_TIMEOUT'


def test_tie_frame_splits_pending_window(sample):
    orphan = next(row for row in sample['pairs'] if row['encounter'] == 'E-OR-CUT')
    tie = next(row for row in sample['pairs'] if row['kind'] == 'tie')
    assert orphan['code'] == 'ORPHAN_TIE_BOUNDARY'
    assert pulse_ids(tie) == ['TIE-A', 'TIE-B']
    assert tie['start_ms'] == tie['end_ms']


def test_distinct_tickets_cannot_form_one_passage(pulses):
    result = pair(pulses([('A', 10, '0001'), ('B', 30, '0002'), ('B', 60, '0001')]))
    assert [(row['ticket'], pulse_ids(row)) for row in result] == [('0001', ['P0', 'P2']), ('0002', ['P1'])]


def test_tailgating_with_following_new_start_is_not_mistaken_for_return(pulses):
    result = pair(pulses([('A', 10, None), ('A', 30, None), ('B', 90, None), ('B', 110, None), ('A', 160, None)]))
    assert [(row['kind'], pulse_ids(row)) for row in result] == [('pair', ['P0', 'P2']), ('pair', ['P1', 'P3']), ('orphan', ['P4'])]


def test_pair_endpoint_reports_timeout_evidence(client):
    result = client.get('/api/pairing/sample', params={'view': 'orphans', 'q': 'TIMEOUT-A'}).json()
    row, = result['items']
    assert row['code'] == 'ORPHAN_TIMEOUT' and row['pulses'][0]['pulse'] == 'TIMEOUT-A'
