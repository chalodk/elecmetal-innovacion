"""Evaluator service (Step 9 of the boot sequence).

Orchestrates the evaluation of an initiative using OpenAI GPT-4o.
Loads the evaluador prompt from agent_configs and the scorecard
mapping from Clara's knowledge base.

Architecture:
  - evaluate_initiative(): called by the API endpoint, receives full DBI data,
    calls OpenAI in batch mode, parses results, stores them as JSONB.
  - The evaluator scores 22 items (1/3/5 scale) across 7 dimensions,
    computes derived scores (novedad, incertidumbre, compuertas), and
    returns the complete scorecard.

Scorecard mapping (from Clara_KnowledgeBase_v5_9.md > Mapeo DBI -> Scorecard):
  Dimension (weight):
    Problema (15), Solucion (20), Cliente (10), Alineamiento (10),
    Equipo (15), Riesgo (20), Hitos (10) = 100 max
  Gates:
    Novedad: similar=1 / mejora relevante=3 / nuevo=5
    Incertidumbre avg: >2 allows Sandbox entry
    Total: <60 fuera / 60-80 con apoyo / >80 Sandbox
"""

from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_pool

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"
_TEMPERATURE = 0.3  # Low temperature for consistent scoring


# ── Scorecard generation prompt (anchored in KB v5.9) ─────────────────────

