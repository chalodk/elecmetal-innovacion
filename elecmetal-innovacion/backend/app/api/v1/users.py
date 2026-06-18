from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_pool
from app.core.security import get_current_user

router = APIRouter()

# La Management API de Supabase no soporta placeholders parametrizados ($1, $2).
# Toda interpolacion de valores en queries debe validarse contra el tipo esperado
# (UUID en el caso de user_id, que viene de un JWT verificado).

_UUID_RE = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _is_valid_uuid(value: str) -> bool:
    import re

    return bool(re.fullmatch(_UUID_RE, value))


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario",
        )

    if not _is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token con identificador de usuario invalido",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT id, full_name, role, avatar_url, created_at "
            f"FROM profiles WHERE id = '{user_id}'"
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado",
        )

    # created_at viene como string ISO del bridge HTTP (Management API);
    # .isoformat() sobre un string crashearia.
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
