"""Evaluations API (Step 9 of the boot sequence).

Endpoints for the evaluation lifecycle:
  - PATCH /initiatives/{id}/status    → move to en_evaluacion (directora)
  - POST  /initiatives/{id}/evaluation → activate evaluator (directora)
  - GET   /evaluations/{id}            → get evaluation details
  - PATCH /evaluations/{id}            → review, adjust, validate (directora)
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import get_pool
from app.core.security import get_current_user
from app.services.evaluator import (
    create_evaluation,
    update_evaluation_results,
    evaluate_initiative,
    EvaluatorError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_BIGINT_RE = re.compile(r"^[0-9]{1,19}$")
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _is_valid_bigint(value: str) -> bool:
    return bool(_BIGINT_RE.match(value))


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.fullmatch(value))


async def _require_directora(user: dict) -> str:
    """Verify the user has directora/admin role. Returns user_id."""
    user_id = user.get("sub")
    if not user_id or not _is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            f"SELECT role FROM profiles WHERE id = '{user_id}'"
        )
        if not profile or profile["role"] not in ("directora", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo directora o admin pueden realizar esta accion",
            )
    return user_id


def _eval_to_response(row: dict) -> dict:
    """Format an evaluation row for API response."""
    result = dict(row)
    for col in ("created_at", "updated_at", "reviewed_at"):
        val = result.get(col)
        if val is not None and not isinstance(val, str):
            result[col] = val.isoformat()
    # Parse results JSONB if string
    if isinstance(result.get("results"), str):
        try:
            result["results"] = json.loads(result["results"])
        except json.JSONDecodeError:
            pass
    return result


# ── Request models ──────────────────────────────────────────────────────────

class UpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(en_evaluacion)$")


class ReviewEvaluationRequest(BaseModel):
    results: dict | None = None
    veredicto: str | None = Field(
        None, pattern=r"^(aprobada|rechazada|pendiente)$"
    )
    validate: bool = False


# ── PATCH /initiatives/{id}/status ──────────────────────────────────────────

@router.patch("/initiatives/{initiative_id}/status")
async def update_initiative_status(
    initiative_id: str,
    body: UpdateStatusRequest,
    user: dict = Depends(get_current_user),
):
    """Mueve una iniciativa a 'en_evaluacion'. Solo directora/admin."""
    user_id = await _require_directora(user)

    if not _is_valid_bigint(initiative_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de iniciativa invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        init = await conn.fetchrow(
            f"SELECT id, status FROM initiatives WHERE id = {initiative_id}"
        )
        if not init:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Iniciativa no encontrada",
            )

        if init["status"] != "notificado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La iniciativa esta en estado '{init['status']}' — "
                       f"debe estar en 'notificado' para pasar a evaluacion",
            )

        await conn.execute(
            f"UPDATE initiatives SET status = 'en_evaluacion', updated_at = now() "
            f"WHERE id = {initiative_id}"
        )

        updated = await conn.fetchrow(
            f"SELECT id, status, updated_at FROM initiatives WHERE id = {initiative_id}"
        )

    logger.info(
        "initiative.status_changed initiative_id=%s old=%s new=%s by=%s",
        initiative_id, init["status"], updated["status"], user_id,
    )

    return dict(updated)


# ── POST /initiatives/{id}/evaluation ───────────────────────────────────────

@router.post("/initiatives/{initiative_id}/evaluation", status_code=status.HTTP_201_CREATED)
async def trigger_evaluation(
    initiative_id: str,
    user: dict = Depends(get_current_user),
):
    """Activa al Evaluador IA para una iniciativa. Solo directora/admin.

    El Evaluador recibe el DBI completo (campos estructurados + dbi_extra),
    genera el scorecard (22 items + derivados), y los resultados se guardan
    en evaluations.results como JSONB.

    La iniciativa pasa a 'evaluado' al completar exitosamente.
    """
    user_id = await _require_directora(user)

    if not _is_valid_bigint(initiative_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de iniciativa invalido",
        )

    try:
        evaluation = await create_evaluation(
            initiative_id=int(initiative_id),
            activated_by=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except EvaluatorError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"El Evaluador fallo: {e}",
        )

    return _eval_to_response(evaluation)


# ── GET /initiatives/{id}/evaluation ─ lookup by initiative ────────────

@router.get("/initiatives/{initiative_id}/evaluation")
async def get_evaluation_by_initiative(
    initiative_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene la evaluacion asociada a una iniciativa (si existe)."""
    user_id = user.get("sub")
    if not user_id or not _is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    if not _is_valid_bigint(initiative_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de iniciativa invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE initiative_id = {initiative_id}"
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluacion no encontrada para esta iniciativa",
        )

    return _eval_to_response(row)


# ── GET /evaluations/{id} ───────────────────────────────────────────────────

@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene los detalles de una evaluacion, incluyendo resultados."""
    user_id = user.get("sub")
    if not user_id or not _is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    if not _is_valid_bigint(evaluation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evaluacion invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {evaluation_id}"
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluacion no encontrada",
        )

    return _eval_to_response(row)


# ── PATCH /evaluations/{id} ─────────────────────────────────────────────────

@router.patch("/evaluations/{evaluation_id}")
async def review_evaluation(
    evaluation_id: str,
    body: ReviewEvaluationRequest,
    user: dict = Depends(get_current_user),
):
    """Revisa, ajusta resultados y valida una evaluacion. Solo directora/admin.

    - Si se envian `results`, se actualiza el scorecard con los ajustes.
    - Si se envia `veredicto`, se registra la decision del comite.
    - Si `validate=true`, se transiciona la iniciativa a 'validado'.
    """
    user_id = await _require_directora(user)

    if not _is_valid_bigint(evaluation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evaluacion invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        eval_row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {evaluation_id}"
        )
        if not eval_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluacion no encontrada",
            )

        if eval_row["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La evaluacion esta en estado '{eval_row['status']}' — "
                       f"debe estar 'completed' para revisar",
            )

        # Build updates
        updates: list[str] = []
        if body.results is not None:
            results_json = json.dumps(body.results, ensure_ascii=False)
            escaped = results_json.replace("'", "''")
            updates.append(f"results = '{escaped}'::jsonb")

        if body.veredicto is not None:
            updates.append(f"veredicto = '{body.veredicto}'")

        if body.validate:
            updates.append(f"reviewed_by = '{user_id}'")
            updates.append("reviewed_at = now()")

        if updates:
            updates.append("updated_at = now()")
            await conn.execute(
                f"UPDATE evaluations SET {', '.join(updates)} "
                f"WHERE id = {evaluation_id}"
            )

        # If validating, transition initiative
        if body.validate:
            init_id = eval_row["initiative_id"]
            await conn.execute(
                f"UPDATE initiatives SET status = 'validado', updated_at = now() "
                f"WHERE id = {init_id}"
            )
            logger.info(
                "evaluation.validated evaluation_id=%s initiative_id=%s by=%s",
                evaluation_id, init_id, user_id,
            )

        updated = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {evaluation_id}"
        )

    return _eval_to_response(updated)
