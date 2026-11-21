import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import runs, web
from app.archive import Archive
from app.modules.m1_intake import handler as intake
from app.modules.m2_clock import handler as clock
from app.modules.m3_pairing import handler as pairing
from app.modules.m4_direction import handler as direction
from app.modules.m5_transfer import handler as transfer
from app.modules.m6_balance import handler as balance
from app.modules.m7_report import handler as report
from app.pipeline import calculate
from app.problems import MESSAGES, Problem
from app.settings import PREVIEW, ROOT


def create_app(path=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.archive = Archive(path or os.environ.get('GATE_DB_PATH', ROOT / 'data' / 'replay.sqlite3'))
        app.state.archive.initialize()
        app.state.preview = calculate(PREVIEW, runs.sample_files())
        yield

    app = FastAPI(title='客流闸机方向回放', lifespan=lifespan)
    app.mount('/static', StaticFiles(directory=ROOT / 'app' / 'static'), name='static')
    for module in (web, runs, intake, clock, pairing, direction, transfer, balance, report):
        app.include_router(module.router)

    @app.exception_handler(Problem)
    def domain_error(_: Request, exc: Problem):
        return JSONResponse({'code': exc.code, 'message': MESSAGES[exc.code], 'detail': exc.detail}, status_code=exc.status)

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()
