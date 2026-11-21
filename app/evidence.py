from collections import defaultdict
from dataclasses import dataclass

from app.problems import BadRow, MESSAGES


@dataclass(frozen=True)
class Row:
    source: str
    line: int
    last_line: int
    raw: tuple[str, ...]
    data: dict[str, str]

    def origin(self):
        return {'source': self.source, 'line': self.line, 'last_line': self.last_line, 'raw': list(self.raw)}


ORIGIN = ('source', 'line', 'last_line', 'raw')


def isolate(issues, origin, code, stage, key='', **detail):
    issues.append({**{field: origin[field] for field in ORIGIN}, 'code': code, 'reason': MESSAGES[code],
                   'stage': stage, 'key': key, 'detail': detail})


def validated_groups(rows, parse, group_key, stage, code_prefix, issues):
    groups = defaultdict(list)
    for row in rows:
        try:
            value = parse(row.data)
        except BadRow as exc:
            isolate(issues, row.origin(), str(exc), stage, row.raw[0] if row.raw else '')
            continue
        groups[group_key(value)].append((value, row.origin()))
    retained, duplicates, conflicts = [], [], []
    for identity, group in groups.items():
        label = '/'.join(map(str, identity)) if isinstance(identity, tuple) else identity
        value, origin = group[0]
        if any(alternative != value for alternative, _ in group[1:]):
            for alternative, current in group:
                conflicts.append({**alternative, **current})
                isolate(issues, current, f'{code_prefix}_CONFLICT', stage, label,
                        related_lines=[item['line'] for _, item in group[:20]], related_count=len(group))
            continue
        retained.append({**value, **origin})
        for _, current in group[1:]:
            isolate(issues, current, f'{code_prefix}_DUPLICATE', stage, label, retained_line=origin['line'])
            duplicates.append({**value, **current, 'retained_line': origin['line']})
    return retained, duplicates, conflicts
