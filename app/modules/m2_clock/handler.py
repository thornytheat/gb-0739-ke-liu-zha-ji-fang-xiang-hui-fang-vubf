from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, issues, snapshot

router = APIRouter(prefix='/api/clock')


@router.get('/{run_id}')
def clock(request: Request, run_id: str, query: QueryRows = Depends()):
    data = snapshot(request, run_id)
    return query.result({'main': data['aligned'], 'versions': data['versions'],
                         'overlaps': data['overlaps'], 'isolated': issues(data, 'clock')})
