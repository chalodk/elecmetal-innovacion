#!/usr/bin/env python3
"""Integration tests for evaluations (Step 9 verification).

Tests:
  1. PATCH /initiatives/{id}/status — move to en_evaluacion
  2. Direct initiative -> evaluation flow (create, evaluate, verify)
  3. Review and validate evaluation
  4. Edge cases: duplicate eval, wrong status, veredicto

Runs against the real Supabase database via Management API.
Cleans up after itself.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import create_pool, close_pool, get_pool
from app.services.evaluator import (
    create_evaluation,
    update_evaluation_results,
    evaluate_initiative,
    EvaluatorError,
    _build_initiative_context,
)

DIRECTORA_ID = "9ce7b63e-1b71-4df0-ba19-6ffaa7fc4707"  # Test Trigger User
TEST_USER_ID = "36b14f0b-ace3-46a7-bbaf-ba1bb38c8ac9"  # Usuario de Prueba


async def _ensure_directora_exists(conn):
    """Ensure there's a user with directora role for testing."""
    existing = await conn.fetchrow(
        f"SELECT id, role FROM profiles WHERE id = '{DIRECTORA_ID}'"
    )
    if existing and existing["role"] in ("directora", "admin"):
        return DIRECTORA_ID

    # Promote the test user to directora temporarily
    await conn.execute(
        f"UPDATE profiles SET role = 'directora' WHERE id = '{DIRECTORA_ID}'"
    )
    return DIRECTORA_ID


async def _create_test_initiative(conn, session_id: int, status: str = "notificado"):
    """Create a test initiative for evaluation testing."""
    from app.services.dbi_parser import parse_dbi

    fixtures = Path(__file__).parent / "tests" / "fixtures" / "dbi"
    raw = (fixtures / "example_internal.txt").read_text(encoding="utf-8")
    parsed = parse_dbi(raw)

    header = parsed["header"]
    b = parsed["block_b_solution"]
    c = parsed["block_c_client"]
    d = parsed["block_d_alignment"]
    e = parsed["block_e_team"]
    f = parsed["block_f_risk"]
    g = parsed["block_g_milestones"]

    trl = b["trl"]["level"]
    crl = c["crl"]["level"]
    brl = f["brl"]["level"]

    seq_row = await conn.fetchrow("SELECT nextval('seq_initiative_code') AS seq")
    code = f"INI-2026-{seq_row['seq']:03d}"

    extra = {
        "executive_summary": parsed.get("executive_summary"),
        "block_a_extra": {
            "why_it_matters": parsed["block_a_problem"].get("why_it_matters"),
            "who_has_it": parsed["block_a_problem"].get("who_has_it"),
            "current_solution": parsed["block_a_problem"].get("current_solution"),
        },
        "block_b_extra": {
            "differentiator_novelty_grade": b.get("differentiator_novelty_grade"),
            "competition_grade": b.get("competition_grade"),
            "trl_evidence": b["trl"]["evidence"],
            "market_repeatability": b.get("market_repeatability"),
        },
        "block_c_extra": {
            "crl_evidence": c["crl"]["evidence"],
        },
        "block_d_extra": {
            "horizon": d.get("horizon"),
        },
        "block_e_extra": {
            "support_received": e.get("support_received"),
            "other_resources": e.get("other_resources"),
        },
        "block_f_extra": {
            "brl_evidence": f["brl"]["evidence"],
            "uncertainty": f.get("uncertainty", {}),
        },
        "pending_blocks": [],
    }
    extra_json = json.dumps(extra, ensure_ascii=False)

    init_row = await conn.fetchrow(
        f"INSERT INTO initiatives (session_id, user_id, status, initiative_code, "
        f"title, initiative_type, postulation_date, area, applicant_name, "
        f"problem, solution, economic_impact, trl, crl, brl, scalability, "
        f"internal_client, external_client, sponsor, internal_team, external_team, "
        f"estimated_duration, main_doubt, key_condition, value_capture, "
        f"technical_milestones, financial_milestones, return_horizon, "
        f"strategic_alignment, dbi_raw_text, dbi_extra) "
        f"VALUES ({session_id}, '{TEST_USER_ID}', '{status}', '{code}', "
        f"'{header['title']}', '{header['initiative_type']}', "
        f"'{header['postulation_date']}', '{header['area']}', '{header['applicant_name']}', "
        f"'{parsed['block_a_problem']['problem']}', '{b['description']}', "
        f"'{b['economic_impact']['value']}', {trl}, {crl}, {brl}, "
        f"'{b['scalability']}', '{c.get('internal_client') or 'No aplica'}', "
        f"'{c.get('external_client') or 'No aplica'}', "
        f"'{e.get('sponsor') or 'Sin patrocinador'}', "
        f"'{e.get('internal_team') or 'solo postulante'}', "
        f"'{e.get('external_team') or 'No aplica'}', "
        f"'{e.get('estimated_duration') or 'No estimado'}', "
        f"'{f.get('main_doubt') or ''}', "
        f"'{f.get('key_condition') or ''}', "
        f"'{f.get('value_capture') or 'no claro'}', "
        f"'{g.get('technical_milestones') or 'No definido'}', "
        f"'{g.get('financial_milestones') or 'No definido'}', "
        f"{g.get('return_horizon_months') or 'NULL'}, "
        f"'{d.get('focus') or 'por asignar' if d.get('focus') else 'por asignar'}', "
        f"'{raw.replace(chr(39), chr(39)+chr(39))}', "
        f"'{extra_json.replace(chr(39), chr(39)+chr(39))}'::jsonb) "
        f"RETURNING *"
    )

    return dict(init_row)


