from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, snapshot

router = APIRouter(prefix='/api/direction')


@router.get('/{run_id}')
def direction(request: Request, run_id: str, query: QueryRows = Depends()):
    entries = snapshot(request, run_id)['direction']
    return query.result({'main': entries, 'exceptions': [row for row in entries if row['direction'] not in {'entry', 'exit'}]})
