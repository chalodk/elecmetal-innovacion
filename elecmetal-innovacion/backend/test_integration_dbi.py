#!/usr/bin/env python3
"""Integration test: DBI parse -> persist (Step 7 verification).

Runs against the real Supabase database via Management API.
Cleans up after itself.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.dbi_parser import parse_dbi, DBIParseError
from app.services.dbi_persistence import persist_initiative, detect_dbi_in_message
from app.core.database import create_pool, close_pool, get_pool

FIXTURES = Path(__file__).parent / "tests" / "fixtures" / "dbi"
TEST_USER_ID = "36b14f0b-ace3-46a7-bbaf-ba1bb38c8ac9"  # Usuario de Prueba


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def test_detect_heuristic():
    """Quick detection heuristics."""
    print("\n--- Test: detect_dbi_in_message ---")

    raw = _read_fixture("example_internal.txt")
    assert detect_dbi_in_message(raw), "Should detect valid DBI"
    print("  [PASS] Valid DBI detected")

    plain = "Hola, soy Clara. En que puedo ayudarte?"
    assert not detect_dbi_in_message(plain), "Should reject plain text"
    print("  [PASS] Plain text rejected")

    border_only = "=== texto === sin DOCUMENTO"
    assert not detect_dbi_in_message(border_only), "Should reject border-only text"
    print("  [PASS] Border-only text rejected")


async def test_golden_roundtrip():
    """Parse golden fixture -> persist -> verify."""
    print("\n--- Test: Golden fixture roundtrip ---")

    raw = _read_fixture("example_internal.txt")
    expected = json.loads(_read_fixture("example_internal.expected.json"))

    pool = get_pool()

    async with pool.acquire() as conn:
        # -- Create test session (let DB auto-generate ID) ---------------
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Integration Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            # -- Persist -------------------------------------------------
            initiative = await persist_initiative(
                session_id=session_id,
                user_id=TEST_USER_ID,
                dbi_text=raw,
            )

            # -- Verify core fields --------------------------------------
            assert initiative["status"] == "persistido", \
                f"Expected persistido, got {initiative['status']}"
            assert initiative["initiative_code"].startswith("INI-"), \
                "initiative_code missing"
            assert initiative["title"] == expected["header"]["title"]
            assert initiative["initiative_type"] == "interna"
            assert initiative["area"] == expected["header"]["area"]
            assert initiative["applicant_name"] == expected["header"]["applicant_name"]
            assert initiative["trl"] == 4, \
                f"TRL expected 4, got {initiative['trl']}"
            assert initiative["crl"] == 5, \
                f"CRL expected 5, got {initiative['crl']}"
            assert initiative["brl"] == 4, \
                f"BRL expected 4, got {initiative['brl']}"
            assert initiative["scalability"] == "Interna"
            assert initiative["return_horizon"] == 12
            assert initiative["external_client"] is None  # "No aplica" -> NULL
            assert initiative["strategic_alignment"] is None  # "por asignar" -> NULL
            assert initiative["dbi_raw_text"] == raw
            assert initiative["dbi_extra"] is not None

            extra = initiative["dbi_extra"]
            assert extra.get("executive_summary") == expected["executive_summary"]
            # Empty lists are not stored in dbi_extra (falsy optimization)
            assert extra.get("pending_blocks") in (None, [])
            assert extra.get("attached_evidence") == expected["attached_evidence"]
            assert extra.get("block_a_extra", {}).get("why_it_matters") is not None
            assert extra.get("block_b_extra", {}).get("trl_evidence") is not None
            assert extra.get("block_f_extra", {}).get("brl_evidence") is not None

            # -- Verify session transitioned -----------------------------
            session_row = await conn.fetchrow(
                f"SELECT status, ended_at FROM sessions WHERE id = {session_id}"
            )
            assert session_row["status"] == "completed", \
                f"Session should be completed, got {session_row['status']}"
            assert session_row["ended_at"] is not None, "ended_at should be set"

            print(f"  [PASS] Initiative persisted: {initiative['initiative_code']}")
            print(f"     ID: {initiative['id']}")
            print(f"     Title: {initiative['title']}")
            print(f"     TRL: {initiative['trl']} | CRL: {initiative['crl']} | BRL: {initiative['brl']}")
            print(f"     dbi_extra keys: {list(extra.keys())}")
            print(f"     Session {session_id} -> completed [OK]")

        finally:
            # -- Cleanup ------------------------------------------------
            await conn.execute(
                f"DELETE FROM initiatives WHERE session_id = {session_id}"
            )
            await conn.execute(
                f"DELETE FROM messages WHERE session_id = {session_id}"
            )
            await conn.execute(
                f"DELETE FROM sessions WHERE id = {session_id}"
            )
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_dbi_in_conversation():
    """Simulate what Clara actually returns: DBI embedded in conversational text."""
    print("\n--- Test: DBI embedded in conversation ---")

    raw = _read_fixture("example_internal.txt")

    # Simulate a real Clara response
    clara_response = (
        "Excelente trabajo! He procesado toda la informacion y he generado "
        "tu Documento Base de Iniciativa:\n\n"
        f"{raw}\n\n"
        "Tu iniciativa ha quedado registrada con exito. "
        "Necesitas ayuda con algo mas?"
    )

    assert detect_dbi_in_message(clara_response), "Should detect DBI in conversation"
    print("  [PASS] DBI detected in conversation text")

    # Parse should still work -- parser finds borders regardless of
    # surrounding text
    parsed = parse_dbi(clara_response)
    assert parsed["header"]["title"] == "Mantenimiento predictivo de hornos"
    assert parsed["block_b_solution"]["trl"]["level"] == 4
    print("  [PASS] DBI correctly parsed from conversation wrapper")


async def test_parse_errors():
    """Verify that invalid DBI is rejected (all-or-nothing contract)."""
    print("\n--- Test: Parse error rejection ---")

    raw = _read_fixture("example_internal.txt")

    # Invalid TRL level
    bad = raw.replace("• TRL: 4", "• TRL: 12")
    try:
        parse_dbi(bad)
        assert False, "Should have raised DBIParseError"
    except DBIParseError as e:
        print(f"  [PASS] Invalid TRL rejected: {e}")

    # Missing required block (C)
    bad2 = raw.replace("C. CLIENTE", "X. OTRO")
    try:
        parse_dbi(bad2)
        assert False, "Should have raised DBIParseError"
    except DBIParseError as e:
        print(f"  [PASS] Missing block rejected: {e}")

    # Missing borders
    try:
        parse_dbi("DOCUMENTO BASE DE INICIATIVA\nA. PROBLEMA\n- Problema: x")
        assert False, "Should have raised DBIParseError"
    except DBIParseError as e:
        print(f"  [PASS] Missing borders rejected: {e}")


async def test_persist_with_parse_error():
    """persist_initiative should raise DBIParseError and NOT create anything."""
    print("\n--- Test: Persist fails cleanly on parse error ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Error Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            await persist_initiative(
                session_id=session_id,
                user_id=TEST_USER_ID,
                dbi_text="This is not a DBI",
            )
            assert False, "Should have raised DBIParseError"
        except DBIParseError:
            # Verify session is still active (NOT completed)
            session_row = await conn.fetchrow(
                f"SELECT status FROM sessions WHERE id = {session_id}"
            )
            assert session_row["status"] == "active", \
                "Session should remain active after failed parse"
            print("  [PASS] Session unchanged after failed parse")

        finally:
            await conn.execute(
                f"DELETE FROM initiatives WHERE session_id = {session_id}"
            )
            await conn.execute(
                f"DELETE FROM messages WHERE session_id = {session_id}"
            )
            await conn.execute(
                f"DELETE FROM sessions WHERE id = {session_id}"
            )
            print("     [CLEAN] Removed")


async def main():
    print("=" * 60)
    print("  DBI Parse & Persist - Integration Tests (Step 7)")
    print("=" * 60)

    # Initialize DB pool
    await create_pool()
    print("[OK] DB pool initialized")

    try:
        await test_detect_heuristic()
        await test_golden_roundtrip()
        await test_dbi_in_conversation()
        await test_parse_errors()
        await test_persist_with_parse_error()

        print("\n" + "=" * 60)
        print("  [PASS] ALL INTEGRATION TESTS PASSED")
        print("=" * 60)

    finally:
        await close_pool()
        print("[OK] DB pool closed")


if __name__ == "__main__":
    # Force UTF-8 for stdout on Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
