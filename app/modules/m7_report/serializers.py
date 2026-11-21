import csv
import io
import json
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def tabular(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(fields)
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field)
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            if isinstance(value, str) and (value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\n', '\r'))):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return stream.getvalue().encode('utf-8-sig')


def zip_members(members):
    stream = io.BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, contents in sorted(members.items()):
            archive.writestr(ZipInfo(name), contents, compress_type=ZIP_DEFLATED)
    return stream.getvalue()
