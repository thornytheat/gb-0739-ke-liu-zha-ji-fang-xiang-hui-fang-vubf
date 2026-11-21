from datetime import timedelta
from zoneinfo import ZoneInfo

from app.fields import utc_date
from app.settings import ZONE

LOCAL = ZoneInfo(ZONE)


def shift_of(milliseconds):
    local = utc_date(milliseconds).astimezone(LOCAL)
    day = local.date() - timedelta(days=int(local.hour < 6))
    if 6 <= local.hour < 14:
        name = '早班'
    elif 14 <= local.hour < 22:
        name = '中班'
    else:
        name = '夜班'
    return f'{day.isoformat()} {name}'
