from fastapi import APIRouter
from app.core.database import health_check

router = APIRouter()


@router.get("/health")
async def health():
    db_ok = await health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }
