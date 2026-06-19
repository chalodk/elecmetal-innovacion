import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from app.api.v1 import sessions, initiatives, notifications, evaluations
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", environment=settings.environment)
    await create_pool()
    yield
    await close_pool()
    log.info("shutdown")


app = FastAPI(
    title="Elecmetal Innovacion API",
    version="0.1.0",
    lifespan=lifespan,
    # En producción ocultar docs si se requiere
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

# ── Exception handlers (unified error format) ────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(initiatives.router, prefix="/api/v1/initiatives", tags=["initiatives"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(evaluations.router, prefix="/api/v1", tags=["evaluations"])
