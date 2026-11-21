from app.fields import timestamp
from app.modules.m6_balance.service import reconcile
from app.modules.m6_balance.shifts import shift_of


def test_trackable_pulses_equal_evidence_orphans_and_repeats(sample):
    totals = sample['balance']['totals']
    assert (totals['trackable'], totals['evidence_pulses'], totals['orphan_pulses'], totals['repeats']) == (34, 30, 3, 1)
    assert totals['pulse_difference'] == 0 and totals['clock_isolated'] == 3
    assert all(row['pulse_difference'] == 0 for row in sample['balance']['shifts'])


def test_origin_and_destination_must_offset_transfer_net(sample):
    by_station = {row['station']: row for row in sample['balance']['shifts'] if row['shift'] == '2026-11-19 夜班'}
    assert (by_station['NTH']['transfer_out'], by_station['NTH']['transfer_net']) == (1, -1)
    assert (by_station['STH']['transfer_in'], by_station['STH']['transfer_net']) == (1, 1)
    assert sample['balance']['totals']['transfer_net'] == 0


def test_pulses_follow_own_shift_but_encounter_follows_completion(sample):
    by_shift = {row['shift']: row for row in sample['balance']['shifts'] if row['station'] == 'STH'}
    assert (by_shift['2026-11-19 夜班']['trackable'], by_shift['2026-11-19 夜班']['entry']) == (7, 2)
    assert (by_shift['2026-11-20 早班']['trackable'], by_shift['2026-11-20 早班']['entry']) == (3, 2)
    assert by_shift['2026-11-20 早班']['pulse_difference'] == 0


def test_operating_day_handles_new_year_and_shift_boundaries():
    cases = [('2027-01-01T05:59:59.999+08:00', '2026-12-31 夜班'), ('2027-01-01T06:00:00+08:00', '2027-01-01 早班'),
             ('2027-01-01T14:00:00+08:00', '2027-01-01 中班'), ('2027-01-01T22:00:00+08:00', '2027-01-01 夜班')]
    assert [shift_of(timestamp(raw)) for raw, _ in cases] == [expected for _, expected in cases]


def test_duplicate_token_cannot_hide_another_pulse_loss(sample):
    directions = [dict(row) for row in sample['direction']]
    live = next(row for row in directions if row['encounter'] == 'E-TAIL-A1')
    paired = live['pulses']
    live['pulses'] = [paired[0], {**paired[1], 'pulse': paired[0]['pulse']}]
    data = reconcile(sample['aligned'], sample['duplicates'], [], directions, sample['transfers'], sample['balance']['sources'])
    assert data['checks']['shifts'] is True
    assert data['checks']['pulse_ids'] is False
    assert data['balanced'] is False


def test_input_count_connects_all_isolated_rows_and_clean_lines(sample):
    facts = sample['balance']['sources']
    assert sum(row['logical_rows'] for row in facts) == 69
    assert sum(row['accepted'] for row in facts) == 46
    assert sum(row['isolated'] for row in facts) == 17
    assert sum(row['headers'] + row['blanks'] for row in facts) == 6
    assert all(row['difference'] == 0 for row in facts)


def test_balance_endpoint_reports_physical_and_unique_counts(client):
    response = client.get('/api/balance/sample', params={'station': 'STH'})
    data = response.json()
    assert response.status_code == 200 and data['total'] == 2
    assert data['balanced'] is True
    assert (data['totals']['entry'], data['totals']['exit'], data['totals']['unique_entries']) == (9, 2, 8)
