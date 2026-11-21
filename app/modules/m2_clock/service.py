from app.evidence import isolate, validated_groups
from app.fields import key, number, time_window
from app.modules.m2_clock.index import gate_key, normalize_by_gate, overlap_regions
from app.problems import Problem


def parse_version(row):
    start, end = time_window(row, 'device_from', 'device_to')
    return {'station': key(row['station']), 'gate': key(row['gate']), 'start_ms': start, 'end_ms': end,
            'offset_ms': number(row['offset_ms'], -120_000, 120_000)}


def prepare(rows, issues):
    versions, _, conflicts = validated_groups(rows, parse_version, lambda row: (*gate_key(row), row['start_ms'], row['end_ms']),
                                   'clock', 'CLOCK', issues)
    return versions, conflicts, list(overlap_regions(versions + conflicts))


def correct(pulses, versions, issues):
    aligned, unavailable = [], []
    for pulse, version, candidates in normalize_by_gate(pulses, versions):
        if not version:
            code = 'CLOCK_OVERLAP' if candidates else 'CLOCK_GAP'
            isolate(issues, pulse, code, 'clock', pulse['pulse'], offset_lines=candidates)
            unavailable.append({**pulse, 'code': code})
            continue
        aligned.append({**pulse, 'corrected_ms': pulse['device_ms'] - version['offset_ms'],
                        'offset_ms': version['offset_ms'], 'offset_line': version['line']})
    if not aligned:
        raise Problem('NO_CLOCKED')
    aligned.sort(key=lambda row: (row['corrected_ms'], row['station'], row['gate'], row['pulse']))
    return aligned, unavailable
