import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import accounts as accounts_router
from app.api.v1 import auth as auth_router
from app.api.v1 import prospect as prospect_router
from app.api.v1 import workflows as workflows_router
from app.core.config import get_settings
from app.observability.logging import request_log_fields
from app.seed.loader import SeedLoader
from app.seed.demo_generator import DemoDataGenerator
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
app.include_router(prospect_router.router, prefix="/v1")
app.include_router(workflows_router.router, prefix="/v1")


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
    
    logger.info("[startup] Auto-seeding enabled")
    seed_loaded = False
    
    # Try SeedLoader (YAML)
    try:
        with session_scope() as session:
            loader = SeedLoader(seed_dir=settings.seed_dir)
            counts = loader.seed(session=session)
            logger.info(f"[startup] Seed data loaded from YAML: {counts}")
            seed_loaded = True
    except Exception as e:
        logger.warning(f"[startup] SeedLoader failed (expected if YAMLs missing): {e}")

    # Fallback to DemoDataGenerator
    if not seed_loaded:
        try:
            with session_scope() as session:
                generator = DemoDataGenerator(session)
                counts = generator.generate_all()
                logger.info(f"[startup] Demo data generated: {counts}")
                seed_loaded = True
        except Exception as e:
            logger.error(f"[startup] DemoDataGenerator failed: {e}")

    if not seed_loaded:
        logger.warning("[startup] No seed data was loaded")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
