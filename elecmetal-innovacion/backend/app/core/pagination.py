"""Cursor-based pagination utilities.

Consistent pagination across all list endpoints.
Uses cursor-based (keyset) pagination for stable, efficient iteration.
"""

import re
from typing import Any

from app.core.errors import AppError, ErrorCode

_BIGINT_RE = re.compile(r"^[0-9]{1,19}$")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def validate_cursor(cursor: str | None) -> int | None:
    """Validate and parse a cursor value for BIGINT-primary-key pagination.

    Returns the cursor as int, or None if invalid/missing.
    Raises AppError if the cursor format is invalid.
    """
    if cursor is None:
        return None
    c = cursor.strip()
    if not c:
        return None
    if not _BIGINT_RE.match(c):
        raise AppError(
            code=ErrorCode.INVALID_ID,
            message=f"Cursor invalido: '{cursor}' (debe ser un entero positivo)",
            details={"field": "cursor", "value": cursor},
        )
    val = int(c)
    if val <= 0:
        raise AppError(
            code=ErrorCode.INVALID_ID,
            message=f"Cursor invalido: {cursor} (debe ser > 0)",
            details={"field": "cursor", "value": cursor},
        )
    return val


def validate_limit(limit: str | None) -> int:
    """Parse and clamp a limit parameter.

    Returns the limit as int, clamped to [1, MAX_LIMIT].
    """
    if limit is None:
        return DEFAULT_LIMIT
    try:
        val = int(limit)
    except (ValueError, TypeError):
        return DEFAULT_LIMIT
    if val < 1:
        return DEFAULT_LIMIT
    if val > MAX_LIMIT:
        return MAX_LIMIT
    return val


def build_pagination_clause(
    cursor: int | None,
    sort_col: str = "id",
    direction: str = "DESC",
) -> tuple[str, str]:
    """Build SQL WHERE clause and ORDER BY for cursor-based pagination.

    Cursor-based (keyset) pagination pattern:
      - Forward:  WHERE {sort_col} < {cursor} ORDER BY {sort_col} DESC
      - Backward: WHERE {sort_col} > {cursor} ORDER BY {sort_col} ASC

    The caller specifies direction; this function returns:
      (where_clause, order_clause)

    A cursor of None means "first page" (no WHERE clause).
    """
    if cursor is None:
        return "", f"ORDER BY {sort_col} {direction}"

    if direction.upper() == "DESC":
        return f"WHERE {sort_col} < {cursor}", f"ORDER BY {sort_col} DESC"
    else:
        return f"WHERE {sort_col} > {cursor}", f"ORDER BY {sort_col} ASC"


def paginated_response(
    rows: list[Any],
    cursor_field: str = "id",
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Build a paginated response envelope.

    Returns:
        {
            "data": [...],
            "pagination": {
                "has_more": bool,
                "next_cursor": str | None,
                "limit": int,
            }
        }
    """
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last_item = rows[-1]
        if isinstance(last_item, dict):
            next_cursor = str(last_item.get(cursor_field, ""))
        else:
            next_cursor = str(getattr(last_item, cursor_field, ""))

    return {
        "data": rows,
        "pagination": {
            "has_more": has_more,
            "next_cursor": next_cursor,
            "limit": limit,
        },
    }


def build_sort_clause(
    sort_by: str | None,
    sort_dir: str | None,
    allowed_columns: set[str],
    default_sort: str = "created_at",
    default_dir: str = "DESC",
) -> str:
    """Build a safe ORDER BY clause from user-provided sort parameters.

    Only allows columns in `allowed_columns` to prevent SQL injection.
    """
    col = default_sort
    if sort_by and sort_by in allowed_columns:
        col = sort_by

    direction = default_dir.upper()
    if sort_dir and sort_dir.upper() in ("ASC", "DESC"):
        direction = sort_dir.upper()

    return f"ORDER BY {col} {direction}"
