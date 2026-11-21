from collections import deque

from app.settings import PAIR_MS, RETURN_MS


def encounter(kind, pulses, code=''):
    first, last = pulses[0], pulses[-1]
    return {'encounter': 'E-' + first['pulse'], 'kind': kind, 'station': first['station'], 'gate': first['gate'],
            'ticket': first['ticket'] if kind != 'tie' else None,
            'start_ms': first['corrected_ms'], 'end_ms': last['corrected_ms'], 'code': code,
            'pattern': ('=' if kind == 'tie' else '→').join(pulse['beam'] for pulse in pulses),
            'pulses': [{field: pulse[field] for field in ('pulse', 'ticket', 'beam', 'corrected_ms', 'line', 'offset_line')}
                       for pulse in pulses]}


def triple(first, second, following):
    return (following is not None and following['beam'] == first['beam']
            and 0 < second['corrected_ms'] - first['corrected_ms'] <= RETURN_MS
            and 0 < following['corrected_ms'] - second['corrected_ms'] <= RETURN_MS)


def match_stream(entries, tie_cut=None):
    awaiting = deque()
    cursor = 0
    while cursor < len(entries):
        current = entries[cursor]
        cursor += 1
        at = current['corrected_ms']
        while awaiting and at - awaiting[0]['corrected_ms'] > PAIR_MS:
            yield encounter('orphan', [awaiting.popleft()], 'ORPHAN_TIMEOUT')
        if not awaiting or awaiting[0]['beam'] == current['beam']:
            awaiting.append(current)
            continue
        first = awaiting.popleft()
        following = entries[cursor] if cursor < len(entries) else None
        adjacent = entries[cursor - 2]['pulse'] == first['pulse']
        if not awaiting and adjacent and triple(first, current, following):
            yield encounter('return', [first, current, following])
            cursor += 1
        else:
            yield encounter('pair', [first, current])
    for pulse in awaiting:
        code = 'ORPHAN_END'
        if tie_cut is not None:
            code = 'ORPHAN_TIMEOUT' if tie_cut - pulse['corrected_ms'] > PAIR_MS else 'ORPHAN_TIE_BOUNDARY'
        yield encounter('orphan', [pulse], code)
