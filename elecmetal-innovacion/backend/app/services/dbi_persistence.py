"""Persist a parsed DBI to the initiatives table (Step 7 of the boot sequence).

Takes the structured dict from `dbi_parser.parse_dbi()`, maps fields to
`initiatives` columns + `dbi_extra JSONB`, generates an `initiative_code` via
`seq_initiative_code`, and transitions the session to `completed`.

The mapping follows `docs/context/references/dbi-template.md` > Mapeo campo DBI →
columna BD, with fields marked ➕ going into `dbi_extra`.
"""

from __future__ import annotations

import json
import logging

from app.core.database import get_pool
from app.services.dbi_parser import parse_dbi

logger = logging.getLogger(__name__)


def _sql_str(value: str | None) -> str:
    """Format a string value for SQL interpolation (NULL or escaped literal)."""
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _sql_int(value: int | None) -> str:
    """Format an integer value for SQL interpolation (NULL or bare number)."""
    if value is None:
        return "NULL"
    return str(value)


def _build_dbi_extra(parsed: dict) -> dict:
    """Extract fields without a dedicated column into the dbi_extra JSONB payload.

    Structured by block to keep the JSONB queryable and readable.
    """
    extra: dict = {}

    # ── Top-level ──
    if parsed.get("executive_summary"):
        extra["executive_summary"] = parsed["executive_summary"]

    # ── Block A extra ──
    a = parsed.get("block_a_problem", {})
    a_extra = {}
    for k in ("why_it_matters", "who_has_it", "current_solution"):
        if a.get(k):
            a_extra[k] = a[k]
    if a_extra:
        extra["block_a_extra"] = a_extra

    # ── Block B extra ──
    b = parsed.get("block_b_solution", {})
    b_extra = {}
    for k in (
        "differentiator_novelty_grade",
        "differentiator_text",
        "competition_grade",
        "competition_text",
    ):
        if b.get(k):
            b_extra[k] = b[k]

    ei = b.get("economic_impact") or {}
    if ei.get("source"):
        b_extra["economic_impact_source"] = ei["source"]
    if ei.get("beneficiary"):
        b_extra["economic_impact_beneficiary"] = ei["beneficiary"]
    if ei.get("classification"):
        b_extra["economic_impact_classification"] = ei["classification"]

    if b.get("market_size"):
        b_extra["market_size"] = b["market_size"]
    if b.get("market_repeatability"):
        b_extra["market_repeatability"] = b["market_repeatability"]

    trl = b.get("trl") or {}
    if trl.get("evidence"):
        b_extra["trl_evidence"] = trl["evidence"]

    if b_extra:
        extra["block_b_extra"] = b_extra

    # ── Block C extra ──
    c = parsed.get("block_c_client", {})
    c_extra = {}
    if c.get("target_client_type"):
        c_extra["target_client_type"] = c["target_client_type"]
    crl = c.get("crl") or {}
    if crl.get("evidence"):
        c_extra["crl_evidence"] = crl["evidence"]
    if c_extra:
        extra["block_c_extra"] = c_extra

    # ── Block D extra ──
    d = parsed.get("block_d_alignment", {})
    d_extra = {}
    if d.get("horizon"):
        d_extra["horizon"] = d["horizon"]
    if d_extra:
        extra["block_d_extra"] = d_extra

    # ── Block E extra ──
    e = parsed.get("block_e_team", {})
    e_extra = {}
    for k in ("applicant_area", "support_received", "other_resources"):
        if e.get(k):
            e_extra[k] = e[k]
    if e_extra:
        extra["block_e_extra"] = e_extra

    # ── Block F extra ──
    f = parsed.get("block_f_risk", {})
    f_extra = {}
    uncertainty = f.get("uncertainty") or {}
    if any(uncertainty.values()):
        f_extra["uncertainty"] = {
            k: v for k, v in uncertainty.items() if v
        }
    brl = f.get("brl") or {}
    if brl.get("evidence"):
        f_extra["brl_evidence"] = brl["evidence"]
    if f_extra:
        extra["block_f_extra"] = f_extra

    # ── Footer ──
    if parsed.get("attached_evidence"):
        extra["attached_evidence"] = parsed["attached_evidence"]
    if parsed.get("pending_blocks"):
        extra["pending_blocks"] = parsed["pending_blocks"]

    return extra


