import csv
import io

from app.evidence import Row, isolate
from app.problems import Problem
from app.settings import BYTE_LIMIT, COLUMNS, ROW_LIMIT


def decode(raw, name):
    if len(raw) > BYTE_LIMIT:
        raise Problem('FILE_LIMIT', 413, {'source': name})
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise Problem('BAD_ENCODING', detail={'source': name})


def read(raw, name, meta, issues):
    content, encoding = decode(raw, name)
    if not content:
        raise Problem('EMPTY_FILE', detail={'source': name})
    meta.update(source=name, encoding=encoding, logical_rows=0, headers=0, blanks=0)
    reader = csv.reader(io.StringIO(content, newline=''), strict=True)
    header = None
    try:
        while True:
            line = reader.line_num + 1
            fields = next(reader, None)
            if fields is None:
                break
            meta['logical_rows'] += 1
            if meta['logical_rows'] > ROW_LIMIT:
                raise Problem('FILE_LIMIT', 413, {'source': name, 'line': line})
            if not any(field.strip() for field in fields):
                meta['blanks'] += 1
                continue
            normalized = tuple(field.strip().lstrip('\ufeff') for field in fields)
            if header is None:
                columns = COLUMNS[name]
                if set(normalized) != set(columns) or len(normalized) != len(columns):
                    raise Problem('BAD_HEADER', detail={'source': name, 'line': line, 'expected': columns})
                header = normalized
            if normalized == header:
                meta['headers'] += 1
                continue
            row = Row(name, line, reader.line_num, tuple(fields), dict(zip(header, fields)))
            if len(fields) != len(header):
                isolate(issues, row.origin(), 'BAD_COLUMNS', 'intake', fields[0], expected=len(header), actual=len(fields))
                continue
            yield row
    except csv.Error as exc:
        raise Problem('BAD_CSV', detail={'source': name, 'line': line}) from exc
    if header is None:
        raise Problem('ONLY_BLANK', detail={'source': name})