EVALUATOR_SYSTEM_PROMPT = """Eres el Evaluador de Iniciativas de Innovacion de ME Elecmetal.

Tu tarea es evaluar una iniciativa basandote UNICAMENTE en la evidencia del DBI.
Puntua cada item en escala 1/3/5 segun las rubricas documentadas en la Knowledge Base v5.9.

## Reglas de puntuacion

### Problema (peso 15, 4 items)
1. Claridad del problema (campo A: problema): 1=vago, 3=claro pero generico, 5=especifico y concreto
2. Relevancia/dolor (campo A: por que importa): 1=menor, 3=significativo, 5=critico para el negocio
3. Interes de quien lo tiene (campos A: quien lo tiene + C: CRL): 1=supuesto, 3=confirmado por el area, 5=area pidio avanzar
4. Competencia/sustitutos (campo B: competencia): 1=no analizado, 3=identificados, 5=analizados y diferenciados

### Solucion (peso 20, 4 items)
5. Claridad de la solucion (campo B: descripcion): 1=vaga, 3=clara, 5=detallada y concreta
6. Diferenciacion/novedad (campo B: diferenciador): similar=1, mejora relevante=3, nuevo=5
7. Estado de desarrollo/TRL (campo B: TRL): 1-2=1, 3-6=3, 7-9=5
8. Impacto esperado (campos B: impacto economico + beneficiario): bajo=1, medio=3, alto=5

### Cliente (peso 10, 2 items)
9. Cliente/usuario interno (campo C: interno): no claro=1, identificado=3, comprometido=5
10. Cliente/usuario externo (campos C: externo + CRL): no aplica/no claro=1, identificado=3, validado=5

### Alineamiento (peso 10, 2 items)
11. Foco estrategico (campo D: foco): por asignar=1, asignado=3, alineado con prioridad=5
12. Horizonte (campo D: horizonte): por asignar=1, asignado=3, H1 alineado=5 (H2=4, H3=3)

### Equipo (peso 15, 4 items)
13. Equipo interno (campo E: equipo interno): solo postulante=1, equipo parcial=3, equipo completo=5
14. Equipo externo (campo E: equipo externo): no aplica=1, identificado=3, comprometido=5
15. Sponsor (campo E: patrocinador): sin patrocinador=1, identificado=3, activo=5
16. Otros recursos (campo E: otros recursos): no claros=1, parciales=3, claros y disponibles=5

### Riesgo (peso 20, 3 items)
17. Incertidumbre cliente (invertida, campo F + CRL): CRL 6-9=1, 4-5=3, 1-3=5
18. Incertidumbre solucion (invertida, campo F + TRL): TRL 7-9=1, 3-6=3, 1-2=5
19. Incertidumbre modelo (invertida, campo F + BRL): BRL 6-9=1, 3-5=3, 1-2=5

### Hitos (peso 10, 3 items)
20. Hitos tecnicos/operativos (campo G: tecnicos): no definido=1, parcial=3, claro con KPI=5
21. Hitos economicos (campo G: economicos): no definido=1, parcial=3, claro con KPI=5
22. Horizonte de retorno (campo G: return_horizon): >24 meses=1, 18-24=3, <18=5

## Puntajes derivados
- Novedad (item 6): similar=1, mejora relevante=3, nuevo=5
- Indice de Incertidumbre: promedio(items 17, 18, 19)
- Compuerta Sandbox: Novedad <= 2 AND Incertidumbre <= 2 -> fuera de innovacion (derivar a area)
- Puntaje total: suma de los 22 items (max 110, pero normalizado a 100)
- Compuerta puntaje: <60 fuera / 60-80 con apoyo / >80 Sandbox

## Formato de respuesta
Responde UNICAMENTE con un JSON valido, sin markdown ni texto adicional:

{
  "scores": {
    "problema": {
      "claridad_problema": {"score": 3, "evidence": "..."},
      "relevancia_dolor": {"score": 3, "evidence": "..."},
      "interes_quien_lo_tiene": {"score": 3, "evidence": "..."},
      "competencia_sustitutos": {"score": 3, "evidence": "..."}
    },
    "solucion": {
      "claridad_solucion": {"score": 3, "evidence": "..."},
      "diferenciacion_novedad": {"score": 3, "evidence": "..."},
      "estado_desarrollo_trl": {"score": 3, "evidence": "..."},
      "impacto_esperado": {"score": 3, "evidence": "..."}
    },
    "cliente": {
      "cliente_interno": {"score": 3, "evidence": "..."},
      "cliente_externo": {"score": 3, "evidence": "..."}
    },
    "alineamiento": {
      "foco_estrategico": {"score": 3, "evidence": "..."},
      "horizonte": {"score": 3, "evidence": "..."}
    },
    "equipo": {
      "equipo_interno": {"score": 3, "evidence": "..."},
      "equipo_externo": {"score": 3, "evidence": "..."},
      "sponsor": {"score": 3, "evidence": "..."},
      "otros_recursos": {"score": 3, "evidence": "..."}
    },
    "riesgo": {
      "incertidumbre_cliente": {"score": 3, "evidence": "..."},
      "incertidumbre_solucion": {"score": 3, "evidence": "..."},
      "incertidumbre_modelo": {"score": 3, "evidence": "..."}
    },
    "hitos": {
      "hitos_tecnicos": {"score": 3, "evidence": "..."},
      "hitos_economicos": {"score": 3, "evidence": "..."},
      "horizonte_retorno": {"score": 3, "evidence": "..."}
    }
  },
  "derived": {
    "novedad": 3,
    "indice_incertidumbre": 3.0,
    "puntaje_total": 66,
    "puntaje_normalizado": 60,
    "compuerta_sandbox": "con_apoyo",
    "compuerta_innovacion": "ok",
    "resumen": "Iniciativa con potencial moderado. ...",
    "recomendacion": "Avanzar con apoyo del equipo de innovacion para fortalecer ..."
  }
}
"""


# ── DB helper ──────────────────────────────────────────────────────────────

