from app.problems import MESSAGES

LABELS = {
    'entry': '进站', 'exit': '出站', 'return': '折返', 'ambiguous': '歧义', 'orphan': '孤脉冲',
}


def classify(evidence):
    readings = []
    for row in evidence:
        kind, code = row['kind'], row['code']
        if kind == 'pair':
            direction = 'entry' if row['pattern'] == 'A→B' else 'exit'
        elif kind == 'return' and row['ticket']:
            direction, code = 'return', 'RETURNED'
        elif kind == 'return':
            direction, code = 'ambiguous', 'ANONYMOUS_RETURN'
        else:
            direction = 'ambiguous' if kind == 'tie' else 'orphan'
        readings.append({**row, 'direction': direction, 'label': LABELS[direction],
                         'code': code, 'reason': MESSAGES[code] if code else '',
                         'duration_ms': row['end_ms'] - row['start_ms']})
    return readings
