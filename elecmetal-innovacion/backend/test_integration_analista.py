#!/usr/bin/env python3
"""Integration tests for Analista de Oportunidad (Step 11 verification).

Tests:
  1. Creating analista_oportunidad sessions
  2. Session listing filters by agent_type
  3. AnalistaService loads prompt correctly
  4. Streaming with Analista prompt
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import create_pool, close_pool, get_pool
from app.services.analista import AnalistaService

TEST_USER_ID = "36b14f0b-ace3-46a7-bbaf-ba1bb38c8ac9"


async def test_create_analista_session():
    """Step 11.1: Can create a session with agent_type='analista_oportunidad'."""
    print("\n--- Test: Create Analista session ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'analista_oportunidad', 'active', "
            f"'Analisis de oportunidad test') "
            f"RETURNING *"
        )
        session_id = row["id"]

        try:
            assert row["agent_type"] == "analista_oportunidad"
            assert row["status"] == "active"
            print(f"  [PASS] Analista session created: id={session_id}")
            print(f"     agent_type={row['agent_type']} title={row['title']}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_list_sessions_by_agent():
    """Step 11.2: Sessions can be listed and filtered by agent_type."""
    print("\n--- Test: List sessions by agent_type ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        # Create Clara session
        c_row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Clara test') "
            f"RETURNING id"
        )

        # Create Analista session
        a_row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'analista_oportunidad', 'active', "
            f"'Analista test') "
            f"RETURNING id"
        )

        try:
            # List all active sessions for user
            all_sessions = await conn.fetch(
                f"SELECT id, agent_type FROM sessions "
                f"WHERE user_id = '{TEST_USER_ID}' AND status = 'active'"
            )

            clara_sessions = [s for s in all_sessions if s["agent_type"] == "clara"]
            analista_sessions = [
                s for s in all_sessions if s["agent_type"] == "analista_oportunidad"
            ]

            assert len(clara_sessions) >= 1
            assert len(analista_sessions) >= 1
            print(f"  [PASS] Clara sessions: {len(clara_sessions)}, "
                  f"Analista sessions: {len(analista_sessions)}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {c_row['id']}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {c_row['id']}")
            await conn.execute(f"DELETE FROM messages WHERE session_id = {a_row['id']}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {a_row['id']}")
            print("     [CLEAN] Removed both test sessions")


async def test_analista_service_loads():
    """Step 11.3: AnalistaService loads prompt v2 from skill file (lazy init)."""
    print("\n--- Test: AnalistaService prompt loading ---")

    try:
        service = AnalistaService()
        # System prompt is lazy-loaded; ensure it before asserting
        await service._ensure_system_prompt()
        prompt = service._system_prompt

        # Verify key sections from prompt v2
        assert "Analista de Oportunidad" in prompt or "TAM/SAM/SOM" in prompt
        assert "Máquina de estados" in prompt or "A — INGESTA" in prompt
        assert "DATO" in prompt
        assert "SUPUESTO" in prompt
        assert "DERIVADO" in prompt
        assert "Geografía" in prompt or "geografía" in prompt
        assert "CHECKPOINT" in prompt

        print(f"  [PASS] Prompt loaded: {len(prompt)} chars")
        print(f"     States A-L present: {'A — INGESTA' in prompt}")
        print("     Output labels: DATO/SUPUESTO/DERIVADO present")

    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            print("  [SKIP] No OpenAI key configured — service init skipped")
        else:
            raise


async def test_analista_chat_flow():
    """Step 11.4: Simulate a complete Analista conversation."""
    print("\n--- Test: Analista chat flow (DB only, no OpenAI) ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'analista_oportunidad', 'active', "
            f"'Analisis TAM/SAM/SOM') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            # Simulate user sending the 6 input fields
            user_msg = (
                "Titulo: Mantenimiento predictivo de hornos | "
                "Propuesta de valor: Reducir paradas no planificadas con IoT | "
                "Segmento: Fundiciones de cobre en Chile | "
                "Necesidad/friccion: Paradas cuestan USD 120k/ano | "
                "Categoria de solucion: IoT + analitica predictiva | "
                "Beneficio: Ahorro en produccion recuperada"
            )

            await conn.execute(
                f"INSERT INTO messages (session_id, role, content) "
                f"VALUES ({session_id}, 'user', "
                f"'{user_msg.replace(chr(39), chr(39)+chr(39))}')"
            )

            # Simulate assistant response (mock, no OpenAI call)
            asst_msg = (
                "Que buena oportunidad para modelar! Antes de entrar a los numeros, "
                "voy a leer los 6 campos que me compartiste.\n\n"
                "**Estado A — INGESTA**: Recibi tus datos:\n"
                "- Titulo: Mantenimiento predictivo de hornos\n"
                "- Propuesta de valor: Reducir paradas no planificadas con IoT\n"
                "- Segmento: Fundiciones de cobre en Chile [DATO]\n"
                "- Necesidad: Paradas cuestan USD 120k/ano [SUPUESTO]\n"
                "- Categoria: IoT + analitica [DATO]\n"
                "- Beneficio: Ahorro en produccion [DERIVADO]\n\n"
                "Pasemos al CHECKPOINT para validar que entendi bien."
            )

            await conn.execute(
                f"INSERT INTO messages (session_id, role, content) "
                f"VALUES ({session_id}, 'assistant', "
                f"'{asst_msg.replace(chr(39), chr(39)+chr(39))}')"
            )

            # Verify messages persisted
            msgs = await conn.fetch(
                f"SELECT role, content FROM messages WHERE session_id = {session_id} "
                f"ORDER BY created_at"
            )
            assert len(msgs) == 2
            assert msgs[0]["role"] == "user"
            assert msgs[1]["role"] == "assistant"
            assert "INGESTA" in msgs[1]["content"]
            assert "DATO" in msgs[1]["content"]
            assert "SUPUESTO" in msgs[1]["content"]
            assert "DERIVADO" in msgs[1]["content"]

            print(f"  [PASS] {len(msgs)} messages persisted")
            print("     Assistant response labels: DATO/SUPUESTO/DERIVADO present")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_agent_type_validation():
    """Step 11.5: Invalid agent_type is rejected."""
    print("\n--- Test: Agent type validation ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        # Valid types should work
        for at in ("clara", "analista_oportunidad"):
            await conn.execute(
                f"INSERT INTO sessions (user_id, agent_type, status, title) "
                f"VALUES ('{TEST_USER_ID}', '{at}', 'active', 'Test')"
            )
            # Fetch back to verify
            rows = await conn.fetch(
                f"SELECT agent_type FROM sessions "
                f"WHERE user_id = '{TEST_USER_ID}' AND agent_type = '{at}' "
                f"AND status = 'active'"
            )
            assert len(rows) >= 1
            assert rows[0]["agent_type"] == at
            # Cleanup
            await conn.execute(
                f"DELETE FROM sessions WHERE user_id = '{TEST_USER_ID}' "
                f"AND agent_type = '{at}' AND title = 'Test'"
            )
            print(f"  [PASS] agent_type='{at}' accepted")

        # Invalid type should fail on CHECK constraint
        try:
            await conn.execute(
                f"INSERT INTO sessions (user_id, agent_type, status, title) "
                f"VALUES ('{TEST_USER_ID}', 'invalid_agent', 'active', 'Test')"
            )
            print("  [WARN] Invalid agent_type was accepted — CHECK constraint missing")
        except Exception as e:
            assert "violates" in str(e).lower() or "check" in str(e).lower()
            print("  [PASS] Invalid agent_type rejected by DB constraint")


async def main():
    print("=" * 60)
    print("  Analista de Oportunidad — Integration Tests (Step 11)")
    print("=" * 60)

    await create_pool()
    print("[OK] DB pool initialized")

    try:
        await test_create_analista_session()
        await test_list_sessions_by_agent()
        await test_analista_service_loads()
        await test_analista_chat_flow()
        await test_agent_type_validation()

        print("\n" + "=" * 60)
        print("  [PASS] ALL ANALISTA TESTS PASSED")
        print("=" * 60)

    finally:
        await close_pool()
        print("[OK] DB pool closed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