async def persist_initiative(
    session_id: int,
    user_id: str,
    dbi_text: str,
) -> dict:
    """Parse DBI text, INSERT into initiatives, transition session → completed.

    Uses persist_initiative_atomic() (PL/pgSQL) for atomic INSERT + session
    UPDATE — a single SQL call via the Management API. If any DB operation
    fails, the function rolls back automatically (no inconsistent state).

    Args:
        session_id: The session that produced this DBI.
        user_id: UUID (sub from JWT) of the postulant.
        dbi_text: The raw DBI text from Clara's final message.

    Returns:
        The newly inserted initiative row as a dict.

    Raises:
        DBIParseError: If the text doesn't match the DBI v5.9 contract.
    """
    parsed = parse_dbi(dbi_text)

    header = parsed["header"]
    b = parsed.get("block_b_solution", {})
    c = parsed.get("block_c_client", {})
    d = parsed.get("block_d_alignment", {})
    e = parsed.get("block_e_team", {})
    f = parsed.get("block_f_risk", {})
    g = parsed.get("block_g_milestones", {})

    trl = b.get("trl") or {}
    crl = c.get("crl") or {}
    brl = f.get("brl") or {}
    ei = b.get("economic_impact") or {}

    dbi_extra = _build_dbi_extra(parsed)
    dbi_extra_json = json.dumps(dbi_extra, ensure_ascii=False)
    escaped_extra = dbi_extra_json.replace("'", "''")
    escaped_raw = dbi_text.replace("'", "''")

    # ── Call atomic PL/pgSQL function (single Management API request) ────
    # The function does: nextval → code → INSERT → UPDATE session → RETURN row
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM persist_initiative_atomic("
            f"{session_id}, "
            f"'{user_id}', "
            f"{_sql_str(header.get('title'))}, "
            f"{_sql_str(header.get('initiative_type'))}, "
            f"{_sql_str(header.get('postulation_date'))}::date, "
            f"{_sql_str(header.get('area'))}, "
            f"{_sql_str(header.get('applicant_name'))}, "
            f"{_sql_str(parsed.get('block_a_problem', {}).get('problem'))}, "
            f"{_sql_str(b.get('description'))}, "
            f"{_sql_str(ei.get('value'))}, "
            f"{_sql_int(trl.get('level'))}::smallint, "
            f"{_sql_str(b.get('scalability'))}, "
            f"{_sql_str(c.get('internal_client'))}, "
            f"{_sql_str(c.get('external_client'))}, "
            f"{_sql_int(crl.get('level'))}::smallint, "
            f"{_sql_str(e.get('sponsor'))}, "
            f"{_sql_str(e.get('internal_team'))}, "
            f"{_sql_str(e.get('external_team'))}, "
            f"{_sql_str(e.get('estimated_duration'))}, "
            f"{_sql_str(f.get('main_doubt'))}, "
            f"{_sql_str(f.get('key_condition'))}, "
            f"{_sql_str(f.get('value_capture'))}, "
            f"{_sql_int(brl.get('level'))}::smallint, "
            f"{_sql_str(g.get('technical_milestones'))}, "
            f"{_sql_str(g.get('financial_milestones'))}, "
            f"{_sql_int(g.get('return_horizon_months'))}::smallint, "
            f"{_sql_str(d.get('focus'))}, "
            f"{_sql_str(escaped_raw)}, "
            f"'{escaped_extra}'::jsonb"
            f")"
        )

    initiative_id = row["id"]
    initiative_code = row["initiative_code"]

    # ── Step 8: Create notification records (non-critical, after atomic DB op) ─
    try:
        from app.services.notification_service import create_notifications
        await create_notifications(
            initiative_id=initiative_id,
            applicant_user_id=user_id,
            initiative_code=initiative_code,
            initiative_title=header.get("title") or "Sin titulo",
        )
    except Exception as exc:
        # Notifications are non-fatal — the initiative is already persisted
        logger.error(
            "dbi.notifications_failed initiative_id=%s error=%s",
            initiative_id, exc,
        )

    logger.info(
        "dbi.persisted initiative_id=%s initiative_code=%s session_id=%s",
        initiative_id, initiative_code, session_id,
    )

    return dict(row)


def detect_dbi_in_message(content: str) -> bool:
    """Quick pre-check: does this message likely contain a DBI?

    Looks for the distinctive ═══ border lines and the
    DOCUMENTO BASE DE INICIATIVA constant. This is a cheap heuristic
    run before the full parser (which validates the contract thoroughly).
    """
    border = "═"  # ═
    return (
        border in content
        and "DOCUMENTO BASE DE INICIATIVA" in content
    )
