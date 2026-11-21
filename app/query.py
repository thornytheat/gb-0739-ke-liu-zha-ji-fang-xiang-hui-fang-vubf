from typing import Annotated

from fastapi import Query

from app.problems import Problem
from app.settings import PREVIEW


def snapshot(request, run_id):
    return request.app.state.preview if run_id == PREVIEW else request.app.state.archive.read(run_id)


def issues(data, stage):
    return [row for row in data['isolated'] if row['stage'] == stage]


class QueryRows:
    def __init__(self, q: Annotated[str, Query(max_length=64)] = '',
                 station: Annotated[str, Query(max_length=64)] = '',
                 view: Annotated[str, Query(max_length=24)] = 'main',
                 offset: Annotated[int, Query(ge=0)] = 0,
                 limit: Annotated[int, Query(ge=1, le=100)] = 25):
        self.q, self.station, self.view = q.strip().casefold(), station, view
        self.offset, self.limit = offset, limit

    def result(self, views, **meta):
        if self.view not in views:
            raise Problem('UNKNOWN_VIEW', detail={'allowed': list(views)})
        items = [row for row in views[self.view] if self.matches(row)]
        return {'items': items[self.offset:self.offset + self.limit], 'total': len(items),
                'offset': self.offset, 'limit': self.limit, **meta}

    def matches(self, row):
        if self.station and self.station not in (row.get('station'), row.get('from_station'), row.get('to_station'),
                                                 *row.get('raw', [])):
            return False
        if not self.q:
            return True
        keys = ('pulse', 'station', 'gate', 'ticket', 'code', 'key', 'encounter', 'anchor', 'from_station', 'to_station', 'source', 'shift')
        candidates = [str(row[key]) for key in keys if row.get(key) is not None]
        candidates += row.get('raw', [])
        candidates += [pulse['pulse'] for pulse in row.get('pulses', [])]
        return any(self.q in value.casefold() for value in candidates)
