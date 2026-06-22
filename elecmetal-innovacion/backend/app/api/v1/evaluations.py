"""Evaluations API — ciclo de vida de evaluacion de iniciativas."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.database import get_pool
from app.core.errors import AppError, ErrorCode
from app.core.security import (
    get_current_user,
    require_user_id,
    require_bigint_id,
    require_directora,
)
from app.services.evaluator import (
    create_evaluation,
    EvaluatorError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _eval_to_response(row: dict) -> dict:
    """Format an evaluation row for API response."""
    result = dict(row)
    for col in ("created_at", "updated_at", "reviewed_at"):
        val = result.get(col)
        if val is not None and not isinstance(val, str):
            result[col] = val.isoformat()
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
    user_id = await require_directora(user)
    iid = require_bigint_id(initiative_id, "initiative_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        init = await conn.fetchrow(
            f"SELECT id, status FROM initiatives WHERE id = {iid}"
        )
        if not init:
            raise AppError(
                code=ErrorCode.NOT_FOUND,
                message="Iniciativa no encontrada",
            )

        if init["status"] != "notificado":
            raise AppError(
                code=ErrorCode.STATE_CONFLICT,
                message=(
                    f"La iniciativa esta en estado '{init['status']}' — "
                    f"debe estar en 'notificado' para pasar a evaluacion"
                ),
                details={"current_status": init["status"], "required_status": "notificado"},
            )

        await conn.execute(
            f"UPDATE initiatives SET status = 'en_evaluacion', updated_at = now() "
            f"WHERE id = {iid}"
        )

        updated = await conn.fetchrow(
            f"SELECT id, status, updated_at FROM initiatives WHERE id = {iid}"
        )

    logger.info(
        "initiative.status_changed initiative_id=%s old=%s new=%s by=%s",
        iid, init["status"], updated["status"], user_id,
    )

    return dict(updated)


# ── POST /initiatives/{id}/evaluation ───────────────────────────────────────

@router.post("/initiatives/{initiative_id}/evaluation", status_code=status.HTTP_201_CREATED)
async def trigger_evaluation(
    initiative_id: str,
    user: dict = Depends(get_current_user),
):
    """Activa al Evaluador IA para una iniciativa. Solo directora/admin."""
    user_id = await require_directora(user)
    iid = require_bigint_id(initiative_id, "initiative_id")

    try:
        evaluation = await create_evaluation(
            initiative_id=iid,
            activated_by=user_id,
        )
    except ValueError as e:
        raise AppError(
            code=ErrorCode.STATE_CONFLICT,
            message=str(e),
        )
    except EvaluatorError as e:
        raise AppError(
            code=ErrorCode.EVALUATOR_ERROR,
            message=f"El Evaluador fallo: {e}",
        )

    return _eval_to_response(evaluation)


# ── GET /initiatives/{id}/evaluation ─ lookup by initiative ────────────

@router.get("/initiatives/{initiative_id}/evaluation")
async def get_evaluation_by_initiative(
    initiative_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene la evaluacion asociada a una iniciativa (si existe)."""
    require_user_id(user)
    iid = require_bigint_id(initiative_id, "initiative_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE initiative_id = {iid}"
        )

    if not row:
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="Evaluacion no encontrada para esta iniciativa",
        )

    return _eval_to_response(row)


# ── GET /evaluations/{id} ───────────────────────────────────────────────────

@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene los detalles de una evaluacion, incluyendo resultados."""
    require_user_id(user)
    eid = require_bigint_id(evaluation_id, "evaluation_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {eid}"
        )

    if not row:
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="Evaluacion no encontrada",
        )

    return _eval_to_response(row)


# ── PATCH /evaluations/{id} ─────────────────────────────────────────────────

@router.patch("/evaluations/{evaluation_id}")
async def review_evaluation(
    evaluation_id: str,
    body: ReviewEvaluationRequest,
    user: dict = Depends(get_current_user),
):
    """Revisa, ajusta resultados y valida una evaluacion. Solo directora/admin."""
    user_id = await require_directora(user)
    eid = require_bigint_id(evaluation_id, "evaluation_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        eval_row = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {eid}"
        )
        if not eval_row:
            raise AppError(
                code=ErrorCode.NOT_FOUND,
                message="Evaluacion no encontrada",
            )

        if eval_row["status"] != "completed":
            raise AppError(
                code=ErrorCode.STATE_CONFLICT,
                message=(
                    f"La evaluacion esta en estado '{eval_row['status']}' — "
                    f"debe estar 'completed' para revisar"
                ),
                details={"current_status": eval_row["status"], "required_status": "completed"},
            )

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
                f"WHERE id = {eid}"
            )

        if body.validate:
            init_id = eval_row["initiative_id"]
            await conn.execute(
                f"UPDATE initiatives SET status = 'validado', updated_at = now() "
                f"WHERE id = {init_id}"
            )
            logger.info(
                "evaluation.validated evaluation_id=%s initiative_id=%s by=%s",
                eid, init_id, user_id,
            )

        updated = await conn.fetchrow(
            f"SELECT * FROM evaluations WHERE id = {eid}"
        )

    return _eval_to_response(updated)
