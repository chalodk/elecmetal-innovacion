from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_pool
from app.core.security import get_current_user

router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado desde la tabla profiles."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, full_name, role, avatar_url,
                   created_at, updated_at
            FROM profiles
            WHERE id = $1::uuid
            """,
            user["sub"],
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PROFILE_NOT_FOUND",
                    "message": "No se encontró el perfil del usuario",
                }
            },
        )

    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "role": row["role"],
        "avatar_url": row["avatar_url"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
