import re as _re
from functools import lru_cache

import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import AppError, ErrorCode

bearer_scheme = HTTPBearer(auto_error=False)


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
            raise AppError(
                code=ErrorCode.UNAUTHORIZED,
                message="Clave de firma no encontrada",
                details={"reason": "unknown_key_id"},
            )

        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload

    except JWTError as exc:
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="Token inválido o expirado",
            details={"reason": "jwt_decode_error"},
        ) from exc
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="No se pudo validar el token",
            details={"reason": str(exc)},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Dependencia FastAPI: extrae y valida el usuario del token Bearer."""
    if credentials is None:
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="Token de autorizacion requerido",
        )
    return decode_supabase_jwt(credentials.credentials)


# ── Shared validation helpers (use AppError) ────────────────────────────────

_UUID_RE = _re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_BIGINT_RE = _re.compile(r"^[0-9]{1,19}$")


def require_user_id(user: dict) -> str:
    """Extrae y valida el user_id (sub) del JWT. Lanza AppError si falta."""
    user_id = user.get("sub")
    if not user_id or not _UUID_RE.fullmatch(user_id):
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="Token sin identificador de usuario valido",
        )
    return user_id


def require_bigint_id(value: str, label: str = "ID") -> int:
    """Valida que un string sea un BIGINT positivo. Lanza AppError si no."""
    if not _BIGINT_RE.match(value):
        raise AppError(
            code=ErrorCode.INVALID_ID,
            message=f"{label} invalido — debe ser un numero entero positivo",
            details={"field": label, "value": value},
        )
    return int(value)


async def require_directora(user: dict) -> str:
    """Verifica que el usuario tenga rol directora/admin. Devuelve user_id."""
    from app.core.database import get_pool

    user_id = require_user_id(user)

    pool = get_pool()
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            f"SELECT role FROM profiles WHERE id = '{user_id}'"
        )
        if not profile or profile["role"] not in ("directora", "admin"):
            raise AppError(
                code=ErrorCode.FORBIDDEN,
                message="Solo directora o admin pueden realizar esta accion",
            )
    return user_id


def require_role(*roles: str):
    """Fabrica de dependencia: valida que el usuario tenga uno de los roles dados.

    Uso:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role("directora", "admin"))):
            ...

    Retorna un dict con "sub" (UUID), "role" (str), "full_name" (str).
    Lanza AppError 403 si el usuario no tiene el rol requerido.
    """

    async def _check_role(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        from app.core.database import get_pool

        user_id = require_user_id(current_user)

        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT role, full_name FROM profiles WHERE id = $1",
                user_id,
            )

        if row is None:
            raise AppError(
                code=ErrorCode.FORBIDDEN,
                message="Perfil no encontrado",
            )

        user_role = row["role"]
        if user_role not in roles:
            raise AppError(
                code=ErrorCode.FORBIDDEN,
                message=f"Se requiere rol: {', '.join(roles)}",
            )

        return {
            "sub": user_id,
            "role": user_role,
            "full_name": row["full_name"],
        }

    return _check_role
