import re
from datetime import UTC, datetime, timedelta

from app.problems import BadRow

KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,3})?(?:Z|[+-][0-9]{2}:[0-9]{2})')
NULLS = {'', '-', 'NULL', 'N/A', '未知'}
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def key(value, optional=False):
    value = value.strip()
    if value.upper() in NULLS:
        if optional:
            return None
        raise BadRow('MISSING_VALUE')
    if not KEY.fullmatch(value):
        raise BadRow('BAD_KEY')
    return value


def timestamp(value):
    value = value.strip()
    if not TIME.fullmatch(value) or (not value.endswith('Z') and int(value[-2:]) >= 60):
        raise BadRow('BAD_TIME')
    try:
        date = datetime.fromisoformat(value)
        if not 2000 <= date.year < 2100:
            raise ValueError(value)
        delta = date - EPOCH
    except (ValueError, OverflowError) as exc:
        raise BadRow('BAD_TIME') from exc
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def utc_date(milliseconds):
    return EPOCH + timedelta(milliseconds=milliseconds)


def number(value, low, high):
    value = value.strip()
    if not re.fullmatch(r'-?[0-9]{1,9}', value) or not low <= int(value) <= high:
        raise BadRow('BAD_INTEGER')
    return int(value)


def time_window(row, start_field, end_field):
    start, end = timestamp(row[start_field]), timestamp(row[end_field])
    if start >= end:
        raise BadRow('BAD_WINDOW')
    return start, end
