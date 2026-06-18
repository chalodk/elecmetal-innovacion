"""Database via Supabase Management API (HTTP/IPv4 bridge).

Your network only supports IPv4. Direct Postgres to Supabase requires IPv6.
This module proxies queries through the Supabase Management API over HTTPS,
which works on IPv4 networks.

Credentials are read from environment variables via app.core.config.Settings.
"""
import os
from typing import Any, Optional

import httpx

from app.core.config import settings


def _get_api_url() -> str:
    ref = settings.supabase_project_ref
    if not ref:
        raise RuntimeError("SUPABASE_PROJECT_REF not set — Management API requires a project ref")
    return f"https://api.supabase.com/v1/projects/{ref}/database/query"


def _get_headers() -> dict:
    token = settings.supabase_access_token
    if not token:
        raise RuntimeError("SUPABASE_ACCESS_TOKEN not set — Management API requires an access token")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30)
    return _client


async def _run_sql(sql: str) -> list[dict]:
    """Execute SQL query via Management API (async)."""
    client = _get_client()
    resp = await client.post(_get_api_url(), headers=_get_headers(), json={"query": sql})
    if resp.status_code in (200, 201):
        return resp.json()
    raise RuntimeError(
        f"DB API error {resp.status_code}: {resp.text[:300]}"
    )


# ── API-based replacements for asyncpg.Connection / asyncpg.Pool ──────────

class ApiConnection:
    """Replaces asyncpg.Connection — all queries go through Management API."""

    async def fetchval(self, sql: str) -> Any:
        result = await _run_sql(sql)
        if result and isinstance(result, list) and len(result) > 0:
            return list(result[0].values())[0]
        return None

    async def fetch(self, sql: str) -> list[dict]:
        return await _run_sql(sql) or []

    async def fetchrow(self, sql: str) -> Optional[dict]:
        result = await _run_sql(sql)
        return result[0] if result else None

    async def execute(self, sql: str) -> str:
        await _run_sql(sql)
        return "OK"

    async def close(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class ApiPool:
    """Replaces asyncpg.Pool — always returns an ApiConnection."""

    def acquire(self):
        return ApiConnection()

    async def close(self) -> None:
        global _client
        if _client:
            await _client.aclose()
            _client = None


_pool: Optional[ApiPool] = None


async def create_pool() -> None:
    global _pool
    _pool = ApiPool()
    conn = ApiConnection()
    val = await conn.fetchval("SELECT 1")
    print(f"[DB] Management API connection OK (IPv4) -> SELECT 1 = {val}")


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> ApiPool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


async def health_check() -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        return result == 1
