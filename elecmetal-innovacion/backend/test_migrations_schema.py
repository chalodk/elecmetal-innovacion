#!/usr/bin/env python3
"""Migration & Schema validation (Step 12).

Standalone test — reads schema metadata from Supabase.
Run: python test_migrations_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import create_pool, close_pool, get_pool


async def test_all():
    pool = get_pool()
    passed = 0
    total = 0

    # 1. All 7 tables
    total += 1
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        actual = {r["table_name"] for r in rows}
    expected = {"profiles","agent_configs","sessions","messages",
                "initiatives","evaluations","notifications"}
    missing = expected - actual
    assert not missing, f"Missing tables: {missing}"
    print(f"  [PASS] All {len(expected)} tables exist")
    passed += 1

    # 2. v5.9 alignment
    total += 1
    async with pool.acquire() as conn:
        cols = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'initiatives'")
        col_map = {c["column_name"]: c["data_type"] for c in cols}
    assert col_map["trl"] == "smallint"
    assert col_map["crl"] == "smallint"
    assert col_map["brl"] == "smallint"
    assert col_map["dbi_extra"] == "jsonb"
    print("  [PASS] v5.9 columns: smallint TRL/CRL/BRL, jsonb dbi_extra")
    passed += 1

    # 3. CHECK constraints
    total += 1
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT con.conname FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "WHERE rel.relname IN ('initiatives','sessions','evaluations','notifications','profiles') "
            "AND con.contype = 'c'")
    names = {r["conname"] for r in rows}
    checks = ["ck_initiatives_type","ck_initiatives_trl","ck_initiatives_crl",
              "ck_initiatives_brl","ck_sessions_agent_type","ck_sessions_status",
              "ck_profiles_role","ck_evaluations_status","ck_notifications_type"]
    for c in checks:
        found = [n for n in names if n.startswith(c)]
        assert found, f"Missing: {c}"
    print(f"  [PASS] {len(checks)} CHECK constraints verified")
    passed += 1

    # 4. Sequences
    total += 1
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema='public'")
        sequences = {r["sequence_name"] for r in rows}
    assert "seq_initiative_code" in sequences
    val = await conn.fetchval("SELECT nextval('seq_initiative_code')")
    assert val > 0
    print(f"  [PASS] seq_initiative_code (next={val})")
    passed += 1

    # 5. Agent configs seeded
    total += 1
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT agent_name FROM agent_configs WHERE is_active=true")
        agents = {r["agent_name"] for r in rows}
    assert "clara" in agents
    assert "analista_oportunidad" in agents
    assert "evaluador" in agents
    print(f"  [PASS] {len(agents)} active agents: {agents}")
    passed += 1

    # 6. Monitoring
    total += 1
    async with pool.acquire() as conn:
        for t in ["profiles","sessions","messages","initiatives",
                   "evaluations","notifications","agent_configs"]:
            await conn.fetchval(f"SELECT count(*) FROM {t}")
    print("  [PASS] All tables queryable (health check)")
    passed += 1

    return passed, total


async def main():
    print("=" * 60)
    print("  Migration & Schema Validation (Step 12)")
    print("=" * 60)
    await create_pool()
    print("[OK] DB pool initialized")
    try:
        passed, total = await test_all()
        print(f"\n  [PASS] {passed}/{total} schema checks passed")
    finally:
        await close_pool()
        print("[OK] DB pool closed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