def _sql_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_initiative_context(initiative: dict) -> str:
    """Build a text representation of initiative data for the evaluator."""
    parts: list[str] = []

    parts.append(f"Titulo: {initiative.get('title', 'Sin titulo')}")
    parts.append(f"Tipo: {initiative.get('initiative_type', 'interna')}")
    parts.append(f"Area: {initiative.get('area', 'No especificada')}")
    parts.append(f"Postulante: {initiative.get('applicant_name', 'No especificado')}")

    parts.append("\n--- PROBLEMA ---")
    parts.append(f"Problema: {initiative.get('problem', 'No especificado')}")

    parts.append("\n--- SOLUCION ---")
    parts.append(f"Descripcion: {initiative.get('solution', 'No especificado')}")
    parts.append(f"Impacto economico: {initiative.get('economic_impact', 'No especificado')}")
    parts.append(f"TRL: {initiative.get('trl', 'No declarado')}")
    parts.append(f"Escalabilidad: {initiative.get('scalability', 'No especificado')}")

    parts.append("\n--- CLIENTE ---")
    parts.append(f"Cliente interno: {initiative.get('internal_client', 'No especificado')}")
    parts.append(f"Cliente externo: {initiative.get('external_client', 'No especificado')}")
    parts.append(f"CRL: {initiative.get('crl', 'No declarado')}")

    parts.append("\n--- ALINEAMIENTO ---")
    parts.append(f"Foco estrategico: {initiative.get('strategic_alignment', 'por asignar')}")

    parts.append("\n--- EQUIPO ---")
    parts.append(f"Equipo interno: {initiative.get('internal_team', 'No especificado')}")
    parts.append(f"Equipo externo: {initiative.get('external_team', 'No especificado')}")
    parts.append(f"Sponsor: {initiative.get('sponsor', 'No especificado')}")
    parts.append(f"Duracion estimada: {initiative.get('estimated_duration', 'No estimado')}")

    parts.append("\n--- RIESGO ---")
    parts.append(f"Duda principal: {initiative.get('main_doubt', 'No especificado')}")
    parts.append(f"Condicion clave: {initiative.get('key_condition', 'No especificado')}")
    parts.append(f"Captura de valor: {initiative.get('value_capture', 'No especificado')}")
    parts.append(f"BRL: {initiative.get('brl', 'No declarado')}")

    parts.append("\n--- HITOS ---")
    parts.append(f"Tecnicos/operativos: {initiative.get('technical_milestones', 'No definido')}")
    parts.append(f"Economicos/financieros: {initiative.get('financial_milestones', 'No definido')}")
    parts.append(f"Horizonte de retorno: {initiative.get('return_horizon', 'No especificado')} meses")

    # Include dbi_extra fields if present
    extra = initiative.get("dbi_extra") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}

    if extra.get("executive_summary"):
        parts.insert(4, f"\nResumen ejecutivo: {extra['executive_summary']}")

    a_extra = extra.get("block_a_extra", {})
    if a_extra:
        # Find insertion point: after PROBLEMA block, before SOLUCION block
        insert_pos = len(parts)
        for idx, p in enumerate(parts):
            if "SOLUCION" in p and p.strip().startswith("---"):
                insert_pos = idx
                break
        for k in ("why_it_matters", "who_has_it", "current_solution"):
            if a_extra.get(k):
                key_labels = {
                    "why_it_matters": "Por que importa",
                    "who_has_it": "Quien lo tiene",
                    "current_solution": "Como se resuelve hoy",
                }
                parts.insert(
                    insert_pos,
                    f"{key_labels.get(k, k)}: {a_extra[k]}",
                )
                insert_pos += 1

    b_extra = extra.get("block_b_extra", {})
    if b_extra:
        if b_extra.get("differentiator_novelty_grade"):
            parts.append(f"Grado de novedad: {b_extra['differentiator_novelty_grade']}")
        if b_extra.get("competition_grade"):
            parts.append(f"Competencia: {b_extra['competition_grade']}")
        if b_extra.get("trl_evidence"):
            parts.append(f"Evidencia TRL: {b_extra['trl_evidence']}")
        if b_extra.get("market_repeatability"):
            parts.append(f"Mercado/repetibilidad: {b_extra['market_repeatability']}")

    c_extra = extra.get("block_c_extra", {})
    if c_extra:
        if c_extra.get("crl_evidence"):
            parts.append(f"Evidencia CRL: {c_extra['crl_evidence']}")
        if c_extra.get("target_client_type"):
            parts.append(f"Tipo de cliente objetivo: {c_extra['target_client_type']}")

    d_extra = extra.get("block_d_extra", {})
    if d_extra:
        if d_extra.get("horizon"):
            parts.append(f"Horizonte (H1/H2/H3): {d_extra['horizon']}")

    e_extra = extra.get("block_e_extra", {})
    if e_extra:
        if e_extra.get("applicant_area"):
            parts.append(f"Area del postulante: {e_extra['applicant_area']}")
        if e_extra.get("support_received"):
            parts.append(f"Apoyo recibido: {e_extra['support_received']}")
        if e_extra.get("other_resources"):
            parts.append(f"Otros recursos: {e_extra['other_resources']}")

    f_extra = extra.get("block_f_extra", {})
    if f_extra:
        if f_extra.get("brl_evidence"):
            parts.append(f"Evidencia BRL: {f_extra['brl_evidence']}")
        unc = f_extra.get("uncertainty", {})
        if unc:
            parts.append(f"Incertidumbre: cliente={unc.get('client','?')} / solucion={unc.get('solution','?')} / modelo={unc.get('model','?')}")

    return "\n".join(parts)


