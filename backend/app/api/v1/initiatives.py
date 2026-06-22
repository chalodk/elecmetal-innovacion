"""Router de iniciativas — listado y detalle con RBAC.

La directora/admin ve todas las iniciativas. El postulante solo las suyas.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_pool
from app.core.security import get_current_user

router = APIRouter()

# ─── Helpers ────────────────────────────────────────────────────────────────


def _initiative_row_to_dict(row) -> dict:
    """Convierte una fila de asyncpg a dict con timestamps ISO."""
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "user_id": row["user_id"],
        "status": row["status"],
        "initiative_code": row["initiative_code"],
        "title": row["title"],
        "initiative_type": row["initiative_type"],
        "postulation_date": str(row["postulation_date"]) if row["postulation_date"] else None,
        "area": row["area"],
        "applicant_name": row["applicant_name"],
        "problem": row["problem"],
        "solution": row["solution"],
        "economic_impact": row["economic_impact"],
        "trl": row["trl"],
        "scalability": row["scalability"],
        "internal_client": row["internal_client"],
        "external_client": row["external_client"],
        "crl": row["crl"],
        "sponsor": row["sponsor"],
        "internal_team": row["internal_team"],
        "external_team": row["external_team"],
        "estimated_duration": row["estimated_duration"],
        "main_doubt": row["main_doubt"],
        "key_condition": row["key_condition"],
        "value_capture": row["value_capture"],
        "brl": row["brl"],
        "technical_milestones": row["technical_milestones"],
        "financial_milestones": row["financial_milestones"],
        "return_horizon": row["return_horizon"],
        "strategic_alignment": row["strategic_alignment"],
        "dbi_raw_text": row["dbi_raw_text"],
        "dbi_extra": row.get("dbi_extra"),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


# ─── List ───────────────────────────────────────────────────────────────────

LIST_COLUMNS = """
    id, session_id, user_id::text, status, initiative_code, title,
    initiative_type, postulation_date, area, applicant_name,
    created_at, updated_at
"""


@router.get("/initiatives")
async def list_initiatives(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filtrar por estado de la iniciativa",
    ),
    cursor: int | None = Query(
        default=None,
        gt=0,
        description="ID de la ultima iniciativa de la pagina anterior",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximo de iniciativas por pagina",
    ),
    user: dict = Depends(get_current_user),
):
    """Lista iniciativas con paginacion cursor-based.

    Directora/admin ve todas. Postulante solo las suyas.
    Filtro opcional por status.
    """
    pool = get_pool()

    # Determinar visibilidad segun rol
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            "SELECT role FROM profiles WHERE id = $1",
            user["sub"],
        )
        user_role = profile["role"] if profile else "postulante"

    is_admin = user_role in ("directora", "admin")

    # Construir query
    conditions = []
    params: list = []
    param_idx = 0

    if not is_admin:
        param_idx += 1
        conditions.append(f"user_id = ${param_idx}")
        params.append(user["sub"])

    if status_filter:
        param_idx += 1
        conditions.append(f"status = ${param_idx}")
        params.append(status_filter)

    if cursor is not None:
        param_idx += 1
        conditions.append(f"id < ${param_idx}")
        params.append(cursor)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    param_idx += 1
    limit_param = f"${param_idx}"
    params.append(limit + 1)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT {LIST_COLUMNS}
            FROM initiatives
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param}
            """,
            *params,
        )

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "status": row["status"],
            "initiative_code": row["initiative_code"],
            "title": row["title"],
            "initiative_type": row["initiative_type"],
            "postulation_date": str(row["postulation_date"]) if row["postulation_date"] else None,
            "area": row["area"],
            "applicant_name": row["applicant_name"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })

    return {
        "data": data,
        "pagination": {
            "next_cursor": data[-1]["id"] if data else None,
            "has_more": has_more,
        },
    }


# ─── Detail ─────────────────────────────────────────────────────────────────

DETAIL_COLUMNS = """
    i.id, i.session_id, i.user_id::text, i.status, i.initiative_code, i.title,
    i.initiative_type, i.postulation_date, i.area, i.applicant_name,
    i.problem, i.solution, i.economic_impact, i.trl, i.scalability,
    i.internal_client, i.external_client, i.crl,
    i.sponsor, i.internal_team, i.external_team, i.estimated_duration,
    i.main_doubt, i.key_condition, i.value_capture, i.brl,
    i.technical_milestones, i.financial_milestones, i.return_horizon,
    i.strategic_alignment, i.dbi_raw_text, i.dbi_extra,
    i.created_at, i.updated_at,
    e.id AS eval_id, e.status AS eval_status, e.results AS eval_results,
    e.veredicto AS eval_veredicto, e.reviewed_at AS eval_reviewed_at
"""


@router.get("/initiatives/{initiative_id}")
async def get_initiative(
    initiative_id: int,
    user: dict = Depends(get_current_user),
):
    """Detalle completo de una iniciativa con su evaluacion (si existe).

    Directora/admin ve cualquier iniciativa. Postulante solo las suyas.
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        # Obtener rol del usuario
        profile = await conn.fetchrow(
            "SELECT role FROM profiles WHERE id = $1",
            user["sub"],
        )
        user_role = profile["role"] if profile else "postulante"
        is_admin = user_role in ("directora", "admin")

        row = await conn.fetchrow(
            f"""
            SELECT {DETAIL_COLUMNS}
            FROM initiatives i
            LEFT JOIN evaluations e ON e.initiative_id = i.id
            WHERE i.id = $1
            """,
            initiative_id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "INITIATIVE_NOT_FOUND",
                    "message": "La iniciativa no existe",
                }
            },
        )

    if not is_admin and row["user_id"] != user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes acceso a esta iniciativa",
                }
            },
        )

    initiative = _initiative_row_to_dict(row)

    # Adjuntar evaluacion si existe
    if row["eval_id"] is not None:
        initiative["evaluation"] = {
            "id": row["eval_id"],
            "status": row["eval_status"],
            "results": row["eval_results"],
            "veredicto": row["eval_veredicto"],
            "reviewed_at": row["eval_reviewed_at"].isoformat()
            if row["eval_reviewed_at"]
            else None,
        }

    return initiative
