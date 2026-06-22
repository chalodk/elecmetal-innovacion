"""User profile endpoint — GET /api/v1/me."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_user_id
from app.core.database import get_pool
from app.core.errors import AppError, ErrorCode

router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado."""
    user_id = require_user_id(user)

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT id, full_name, role, avatar_url, created_at "
            f"FROM profiles WHERE id = '{user_id}'"
        )

    if not row:
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="Perfil no encontrado",
        )

    # created_at viene como string ISO del bridge HTTP (Management API)
    ca = row["created_at"]
    if ca is not None and not isinstance(ca, str):
        ca = ca.isoformat()

    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "role": row["role"],
        "avatar_url": row["avatar_url"],
        "created_at": ca,
    }
