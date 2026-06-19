"""Initiatives API — listar y obtener iniciativas (paso 7 del boot sequence).

Paso 12: cursor-based pagination, filters, and sorting.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_pool
from app.core.pagination import (
    validate_cursor,
    validate_limit,
    paginated_response,
    build_sort_clause,
    DEFAULT_LIMIT,
)
from app.core.security import get_current_user

router = APIRouter()

import re

_UUID_RE = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_BIGINT_RE = re.compile(r"^[0-9]{1,19}$")


def _is_valid_uuid(value: str) -> bool:
    return bool(re.fullmatch(_UUID_RE, value))


def _is_valid_bigint(value: str) -> bool:
    return bool(_BIGINT_RE.match(value))


_INITIATIVE_SORT_COLUMNS = {
    "id", "created_at", "updated_at", "postulation_date",
    "status", "title", "initiative_type", "area", "applicant_name",
    "trl", "crl", "brl",
}


def _initiative_from_row(row: dict) -> dict:
    result = dict(row)
    for col in ("created_at", "updated_at", "postulation_date"):
        val = result.get(col)
        if val is not None and not isinstance(val, str):
            result[col] = val.isoformat()
    return result


@router.get("")
async def list_initiatives(
    user: dict = Depends(get_current_user),
    cursor: str | None = Query(None, description="Cursor for pagination (initiative id)"),
    limit: str | None = Query(None, description=f"Page size (max {100})"),
    sort_by: str | None = Query(None, description="Sort column"),
    sort_dir: str | None = Query(None, description="Sort direction (ASC/DESC)"),
    status_filter: str | None = Query(None, description="Filter by initiative status"),
    type_filter: str | None = Query(None, description="Filter by initiative_type (interna/externa/mixta)"),
):
    """Lista las iniciativas con paginacion, filtros y ordenamiento.

    **Directora/admin** ven todas; **postulante** solo las suyas.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificador de usuario")
    if not _is_valid_uuid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token con identificador de usuario invalido")

    cursor_val = validate_cursor(cursor)
    page_limit = validate_limit(limit)

    sort_clause = build_sort_clause(
        sort_by, sort_dir,
        allowed_columns=_INITIATIVE_SORT_COLUMNS,
        default_sort="created_at",
        default_dir="DESC",
    )

    # Build WHERE clauses
    conditions: list[str] = []

    pool = get_pool()
    async with pool.acquire() as conn:
        # Check role
        profile = await conn.fetchrow(f"SELECT role FROM profiles WHERE id = '{user_id}'")
        is_admin = profile and profile["role"] in ("directora", "admin")

        if not is_admin:
            conditions.append(f"user_id = '{user_id}'")

        if status_filter:
            valid_statuses = {
                "dbi_generado", "persistido", "notificado",
                "en_evaluacion", "evaluado", "validado", "veredicto",
            }
            if status_filter in valid_statuses:
                conditions.append(f"status = '{status_filter}'")

        if type_filter and type_filter in ("interna", "externa", "mixta"):
            conditions.append(f"initiative_type = '{type_filter}'")

        if cursor_val is not None:
            conditions.append(f"id < {cursor_val}")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        rows = await conn.fetch(
            f"SELECT id, session_id, user_id, status, initiative_code, "
            f"title, initiative_type, postulation_date, area, applicant_name, "
            f"trl, crl, brl, scalability, return_horizon, "
            f"strategic_alignment, created_at, updated_at "
            f"FROM initiatives "
            f"{where_clause} "
            f"{sort_clause} "
            f"LIMIT {page_limit + 1}"
        )

    return paginated_response(
        [_initiative_from_row(r) for r in rows],
        cursor_field="id",
        limit=page_limit,
    )


@router.get("/{initiative_id}")
async def get_initiative(
    initiative_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene una iniciativa completa por ID, incluyendo DBI completo."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identificador de usuario")
    if not _is_valid_uuid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token con identificador de usuario invalido")
    if not _is_valid_bigint(initiative_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de iniciativa invalido")

    pool = get_pool()
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(f"SELECT role FROM profiles WHERE id = '{user_id}'")
        is_admin = profile and profile["role"] in ("directora", "admin")

        if is_admin:
            row = await conn.fetchrow(f"SELECT * FROM initiatives WHERE id = {initiative_id}")
        else:
            row = await conn.fetchrow(f"SELECT * FROM initiatives WHERE id = {initiative_id} AND user_id = '{user_id}'")

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Iniciativa no encontrada")

    return _initiative_from_row(row)
