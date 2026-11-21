from collections import defaultdict, deque

from app.problems import MESSAGES


def valid_pass(ticket, instant, passes):
    if not ticket:
        return 'NO_TICKET'
    record = passes.get(ticket)
    if record is None:
        return 'PASS_UNKNOWN'
    if not record['transfer']:
        return 'PASS_NOT_TRANSFERABLE'
    if not record['start_ms'] <= instant < record['end_ms']:
        return 'PASS_EXPIRED'
    return ''


def deduplicate(readings, passes, links):
    passes = {row['ticket']: row for row in passes}
    links = {(row['from_station'], row['to_station']): row for row in links}
    prior, choices = defaultdict(deque), []
    movements = (row for row in readings if row['direction'] in {'exit', 'entry'})
    for motion in sorted(movements, key=lambda row: (row['end_ms'], row['encounter'])):
        ticket, instant, station = motion['ticket'], motion['end_ms'], motion['station']
        code = valid_pass(ticket, instant, passes)
        if motion['direction'] == 'exit':
            if not code:
                prior[ticket].append(motion)
            continue
        anchor, link = None, None
        if not code:
            exits = prior[ticket]
            while exits and instant - exits[0]['end_ms'] > 3_600_000:
                exits.popleft()
            for previous in reversed(exits):
                route = links.get((previous['station'], station))
                duration = instant - previous['end_ms']
                if route and route['min_ms'] <= duration <= route['max_ms']:
                    anchor, link = previous, route
                    exits.remove(previous)
                    break
            code = 'TRANSFER' if anchor else 'NO_ELIGIBLE_EXIT'
        choices.append({'encounter': motion['encounter'], 'station': station, 'gate': motion['gate'],
                        'ticket': ticket, 'at_ms': instant, 'code': code, 'reason': MESSAGES[code], 'is_transfer': bool(anchor),
                        'unique_entry': int(anchor is None), 'entry_line': motion['pulses'][-1]['line'],
                        'anchor': anchor['encounter'] if anchor else None, 'from_station': anchor['station'] if anchor else None,
                        'anchor_ms': anchor['end_ms'] if anchor else None,
                        'anchor_line': anchor['pulses'][-1]['line'] if anchor else None,
                        'gap_ms': instant - anchor['end_ms'] if anchor else None,
                        'link_line': link['line'] if link else None,
                        'pass_line': passes[ticket]['line'] if ticket in passes else None})
    return choices
