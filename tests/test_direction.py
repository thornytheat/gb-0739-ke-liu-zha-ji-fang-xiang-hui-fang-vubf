from app.modules.m3_pairing.service import pair
from app.modules.m4_direction.service import classify


def test_opposite_order_meaning_is_not_interchangeable(sample):
    rows = {row['encounter']: row for row in sample['direction']}
    assert (rows['E-TR-IN-A']['pattern'], rows['E-TR-IN-A']['direction']) == ('A→B', 'entry')
    assert (rows['E-TR-OUT-B']['pattern'], rows['E-TR-OUT-B']['direction']) == ('B→A', 'exit')


def test_same_ticket_return_is_single_three_pulse_encounter(sample):
    row = next(row for row in sample['direction'] if row['encounter'] == 'E-RF-B1')
    assert (row['direction'], row['pattern'], row['duration_ms']) == ('return', 'B→A→B', 320)
    assert row['code'] == 'RETURNED' and len(row['pulses']) == 3


def test_anonymous_return_and_simultaneous_frame_never_invent_direction(sample):
    """TRAP-19. 等时规则先于按票配对；无票短往返只形成歧义。"""
    ambiguous = [row for row in sample['direction'] if row['direction'] == 'ambiguous']
    assert [(row['pattern'], row['code']) for row in ambiguous] == [('A→B→A', 'ANONYMOUS_RETURN'), ('A=B', 'SIMULTANEOUS')]
    assert sum(len(row['pulses']) for row in ambiguous) == 5


def test_third_pulse_one_ms_after_return_window_is_independent(pulses):
    rows = classify(pair(pulses([('A', 0, '02'), ('B', 250, '02'), ('A', 501, '02')])))
    assert [(row['direction'], row['pattern']) for row in rows] == [('entry', 'A→B'), ('orphan', 'A')]


def test_foldback_accepts_the_inclusive_threshold_both_legs(pulses):
    row, = classify(pair(pulses([('A', 0, '02'), ('B', 250, '02'), ('A', 500, '02')])))
    assert row['direction'] == 'return' and row['duration_ms'] == 500


def test_direction_endpoint_filters_exceptions_and_exposes_trace(client):
    result = client.get('/api/direction/sample', params={'view': 'exceptions', 'q': 'TIE-B'}).json()
    row, = result['items']
    assert row['direction'] == 'ambiguous'
    assert [pulse['pulse'] for pulse in row['pulses']] == ['TIE-A', 'TIE-B']


def test_same_timestamp_in_a_different_gate_can_still_have_order(pulses):
    raw = pulses([('A', 0, '02'), ('B', 0, '02'), ('B', 200, '02'), ('A', 210, '02')])
    raw[1]['gate'] = 'G2'
    rows = classify(pair(raw))
    assert [(row['gate'], row['direction']) for row in rows] == [('G1', 'return'), ('G2', 'orphan')]
