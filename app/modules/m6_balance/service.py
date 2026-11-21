from collections import Counter, defaultdict

from app.modules.m6_balance.shifts import shift_of


def source_balance(stats, issues, accepted):
    counts = Counter(row['source'] for row in issues)
    results = []
    for source, facts in stats.items():
        passed = accepted[source]
        isolated = counts[source]
        results.append({**facts, 'accepted': passed, 'isolated': isolated,
                        'difference': facts['logical_rows'] - passed - isolated - facts['headers'] - facts['blanks']})
    return results


def reconcile(aligned, duplicates, unavailable, readings, transfers, sources):
    grouped = defaultdict(Counter)
    pulse_index = {row['pulse']: row for row in aligned}

    def counts(station, instant):
        return grouped[shift_of(instant), station]

    repeat_count = 0
    for row in aligned:
        counts(row['station'], row['corrected_ms'])['trackable'] += 1
    for repeat in duplicates:
        pulse = pulse_index.get(repeat['pulse'])
        if pulse:
            row = counts(pulse['station'], pulse['corrected_ms'])
            row.update(trackable=1, repeats=1)
            repeat_count += 1
    for reading in readings:
        for pulse in reading['pulses']:
            row = counts(reading['station'], pulse['corrected_ms'])
            row['orphan_pulses' if reading['direction'] == 'orphan' else 'evidence_pulses'] += 1
        row = counts(reading['station'], reading['end_ms'])
        row[reading['direction']] += 1
    for transfer in transfers:
        row = counts(transfer['station'], transfer['at_ms'])
        row['unique_entries'] += transfer['unique_entry']
        if transfer['is_transfer']:
            row['transfer_in'] += 1
            counts(transfer['from_station'], transfer['anchor_ms'])['transfer_out'] += 1
    fields = ('trackable', 'repeats', 'evidence_pulses', 'orphan_pulses', 'entry', 'exit', 'return', 'ambiguous',
              'orphan', 'unique_entries', 'transfer_in', 'transfer_out')
    totals, shifts = Counter(), []
    for (shift, station), row in sorted(grouped.items()):
        facts = {field: row[field] for field in fields}
        facts.update(pulse_difference=row['trackable'] - row['repeats'] - row['evidence_pulses'] - row['orphan_pulses'],
                     entry_difference=row['entry'] - row['unique_entries'] - row['transfer_in'],
                     physical_net=row['entry'] - row['exit'], transfer_net=row['transfer_in'] - row['transfer_out'])
        facts['nontransfer_net'] = facts['physical_net'] - facts['transfer_net']
        shifts.append({'shift': shift, 'station': station, **facts})
        for key, value in facts.items():
            totals[key] += value
    occurrences = Counter(pulse['pulse'] for reading in readings for pulse in reading['pulses'])
    totals.update(clock_isolated=len(unavailable), clock_blocked_repeats=len(duplicates) - repeat_count)
    checks = {
        'sources': all(item['difference'] == 0 for item in sources),
        'pulse_ids': occurrences == Counter(row['pulse'] for row in aligned),
        'shifts': all(row['pulse_difference'] == 0 and row['entry_difference'] == 0 for row in shifts),
        'transfers': totals['transfer_in'] == totals['transfer_out'] and
                     totals['transfer_in'] == len({row['anchor'] for row in transfers if row['is_transfer']}),
    }
    return {'balanced': all(checks.values()), 'checks': checks, 'totals': dict(totals), 'shifts': shifts, 'sources': sources}
