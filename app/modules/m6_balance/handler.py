from fastapi import APIRouter, Depends, Request

from app.query import QueryRows, snapshot

router = APIRouter(prefix='/api/balance')


@router.get('/{run_id}')
def balance(request: Request, run_id: str, query: QueryRows = Depends()):
    result = snapshot(request, run_id)['balance']
    return query.result({'main': result['shifts'], 'sources': result['sources']},
                        totals=result['totals'], checks=result['checks'], balanced=result['balanced'])
