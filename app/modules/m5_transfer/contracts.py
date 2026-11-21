from app.evidence import validated_groups
from app.fields import key, number, time_window
from app.problems import BadRow


def parse_pass(row):
    ticket = key(row['ticket'])
    start, end = time_window(row, 'valid_from', 'valid_to')
    if row['transfer'].strip() not in {'yes', 'no'}:
        raise BadRow('BAD_TRANSFER_FLAG')
    return {'ticket': ticket, 'start_ms': start, 'end_ms': end, 'transfer': row['transfer'].strip() == 'yes'}


def parse_link(row):
    origin = key(row['from_station'])
    destination = key(row['to_station'])
    minimum = number(row['min_seconds'], 1, 3600)
    maximum = number(row['max_seconds'], 1, 3600)
    if origin == destination or minimum > maximum:
        raise BadRow('BAD_LINK')
    return {'from_station': origin, 'to_station': destination, 'min_ms': minimum * 1000, 'max_ms': maximum * 1000}


def load_rules(passes, links, issues):
    pass_rows, _, _ = validated_groups(passes, parse_pass, lambda row: row['ticket'], 'transfer', 'PASS', issues)
    link_rows, _, _ = validated_groups(links, parse_link, lambda row: (row['from_station'], row['to_station']),
                                     'transfer', 'LINK', issues)
    return pass_rows, link_rows
