from app.evidence import ORIGIN
from app.manifest import json_bytes, sha
from app.modules.m7_report.serializers import tabular, zip_members

PULSE = ('pulse', 'station', 'gate', 'beam', 'ticket', 'device_ms')
MOVEMENT = ('encounter', 'station', 'gate', 'ticket', 'pattern', 'start_ms', 'end_ms', 'pulses', 'code')


def build(snapshot, sources):
    balance = snapshot['balance']
    columns = {
        'aligned.csv': (snapshot['aligned'], (*PULSE, 'corrected_ms', 'offset_ms', 'offset_line', *ORIGIN)),
        'repeats.csv': (snapshot['duplicates'], (*PULSE, 'retained_line', *ORIGIN)),
        'pairs.csv': (snapshot['pairs'], ('kind', *MOVEMENT)),
        'direction.csv': (snapshot['direction'], ('direction', 'duration_ms', *MOVEMENT)),
        'transfers.csv': (snapshot['transfers'], ('encounter', 'station', 'gate', 'ticket', 'at_ms', 'unique_entry',
            'is_transfer', 'code', 'entry_line', 'anchor', 'from_station', 'anchor_ms', 'anchor_line', 'gap_ms',
            'link_line', 'pass_line')),
        'shifts.csv': (balance['shifts'], ('shift', 'station', 'trackable', 'repeats', 'evidence_pulses', 'orphan_pulses',
            'entry', 'exit', 'return', 'ambiguous', 'orphan', 'unique_entries', 'transfer_in', 'transfer_out',
            'pulse_difference', 'entry_difference', 'physical_net', 'transfer_net', 'nontransfer_net')),
        'source-counts.csv': (balance['sources'], ('source', 'encoding', 'logical_rows', 'headers', 'blanks', 'accepted',
                                                'isolated', 'difference')),
        'isolated.csv': (snapshot['isolated'], (*ORIGIN, 'stage', 'key', 'code', 'reason', 'detail')),
        'clock-overlaps.csv': (snapshot['overlaps'], ('station', 'gate', 'start_ms', 'end_ms', 'code')),
    }
    members = {f'input/{name}': raw for name, raw in sources.items()}
    for name, (entries, fields) in columns.items():
        members[f'evidence/{name}'] = tabular(entries, fields)
    manifest = {**snapshot['manifest'], 'checks': balance['checks'], 'totals': balance['totals'],
                'reason_counts': snapshot['reason_counts'], 'member_sha256': {name: sha(raw) for name, raw in members.items()}}
    members['manifest.json'] = json_bytes(manifest)
    return zip_members(members)
