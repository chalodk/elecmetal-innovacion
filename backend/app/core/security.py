from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    """Obtiene y cachea el JWKS de Supabase. Se reinicia al cambiar la config."""
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise RuntimeError(f"No se pudo obtener JWKS desde {url}: {exc}") from exc


def decode_supabase_jwt(token: str) -> dict:
    """Valida un JWT emitido por Supabase usando JWKS (ES256)."""
    try:
        unverified_header = jwt.get_unverified_header(token)
        jwks = _fetch_jwks()

        # Buscar la key que coincide con el kid del token
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]),
            None,
        )
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave de firma no encontrada",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Dependencia FastAPI: extrae y valida el usuario del token Bearer."""
    return decode_supabase_jwt(credentials.credentials)


async def require_role(*roles: str):
    """Fabrica de dependencia: valida que el usuario tenga uno de los roles dados.

    Uso:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role("directora", "admin"))):
            ...

    Retorna un dict con "sub" (UUID), "role" (str), "full_name" (str).
    Lanza 403 si el usuario no tiene el rol requerido.
    """

    async def _check_role(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        from app.core.database import get_pool

        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT role, full_name FROM profiles WHERE id = $1",
                current_user["sub"],
            )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PROFILE_NOT_FOUND",
                        "message": "Perfil no encontrado",
                    }
                },
            )

        user_role = row["role"]
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Se requiere rol: {', '.join(roles)}",
                    }
                },
            )

        return {
            "sub": current_user["sub"],
            "role": user_role,
            "full_name": row["full_name"],
        }

    return _check_role
