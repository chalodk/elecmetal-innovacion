"""Notifications API (Step 8 of the boot sequence).

Endpoints para listar notificaciones y disparar el procesamiento.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_pool
from app.core.pagination import (
    validate_cursor,
    validate_limit,
    paginated_response,
)
from app.core.security import get_current_user
from app.services.notification_service import process_pending

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


class ProcessSummary(BaseModel):
    found: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0


# ── GET / — list notifications for the authenticated user ───────────────────

@router.get("")
async def list_notifications(
    user: dict = Depends(get_current_user),
    cursor: str | None = Query(None, description="Cursor for pagination (notification id)"),
    limit: str | None = Query(None, description=f"Page size (max {100})"),
):
    """Lista las notificaciones del usuario autenticado, con paginacion."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificador de usuario")
    if not _is_valid_uuid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token con identificador de usuario invalido")

    cursor_val = validate_cursor(cursor)
    page_limit = validate_limit(limit)

    conditions = [f"n.recipient_user_id = '{user_id}'"]
    if cursor_val is not None:
        conditions.append(f"n.id < {cursor_val}")

    where_clause = "WHERE " + " AND ".join(conditions)

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT n.id, n.initiative_id, n.notification_type, n.status, "
            f"n.sent_at, n.created_at, "
            f"i.initiative_code, i.title AS initiative_title "
            f"FROM notifications n "
            f"LEFT JOIN initiatives i ON n.initiative_id = i.id "
            f"{where_clause} "
            f"ORDER BY n.created_at DESC "
            f"LIMIT {page_limit + 1}"
        )

    result = []
    for r in rows:
        item = dict(r)
        for col in ("sent_at", "created_at"):
            val = item.get(col)
            if val is not None and not isinstance(val, str):
                item[col] = val.isoformat()
        result.append(item)

    return paginated_response(result, cursor_field="id", limit=page_limit)


# ── POST /process — trigger pending notification processing ─────────────────

@router.post("/process", response_model=ProcessSummary)
async def trigger_process(user: dict = Depends(get_current_user)):
    """Dispara el procesamiento de notificaciones pendientes (admin/directora).

    Envia emails via Resend para todas las notificaciones con status='pending'.
    Solo accesible para usuarios con rol directora o admin.
    """
    user_id = user.get("sub")
    if not user_id or not _is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    # Verify role
    pool = get_pool()
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            f"SELECT role FROM profiles WHERE id = '{user_id}'"
        )
        if not profile or profile["role"] not in ("directora", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo directora o admin pueden procesar notificaciones",
            )

    summary = await process_pending()
    logger.info(
        "notifications.process_triggered",
        by=user_id,
        **summary,
    )
    return summary
