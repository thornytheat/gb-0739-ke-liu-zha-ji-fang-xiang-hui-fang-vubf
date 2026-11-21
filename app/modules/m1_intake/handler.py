from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, issues, snapshot

router = APIRouter(prefix='/api/intake')


@router.get('/{run_id}')
def intake(request: Request, run_id: str, query: QueryRows = Depends()):
    data = snapshot(request, run_id)
    return query.result({'main': data['intake'], 'repeat': data['duplicates'], 'isolated': issues(data, 'intake')})