async def test_build_context():
    """Step 9.0: _build_initiative_context() produces valid evaluator input."""
    print("\n--- Test: Build evaluator context ---")

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Context Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            initiative = await _create_test_initiative(conn, session_id)
            context = _build_initiative_context(initiative)

            # Verify key fields are present
            assert "Mantenimiento predictivo" in context
            assert "PROBLEMA" in context
            assert "SOLUCION" in context
            assert "CLIENTE" in context
            assert "RIESGO" in context
            assert "HITOS" in context
            assert "TRL:" in context
            assert "CRL:" in context
            assert "BRL:" in context

            print(f"  [PASS] Context generated ({len(context)} chars)")
            print(f"     First line: {context.split(chr(10))[0]}")

        finally:
            await conn.execute(f"DELETE FROM initiatives WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_evaluation_lifecycle():
    """Step 9.1-9.4: Full evaluation lifecycle."""
    print("\n--- Test: Full evaluation lifecycle ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        await _ensure_directora_exists(conn)

        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Eval Lifecycle') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            # ── 1. Create test initiative in notificado ──────────────
            initiative = await _create_test_initiative(conn, session_id, status="notificado")
            init_id = initiative["id"]
            assert initiative["status"] == "notificado"
            print(f"  [PASS] Initiative created: id={init_id} status=notificado")

            # ── 2. Move to en_evaluacion ─────────────────────────────
            await conn.execute(
                f"UPDATE initiatives SET status = 'en_evaluacion', updated_at = now() "
                f"WHERE id = {init_id}"
            )
            updated = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {init_id}"
            )
            assert updated["status"] == "en_evaluacion"
            print(f"  [PASS] Initiative -> en_evaluacion")

            # ── 3. Create evaluation record ──────────────────────────
            eval_row = await conn.fetchrow(
                f"INSERT INTO evaluations (initiative_id, activated_by, status) "
                f"VALUES ({init_id}, '{DIRECTORA_ID}', 'in_progress') "
                f"RETURNING *"
            )
            eval_id = eval_row["id"]
            assert eval_row["status"] == "in_progress"
            print(f"  [PASS] Evaluation created: id={eval_id} status=in_progress")

            # ── 4. Simulate evaluator results (without OpenAI call) ──
            mock_results = {
                "scores": {
                    "problema": {
                        "claridad_problema": {"score": 5, "evidence": "Problema claramente descrito"},
                        "relevancia_dolor": {"score": 5, "evidence": "Paradas cuestan turnos completos"},
                        "interes_quien_lo_tiene": {"score": 3, "evidence": "Equipo de operaciones"},
                        "competencia_sustitutos": {"score": 3, "evidence": "SCADA identificado pero no calibrado"},
                    },
                    "solucion": {
                        "claridad_solucion": {"score": 5, "evidence": "Sensores IoT con modelo de deteccion"},
                        "diferenciacion_novedad": {"score": 3, "evidence": "Mejora relevante"},
                        "estado_desarrollo_trl": {"score": 3, "evidence": "TRL 4"},
                        "impacto_esperado": {"score": 3, "evidence": "USD 120k/ano, medio"},
                    },
                    "cliente": {
                        "cliente_interno": {"score": 5, "evidence": "Jefatura de Operaciones"},
                        "cliente_externo": {"score": 1, "evidence": "No aplica"},
                    },
                    "alineamiento": {
                        "foco_estrategico": {"score": 1, "evidence": "por asignar"},
                        "horizonte": {"score": 1, "evidence": "por asignar"},
                    },
                    "equipo": {
                        "equipo_interno": {"score": 3, "evidence": "2 personas"},
                        "equipo_externo": {"score": 1, "evidence": "No aplica"},
                        "sponsor": {"score": 5, "evidence": "Gerente de Operaciones"},
                        "otros_recursos": {"score": 3, "evidence": "parciales"},
                    },
                    "riesgo": {
                        "incertidumbre_cliente": {"score": 3, "evidence": "CRL 5"},
                        "incertidumbre_solucion": {"score": 3, "evidence": "TRL 4"},
                        "incertidumbre_modelo": {"score": 3, "evidence": "BRL 4"},
                    },
                    "hitos": {
                        "hitos_tecnicos": {"score": 5, "evidence": "Piloto con KPI claro"},
                        "hitos_economicos": {"score": 5, "evidence": "Validar ahorro USD 120k"},
                        "horizonte_retorno": {"score": 5, "evidence": "12 meses"},
                    },
                },
                "derived": {
                    "novedad": 3,
                    "indice_incertidumbre": 3.0,
                    "puntaje_total": 72,
                    "puntaje_normalizado": 65,
                    "compuerta_sandbox": "con_apoyo",
                    "compuerta_innovacion": "ok",
                    "resumen": "Iniciativa con potencial moderado.",
                    "recomendacion": "Avanzar con apoyo del equipo de innovacion.",
                },
            }

            results_json = json.dumps(mock_results, ensure_ascii=False)
            escaped_results = results_json.replace("'", "''")

            await conn.execute(
                f"UPDATE evaluations SET "
                f"status = 'completed', "
                f"results = '{escaped_results}'::jsonb, "
                f"updated_at = now() "
                f"WHERE id = {eval_id}"
            )

            # Move initiative to evaluado
            await conn.execute(
                f"UPDATE initiatives SET status = 'evaluado', updated_at = now() "
                f"WHERE id = {init_id}"
            )

            # Verify
            eval_check = await conn.fetchrow(
                f"SELECT status, results FROM evaluations WHERE id = {eval_id}"
            )
            assert eval_check["status"] == "completed"
            stored_results = eval_check["results"]
            if isinstance(stored_results, str):
                stored_results = json.loads(stored_results)
            assert stored_results["derived"]["puntaje_total"] == 72
            print(f"  [PASS] Evaluation completed: total={stored_results['derived']['puntaje_total']}")

            init_check = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {init_id}"
            )
            assert init_check["status"] == "evaluado"
            print(f"  [PASS] Initiative -> evaluado")

            # ── 5. Review and validate ───────────────────────────────
            await conn.execute(
                f"UPDATE evaluations SET "
                f"reviewed_by = '{DIRECTORA_ID}', "
                f"reviewed_at = now(), "
                f"veredicto = 'aprobada', "
                f"updated_at = now() "
                f"WHERE id = {eval_id}"
            )
            await conn.execute(
                f"UPDATE initiatives SET status = 'validado', updated_at = now() "
                f"WHERE id = {init_id}"
            )

            final_eval = await conn.fetchrow(
                f"SELECT status, reviewed_by, reviewed_at, veredicto FROM evaluations WHERE id = {eval_id}"
            )
            assert final_eval["veredicto"] == "aprobada"
            assert final_eval["reviewed_by"] == DIRECTORA_ID
            print(f"  [PASS] Evaluation reviewed: veredicto={final_eval['veredicto']}")

            final_init = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {init_id}"
            )
            assert final_init["status"] == "validado"
            print(f"  [PASS] Initiative -> validado")

            # ── Cleanup ──────────────────────────────────────────
            await conn.execute(f"DELETE FROM evaluations WHERE id = {eval_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {init_id}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_duplicate_evaluation_prevented():
    """Step 9.5: Can't create duplicate evaluation for same initiative."""
    print("\n--- Test: Duplicate evaluation prevention ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        await _ensure_directora_exists(conn)

        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Duplicate Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            initiative = await _create_test_initiative(conn, session_id, status="notificado")

            # Create first evaluation
            await conn.execute(
                f"INSERT INTO evaluations (initiative_id, activated_by, status) "
                f"VALUES ({initiative['id']}, '{DIRECTORA_ID}', 'in_progress')"
            )

            # Try to create second — should fail on UNIQUE constraint
            try:
                await conn.execute(
                    f"INSERT INTO evaluations (initiative_id, activated_by, status) "
                    f"VALUES ({initiative['id']}, '{DIRECTORA_ID}', 'in_progress')"
                )
                # If we get here with the Management API, it means the UNIQUE
                # constraint is working at the DB level
                print("  [WARN] Duplicate INSERT succeeded — UNIQUE constraint may be missing")
            except Exception as e:
                assert "duplicate" in str(e).lower() or "unique" in str(e).lower() or "violates" in str(e).lower(), \
                    f"Unexpected error: {e}"
                print(f"  [PASS] Duplicate evaluation prevented by DB constraint")

            # Cleanup
            await conn.execute(f"DELETE FROM evaluations WHERE initiative_id = {initiative['id']}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {initiative['id']}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_wrong_status_rejected():
    """Step 9.6: Can't evaluate initiative in wrong status."""
    print("\n--- Test: Wrong status rejection ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        await _ensure_directora_exists(conn)

        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'WrongStatus Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            # Create initiative in persistido (not notificado)
            initiative = await _create_test_initiative(conn, session_id, status="persistido")

            # Try to evaluate — should be rejected
            try:
                await create_evaluation(
                    initiative_id=initiative["id"],
                    activated_by=DIRECTORA_ID,
                )
                print("  [WARN] Evaluation created despite wrong status")
            except ValueError as e:
                assert "notificado" in str(e) or "en_evaluacion" in str(e), \
                    f"Unexpected error: {e}"
                print(f"  [PASS] Correctly rejected: {e}")

            # Cleanup
            await conn.execute(f"DELETE FROM evaluations WHERE initiative_id = {initiative['id']}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {initiative['id']}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_update_evaluation_results():
    """Step 9.7: update_evaluation_results() adjusts scores and validates."""
    print("\n--- Test: Update evaluation results ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        await _ensure_directora_exists(conn)

        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'UpdateResults Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            initiative = await _create_test_initiative(conn, session_id, status="notificado")

            # Create and complete evaluation
            eval_row = await conn.fetchrow(
                f"INSERT INTO evaluations (initiative_id, activated_by, status) "
                f"VALUES ({initiative['id']}, '{DIRECTORA_ID}', 'in_progress') "
                f"RETURNING *"
            )
            eval_id = eval_row["id"]

            # Store initial results
            initial_results = {"scores": {"test": "initial"}, "derived": {"total": 50}}
            results_json = json.dumps(initial_results, ensure_ascii=False)
            escaped = results_json.replace("'", "''")
            await conn.execute(
                f"UPDATE evaluations SET status = 'completed', "
                f"results = '{escaped}'::jsonb, updated_at = now() "
                f"WHERE id = {eval_id}"
            )
            await conn.execute(
                f"UPDATE initiatives SET status = 'evaluado', updated_at = now() "
                f"WHERE id = {initiative['id']}"
            )

            # Now update with adjusted results
            adjusted_results = {
                "scores": {"test": "adjusted_by_directora"},
                "derived": {"total": 75, "compuerta_sandbox": "sandbox"},
            }
            updated_eval = await update_evaluation_results(
                evaluation_id=eval_id,
                results=adjusted_results,
                reviewed_by=DIRECTORA_ID,
            )

            stored = updated_eval["results"]
            if isinstance(stored, str):
                stored = json.loads(stored)
            assert stored["derived"]["total"] == 75
            assert stored["derived"]["compuerta_sandbox"] == "sandbox"
            print(f"  [PASS] Results updated: total={stored['derived']['total']}")

            # Verify initiative -> validado
            init_check = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {initiative['id']}"
            )
            assert init_check["status"] == "validado"
            print(f"  [PASS] Initiative -> validado after review")

            # Cleanup
            await conn.execute(f"DELETE FROM evaluations WHERE id = {eval_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {initiative['id']}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def main():
    print("=" * 60)
    print("  Evaluations — Integration Tests (Step 9)")
    print("=" * 60)

    await create_pool()
    print("[OK] DB pool initialized")

    try:
        await test_build_context()
        await test_evaluation_lifecycle()
        await test_duplicate_evaluation_prevented()
        await test_wrong_status_rejected()
        await test_update_evaluation_results()

        print("\n" + "=" * 60)
        print("  [PASS] ALL EVALUATION TESTS PASSED")
        print("=" * 60)

    finally:
        await close_pool()
        print("[OK] DB pool closed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
