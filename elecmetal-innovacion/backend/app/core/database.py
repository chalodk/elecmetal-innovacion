from typing import Optional

import asyncpg
from app.core.config import settings

_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


async def health_check() -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        return result == 1
