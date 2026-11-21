from app.modules.m5_transfer.service import deduplicate


def test_cross_midnight_uses_corrected_exit_and_entry(sample):
    match = next(row for row in sample['transfers'] if row['is_transfer'])
    assert (match['ticket'], match['from_station'], match['station']) == ('00017', 'NTH', 'STH')
    assert (match['encounter'], match['anchor'], match['gap_ms']) == ('E-TR-IN-A', 'E-TR-OUT-B', 90_100)
    assert (match['entry_line'], match['anchor_line'], match['pass_line'], match['link_line']) == (4, 6, 2, 2)


def test_transfer_exit_anchor_is_single_use(sample):
    decisions = [row for row in sample['transfers'] if row['ticket'] == '00017']
    assert [(row['code'], row['unique_entry'], row['anchor']) for row in decisions] == [
        ('TRANSFER', 0, 'E-TR-OUT-B'), ('NO_ELIGIBLE_EXIT', 1, None),
    ]


def test_reverse_of_directed_link_is_not_a_transfer(sample):
    row = next(row for row in sample['transfers'] if row['ticket'] == '00050')
    assert row['station'] == 'NTH' and row['code'] == 'NO_ELIGIBLE_EXIT'
    assert {item['direction'] for item in sample['direction'] if item['ticket'] == '00050'} == {'entry', 'exit'}


def test_no_ticket_entries_do_not_merge(sample):
    anonymous = [row for row in sample['transfers'] if row['code'] == 'NO_TICKET']
    assert len(anonymous) == 2
    assert sum(row['unique_entry'] for row in anonymous) == 2
    assert all(row['ticket'] is None for row in anonymous)


def test_expiration_boundary_is_not_valid(sample):
    final = next(row for row in sample['transfers'] if row['ticket'] == '00099')
    assert final['code'] == 'PASS_EXPIRED' and final['unique_entry'] == 1
    assert sample['reason_counts']['PASS_CONFLICT'] == 2


def test_transfer_windows_include_minimum_and_maximum_and_exclude_outside():
    def event(identifier, station, direction, time, ticket):
        return {'encounter': identifier, 'station': station, 'direction': direction, 'end_ms': time,
                'ticket': ticket, 'gate': 'G1', 'pulses': [{'line': 2}]}
    tickets = ['0', '1', '2', '3']
    passes = [{'ticket': ticket, 'start_ms': 0, 'end_ms': 1_000_000, 'transfer': True, 'line': 2} for ticket in tickets]
    links = [{'from_station': 'NTH', 'to_station': 'STH', 'min_ms': 60_000, 'max_ms': 720_000, 'line': 2}]
    exits = [event(f'O{ticket}', 'NTH', 'exit', 1000, ticket) for ticket in tickets]
    entries = [event(f'I{ticket}', 'STH', 'entry', 1000 + gap, ticket)
               for ticket, gap in zip(tickets, [59999, 60000, 720000, 720001])]
    assert [row['is_transfer'] for row in deduplicate(entries[::-1] + exits, passes, links)] == [False, True, True, False]


def test_anchor_api_returns_cross_station_proof(client):
    response = client.get('/api/transfer/sample', params={'view': 'anchors'})
    row, = response.json()['items']
    assert response.status_code == 200 and row['anchor'] == 'E-TR-OUT-B'
    assert row['is_transfer'] is True and row['gap_ms'] == 90_100


def test_nearest_eligible_exit_wins_and_other_exit_remains_available():
    def motion(identity, station, label, instant):
        return {'encounter': identity, 'station': station, 'gate': 'G1', 'direction': label,
                'end_ms': instant, 'ticket': '001', 'pulses': [{'line': 9}]}
    entries = [motion('soon', 'STH', 'entry', 100_000), motion('later', 'STH', 'entry', 180_000)]
    exits = [motion('old', 'NTH', 'exit', 2_000), motion('too-close', 'WST', 'exit', 90_000),
             motion('recent', 'NTH', 'exit', 10_000)]
    passes = [{'ticket': '001', 'start_ms': 0, 'end_ms': 1_000_000, 'transfer': True, 'line': 2}]
    links = [{'from_station': origin, 'to_station': 'STH', 'min_ms': 60_000, 'max_ms': 180_000, 'line': 2}
             for origin in ('NTH', 'WST')]
    decisions = deduplicate(entries + exits, passes, links)
    assert [(row['anchor'], row['gap_ms']) for row in decisions] == [('recent', 90_000), ('too-close', 90_000)]
