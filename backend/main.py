"""
main.py — FastAPI application entry point.

Registers all routers, CORS, rate-limiting, Prometheus metrics,
and startup/shutdown lifecycle hooks.

Run locally:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.logging import configure_logging

# ──────────────────────────────────────────────────────────────────────────────
# Logging setup (must happen before any other imports that call getLogger)
# ──────────────────────────────────────────────────────────────────────────────
configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Prometheus metrics (optional — gracefully skip if not installed)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _REQUESTS = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    _LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
    )
    _PREDICTIONS = Counter(
        "gesture_predictions_total",
        "Total gesture predictions served",
        ["gesture"],
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed; /metrics endpoint disabled.")


# ──────────────────────────────────────────────────────────────────────────────
# Rate limiting (optional — gracefully skip if slowapi not installed)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    limiter = None
    logger.warning("slowapi not installed; rate limiting disabled.")


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup tasks and tear down gracefully."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting up Hand Gesture Recognition API …")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Database: %s", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL)

    # Initialise database tables
    from backend.db.database import init_db
    init_db()
    logger.info("Database tables initialised.")

    # Warm up the gesture predictor (loads TF model into memory)
    try:
        from ai.inference import GesturePredictor
        predictor = GesturePredictor.get_instance(
            model_path=settings.MODEL_PATH,
            class_names_path=settings.CLASS_NAMES_PATH,
            inference_mode=settings.INFERENCE_MODE,
        )
        if predictor.is_loaded:
            logger.info(
                "Model loaded: %d classes, mode=%s",
                len(predictor.class_names),
                predictor.inference_mode,
            )
        else:
            logger.warning(
                "Model NOT loaded (file missing at %s). "
                "Train a model first — prediction endpoints will return 503.",
                settings.MODEL_PATH,
            )
    except Exception:
        logger.exception("Failed to warm up GesturePredictor at startup.")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down Hand Gesture Recognition API.")


# ──────────────────────────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hand Gesture Recognition API",
    description=(
        "AI-powered hand gesture classification using TensorFlow + MediaPipe. "
        "Recognises 10 gesture classes in real time from webcam frames."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
if SLOWAPI_AVAILABLE and limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging + Prometheus middleware ───────────────────────────────────
@app.middleware("http")
async def _request_middleware(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start

    path = request.url.path
    method = request.method
    status_code = str(response.status_code)

    logger.info(
        "%s %s %s %.0fms",
        method,
        path,
        status_code,
        duration * 1000,
    )

    if PROMETHEUS_AVAILABLE:
        _REQUESTS.labels(method=method, endpoint=path, status_code=status_code).inc()
        _LATENCY.labels(method=method, endpoint=path).observe(duration)

    return response


# ──────────────────────────────────────────────────────────────────────────────
# Register routers
# ──────────────────────────────────────────────────────────────────────────────

from backend.routers.auth import router as auth_router
from backend.routers.predict import router as predict_router
from backend.routers.training import router as training_router
from backend.routers.admin import router as admin_router

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(predict_router, prefix=API_PREFIX)
app.include_router(training_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)


# ──────────────────────────────────────────────────────────────────────────────
# Built-in endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> dict:
    """Return service health and model status."""
    model_loaded = False
    class_names: list[str] = []
    try:
        from ai.inference import GesturePredictor
        predictor = GesturePredictor.get_instance(
            model_path=settings.MODEL_PATH,
            class_names_path=settings.CLASS_NAMES_PATH,
        )
        model_loaded = predictor.is_loaded
        class_names = predictor.class_names
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "model_loaded": model_loaded,
        "inference_mode": settings.INFERENCE_MODE,
        "class_count": len(class_names),
    }


@app.get("/metrics", tags=["System"], summary="Prometheus metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics in text format."""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=501,
            content={"detail": "prometheus_client is not installed."},
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["System"], include_in_schema=False)
async def root() -> dict:
    return {
        "message": "Hand Gesture Recognition API",
        "docs": "/docs",
        "health": "/health",
    }