async def _load_evaluator_prompt() -> str:
    """Load evaluator prompt from agent_configs database table."""
    from app.core.database import get_pool

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT prompt_text FROM agent_configs "
            "WHERE agent_name = 'evaluador' AND is_active = true "
            "ORDER BY created_at DESC LIMIT 1"
        )

    _db_prompt = row["prompt_text"] if row else ""
    # The DB prompt is a placeholder — use the comprehensive system prompt
    return EVALUATOR_SYSTEM_PROMPT


# ── Main evaluation function ───────────────────────────────────────────────

class EvaluatorError(RuntimeError):
    """Evaluation failed (OpenAI error, parse error, etc.)."""


async def evaluate_initiative(initiative: dict) -> dict:
    """Run the evaluator on an initiative and return the scorecard results.

    Args:
        initiative: Full initiative row (as dict from DB).

    Returns:
        The parsed scorecard JSON (scores + derived).

    Raises:
        EvaluatorError: If OpenAI call fails or response can't be parsed.
    """
    if not settings.openai_api_key:
        raise EvaluatorError("OPENAI_API_KEY no configurada")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    context = _build_initiative_context(initiative)
    system_prompt = await _load_evaluator_prompt()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            "Evalua la siguiente iniciativa de innovacion segun el scorecard. "
            "Responde UNICAMENTE con el JSON, sin markdown ni texto adicional.\n\n"
            f"{context}"
        )},
    ]

    logger.info("evaluator.start initiative_id=%s title=%s",
                initiative.get("id"), initiative.get("title"))

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            temperature=_TEMPERATURE,
            stream=False,
        )

        raw = response.choices[0].message.content.strip() if response.choices else ""

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        results = json.loads(raw)

        # Basic validation
        assert "scores" in results, "Missing 'scores' key"
        assert "derived" in results, "Missing 'derived' key"

        dims = ["problema", "solucion", "cliente", "alineamiento", "equipo", "riesgo", "hitos"]
        for dim in dims:
            assert dim in results["scores"], f"Missing dimension '{dim}'"

        logger.info(
            "evaluator.completed initiative_id=%s total=%s sandbox=%s",
            initiative.get("id"),
            results["derived"].get("puntaje_total", "?"),
            results["derived"].get("compuerta_sandbox", "?"),
        )

        return results

    except json.JSONDecodeError as e:
        logger.error("evaluator.parse_error initiative_id=%s raw=%s",
                     initiative.get("id"), raw[:200] if raw else "empty")
        raise EvaluatorError(f"No se pudo parsear la respuesta del Evaluador: {e}") from e
    except AssertionError as e:
        raise EvaluatorError(f"Respuesta del Evaluador incompleta: {e}") from e
    except Exception as e:
        logger.error("evaluator.error initiative_id=%s error=%s",
                     initiative.get("id"), e)
        raise EvaluatorError(f"Error al evaluar iniciativa: {e}") from e


# ── Persist evaluation results ─────────────────────────────────────────────

