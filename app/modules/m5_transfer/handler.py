from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, issues, snapshot

router = APIRouter(prefix='/api/transfer')


@router.get('/{run_id}')
def transfers(request: Request, run_id: str, query: QueryRows = Depends()):
    data = snapshot(request, run_id)
    return query.result({'main': data['transfers'], 'anchors': [row for row in data['transfers'] if row['is_transfer']],
                         'passes': data['passes'], 'links': data['links'], 'isolated': issues(data, 'transfer')})
