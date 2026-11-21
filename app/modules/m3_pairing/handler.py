from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, snapshot

router = APIRouter(prefix='/api/pairing')


@router.get('/{run_id}')
def pairs(request: Request, run_id: str, query: QueryRows = Depends()):
    data = snapshot(request, run_id)
    return query.result({'main': data['pairs'], 'orphans': [row for row in data['pairs'] if row['kind'] == 'orphan']})
