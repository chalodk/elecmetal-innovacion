from fastapi import APIRouter
from app.core.database import health_check, get_pool

router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check — verifies DB connectivity."""
    db_ok = await health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }


@router.get("/health/monitoring")
async def monitoring():
    """Extended monitoring — row counts + agent status."""
    pool = get_pool()
    async with pool.acquire() as conn:
        tables = [
            "profiles", "sessions", "messages", "initiatives",
            "evaluations", "notifications", "agent_configs",
        ]
        counts = {}
        for t in tables:
            counts[t] = await conn.fetchval(f"SELECT count(*) FROM {t}")

        # Check active agents
        agents = await conn.fetch(
            "SELECT agent_name, version FROM agent_configs WHERE is_active = true"
        )

    return {
        "status": "ok",
        "database": "connected",
        "row_counts": counts,
        "active_agents": [{"name": a["agent_name"], "version": a["version"]} for a in agents],
    }
