import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.api.v1.health import router as health_router

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")

# Próximos routers (agregar a medida que se implementen):
# from app.api.v1 import sessions, initiatives, evaluations
# app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
