from app.evidence import validated_groups
from app.fields import key, timestamp
from app.problems import BadRow, Problem


def parse_pulse(row):
    beam = row['beam'].strip().upper()
    if beam not in {'A', 'B'}:
        raise BadRow('BAD_BEAM')
    return {**{field: key(row[field]) for field in ('pulse', 'station', 'gate')}, 'beam': beam,
            'device_ms': timestamp(row['device_at']), 'ticket': key(row['ticket'], optional=True)}


def intake(rows, issues):
    accepted, duplicates, _ = validated_groups(rows, parse_pulse, lambda row: row['pulse'], 'intake', 'PULSE', issues)
    if not accepted:
        raise Problem('NO_PULSES')
    return accepted, duplicates
