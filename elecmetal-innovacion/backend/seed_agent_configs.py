#!/usr/bin/env python3
"""Seed agent_configs with real prompts from skill files.

Reads the skill files from skills/ and updates the agent_configs
database table with the actual prompt content.

Run: python seed_agent_configs.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import create_pool, close_pool, get_pool

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


async def seed():
    pool = get_pool()

    async with pool.acquire() as conn:
        # ── Clara (v5.4 prompt + v5.9 KB) ─────────────────────────────
        clara_prompt = (SKILLS_DIR / "Clara_Prompt_v5_4_GPT.md").read_text(encoding="utf-8")
        clara_kb = (SKILLS_DIR / "Clara_KnowledgeBase_v5_9.md").read_text(encoding="utf-8")

        clara_full = (
            f"{clara_prompt}\n\n"
            f"─── BASE DE CONOCIMIENTO ───\n\n"
            f"{clara_kb}"
        )

        await conn.execute(
            f"UPDATE agent_configs SET "
            f"prompt_text = '{clara_full[:8000].replace(chr(39), chr(39)+chr(39))}', "
            f"base_knowledge = '{clara_kb[:5000].replace(chr(39), chr(39)+chr(39))}' "
            f"WHERE agent_name = 'clara' AND is_active = true"
        )
        print(f"  [OK] Clara: prompt={len(clara_full)} chars, kb={len(clara_kb)} chars")

        # ── Analista (v2) ─────────────────────────────────────────────
        analista_prompt = (SKILLS_DIR / "prompt_analista_oportunidad_v2.md").read_text(encoding="utf-8")

        await conn.execute(
            f"UPDATE agent_configs SET "
            f"prompt_text = '{analista_prompt[:8000].replace(chr(39), chr(39)+chr(39))}' "
            f"WHERE agent_name = 'analista_oportunidad' AND is_active = true"
        )
        print(f"  [OK] Analista: prompt={len(analista_prompt)} chars")

        # ── Evaluador (v1) ────────────────────────────────────────────
        # The evaluator uses the scorecard from Clara's KB + its own prompt
        evaluador_prompt = (
            "Evaluador de Iniciativas v1 — Evalua postulaciones aprobadas por la directora.\n"
            "Genera scorecard de 22 items en 7 dimensiones (escala 1/3/5) con evidencia del DBI.\n"
            "Deriva puntaje normalizado, compuertas Sandbox/Innovacion, novedad e incertidumbre.\n"
            f"Scorecard mapping:\n{clara_kb}"
        )

        await conn.execute(
            f"UPDATE agent_configs SET "
            f"prompt_text = '{evaluador_prompt[:8000].replace(chr(39), chr(39)+chr(39))}', "
            f"base_knowledge = '{clara_kb[:5000].replace(chr(39), chr(39)+chr(39))}' "
            f"WHERE agent_name = 'evaluador' AND is_active = true"
        )
        print(f"  [OK] Evaluador: prompt={len(evaluador_prompt)} chars")

        # ── Verify ────────────────────────────────────────────────────
        rows = await conn.fetch(
            "SELECT agent_name, version, length(prompt_text) as len, is_active "
            "FROM agent_configs WHERE is_active = true ORDER BY id"
        )
        print("\n  Agent configs after seeding:")
        for r in rows:
            print(f"    {r['agent_name']} v{r['version']}: {r['len']} chars")


async def main():
    print("Seeding agent_configs with real prompts...")
    await create_pool()
    try:
        await seed()
        print("\n[DONE] agent_configs seeded successfully")
    finally:
        await close_pool()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
