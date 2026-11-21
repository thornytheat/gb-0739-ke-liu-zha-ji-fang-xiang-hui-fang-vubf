from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.fields import utc_date
from app.query import snapshot
from app.settings import PAIR_MS, PREVIEW, ROOT, ZONE

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / 'app' / 'templates')
LOCAL = ZoneInfo(ZONE)
MODULES = (
    ('intake', '闸机采信'), ('clock', '时钟偏移'), ('pairing', '双束配对'), ('direction', '方向与折返'),
    ('transfer', '换乘去重'), ('balance', '客流勾稽'), ('report', '班报复算'),
)


def local_ms(milliseconds):
    return utc_date(milliseconds).astimezone(LOCAL).isoformat(timespec='milliseconds')


def waterfall(data):
    journeys = {row['encounter']: row for row in data['transfers'] if row['is_transfer']}
    rows = []
    for event in reversed(data['direction'][-36:]):
        markers = event['pulses'][:5]
        rows.append({**event, 'stamp': local_ms(event['end_ms']), 'transfer': journeys.get(event['encounter']),
                     'markers': [{**pulse, 'x': round((pulse['corrected_ms'] - event['start_ms']) * 100 / PAIR_MS, 3)}
                                 for pulse in markers], 'width': round(event['duration_ms'] * 100 / PAIR_MS, 3),
                     'more': len(event['pulses']) - len(markers)})
    return rows


@router.get('/', response_class=HTMLResponse)
def home(request: Request, run: str = '', notice: str = ''):
    data = (snapshot(request, run) if run else request.app.state.archive.latest()) or request.app.state.preview
    manifest = data['manifest']
    return templates.TemplateResponse(request, 'index.html', {
        'data': data, 'manifest': manifest, 'preview': manifest['run_id'] == PREVIEW, 'modules': MODULES,
        'tracks': waterfall(data), 'totals': data['balance']['totals'],
        'stations': sorted({row['station'] for row in data['intake']}),
        'notice': {'published': '班报已发布', 'reused': '已复用该批次'}.get(notice, ''),
    })
