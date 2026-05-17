import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import accounts as accounts_router
from app.api.v1 import auth as auth_router
from app.core.config import get_settings
from app.observability.logging import request_log_fields
from app.seed.loader import SeedLoader
from app.storage.db import session_scope


settings = get_settings()
logger = logging.getLogger("gtm.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router, prefix="/v1")
app.include_router(accounts_router.router, prefix="/v1")


@app.middleware("http")
async def observe_request(request: Request, call_next):
    request_id = str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    fields = request_log_fields(
        service="api.request",
        status="ok" if response.status_code < 500 else "error",
        duration_ms=duration_ms,
        request_id=request_id,
    )
    logger.info(fields)
    response.headers["x-request-id"] = request_id
    return response


@app.on_event("startup")
def startup_seed():
    if not settings.auto_seed_on_startup:
        return
    with session_scope() as session:
        SeedLoader(seed_dir=settings.seed_dir).seed(session=session)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