async def create_evaluation(
    initiative_id: int,
    activated_by: str,
) -> dict:
    """Create an evaluation record, run the evaluator, store results.

    Args:
        initiative_id: The initiative to evaluate.
        activated_by: UUID of the directora/admin activating the evaluation.

    Returns:
        The created evaluation row as dict.

    Raises:
        EvaluatorError: If evaluation fails.
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        # ── Verify initiative exists and is in valid state ─────────────
        initiative = await conn.fetchrow(
            f"SELECT * FROM initiatives WHERE id = {initiative_id}"
        )
        if not initiative:
            raise ValueError(f"Iniciativa {initiative_id} no encontrada")

        status = initiative["status"]
        if status not in ("notificado", "en_evaluacion"):
            raise ValueError(
                f"Iniciativa en estado '{status}' — debe estar en 'notificado' o 'en_evaluacion'"
            )

        # ── Check for existing evaluation (1:1 constraint) ────────────
        existing = await conn.fetchrow(
            f"SELECT id, status FROM evaluations WHERE initiative_id = {initiative_id}"
        )
        if existing:
            if existing["status"] == "completed":
                raise ValueError(
                    f"La iniciativa {initiative_id} ya tiene una evaluacion completada (id={existing['id']})"
                )
            # Re-use existing in_progress evaluation
            eval_id = existing["id"]
            logger.info("evaluator.reusing_evaluation id=%s", eval_id)
        else:
            # ── Move initiative to en_evaluacion ──────────────────────
            await conn.execute(
                f"UPDATE initiatives SET status = 'en_evaluacion', updated_at = now() "
                f"WHERE id = {initiative_id}"
            )

            # ── Create evaluation record ─────────────────────────────
            eval_row = await conn.fetchrow(
                f"INSERT INTO evaluations (initiative_id, activated_by, status) "
                f"VALUES ({initiative_id}, '{activated_by}', 'in_progress') "
                f"RETURNING *"
            )
            eval_id = eval_row["id"]
            logger.info("evaluator.created evaluation_id=%s initiative_id=%s",
                       eval_id, initiative_id)

        # ── Run evaluator ─────────────────────────────────────────────
        initiative_dict = dict(initiative)
        # Parse dbi_extra if string
        if isinstance(initiative_dict.get("dbi_extra"), str):
            try:
                initiative_dict["dbi_extra"] = json.loads(initiative_dict["dbi_extra"])
            except json.JSONDecodeError:
                initiative_dict["dbi_extra"] = {}

        results = await evaluate_initiative(initiative_dict)

        results_json = json.dumps(results, ensure_ascii=False)
        escaped_results = results_json.replace("'", "''")

        # ── Store results, mark evaluation completed ──────────────────
        await conn.execute(
            f"UPDATE evaluations SET "
            f"status = 'completed', "
            f"results = '{escaped_results}'::jsonb, "
            f"updated_at = now() "
            f"WHERE id = {eval_id}"
        )

        # ── Move initiative to evaluado ───────────────────────────────
        await conn.execute(
            f"UPDATE initiatives SET status = 'evaluado', updated_at = now() "
            f"WHERE id = {initiative_id}"
        )

        # ── Read back complete evaluation ────────────────────────────
        full_eval = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {eval_id}"
        )

    logger.info(
        "evaluator.persisted evaluation_id=%s initiative_id=%s",
        eval_id, initiative_id,
    )

    return dict(full_eval)


async def update_evaluation_results(
    evaluation_id: int,
    results: dict,
    reviewed_by: str,
) -> dict:
    """Update evaluation results (directora adjusts scores), mark as reviewed.

    Args:
        evaluation_id: The evaluation to update.
        results: Updated results JSON to store.
        reviewed_by: UUID of the directora reviewing.

    Returns:
        Updated evaluation row.
    """
    pool = get_pool()

    results_json = json.dumps(results, ensure_ascii=False)
    escaped_results = results_json.replace("'", "''")

    async with pool.acquire() as conn:
        eval_row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {evaluation_id}"
        )
        if not eval_row:
            raise ValueError(f"Evaluacion {evaluation_id} no encontrada")

        initiative_id = eval_row["initiative_id"]

        await conn.execute(
            f"UPDATE evaluations SET "
            f"results = '{escaped_results}'::jsonb, "
            f"reviewed_by = '{reviewed_by}', "
            f"reviewed_at = now(), "
            f"updated_at = now() "
            f"WHERE id = {evaluation_id}"
        )

        # Transition initiative to validado
        await conn.execute(
            f"UPDATE initiatives SET status = 'validado', updated_at = now() "
            f"WHERE id = {initiative_id}"
        )

        full_eval = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {evaluation_id}"
        )

    logger.info(
        "evaluator.validated evaluation_id=%s initiative_id=%s reviewed_by=%s",
        evaluation_id, initiative_id, reviewed_by,
    )

    return dict(full_eval)
