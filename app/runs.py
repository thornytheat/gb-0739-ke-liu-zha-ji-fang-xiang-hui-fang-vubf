from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.problems import Problem
from app.settings import BYTE_LIMIT, COLUMNS, SAMPLE

router = APIRouter(prefix='/api/runs')


def sample_files():
    return {name: (SAMPLE / name).read_bytes() for name in COLUMNS}


def commit(request, sources):
    data, reused = request.app.state.archive.publish(sources)
    return JSONResponse({'run_id': data['manifest']['run_id'], 'manifest': data['manifest'], 'reused': reused,
                         'totals': data['balance']['totals'], 'isolated': len(data['isolated'])},
                        status_code=200 if reused else 201)


@router.post('/sample')
def publish_sample(request: Request):
    return commit(request, sample_files())


@router.post('')
def upload(request: Request, files: Annotated[list[UploadFile], File()]):
    filenames = [item.filename for item in files]
    if len(filenames) != len(COLUMNS) or set(filenames) != set(COLUMNS):
        raise Problem('FILE_SET', detail={'expected': list(COLUMNS)})
    sources = {}
    for item in files:
        raw = item.file.read(BYTE_LIMIT + 1)
        if len(raw) > BYTE_LIMIT:
            raise Problem('FILE_LIMIT', 413, {'source': item.filename})
        sources[item.filename] = raw
    return commit(request, sources)


@router.post('/{run_id}/rerun')
def rerun(request: Request, run_id: str):
    return commit(request, request.app.state.archive.sources(run_id))
