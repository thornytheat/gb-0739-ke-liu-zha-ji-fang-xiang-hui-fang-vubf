from fastapi import APIRouter, Depends, Request, Response

from app.modules.m7_report.bundle import build
from app.query import QueryRows, snapshot

router = APIRouter(prefix='/api/report')


@router.get('/{run_id}')
def report(request: Request, run_id: str, query: QueryRows = Depends()):
    data = snapshot(request, run_id)
    return query.result({'main': data['manifest']['inputs'], 'isolated': data['isolated']}, manifest=data['manifest'],
                        reason_counts=data['reason_counts'], checks=data['balance']['checks'])


@router.get('/{run_id}/export')
def export(request: Request, run_id: str):
    archive = request.app.state.archive
    contents = build(archive.read(run_id), archive.sources(run_id))
    return Response(contents, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="shift-{run_id}.zip"'})
