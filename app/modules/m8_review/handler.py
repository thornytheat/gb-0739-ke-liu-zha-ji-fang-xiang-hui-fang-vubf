from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.problems import Problem
from app.query import QueryRows
from app.settings import PREVIEW
from app.modules.m8_review.service import leg_descriptions, review_summary

router = APIRouter(prefix='/api/review')


class ReviewNote(BaseModel):
    ticket: Annotated[str, Field(min_length=1, max_length=64)]
    kept_anchor: Annotated[str, Field(min_length=1, max_length=64)]
    period_start_ms: Annotated[int, Field(ge=0)]
    period_end_ms: Annotated[int, Field(ge=1)]
    reason: Annotated[str, Field(min_length=1, max_length=200)]


def _snapshot(request, run_id):
    if run_id == PREVIEW:
        return request.app.state.preview
    return request.app.state.archive.read(run_id)


@router.get('/{run_id}')
def review(request: Request, run_id: str, query: QueryRows = Depends()):
    data = _snapshot(request, run_id)
    groups, notes, comparison = leg_descriptions(data), [], []
    if run_id != PREVIEW:
        archive = request.app.state.archive
        notes = archive.review_notes(run_id)
        comparison = archive.shift_comparison(run_id)
    if query.view == 'main':
        query.view = 'groups'
    result = query.result({'groups': groups, 'notes': notes, 'shifts': comparison})
    result['review'] = review_summary(data)
    result['base_totals'] = data['balance']['totals'] if run_id == PREVIEW else \
        request.app.state.archive.base_totals(run_id)
    return result


@router.post('/{run_id}/notes')
def add_note(request: Request, run_id: str, payload: ReviewNote):
    if run_id == PREVIEW:
        raise Problem('REVIEW_PREVIEW', 409)
    snapshot, reused = request.app.state.archive.submit_review(
        run_id, payload.ticket.strip(), payload.kept_anchor.strip(),
        payload.period_start_ms, payload.period_end_ms, payload.reason)
    return JSONResponse({'run_id': run_id, 'reused': reused, 'review': review_summary(snapshot),
                         'totals': snapshot['balance']['totals']},
                        status_code=200 if reused else 201)
