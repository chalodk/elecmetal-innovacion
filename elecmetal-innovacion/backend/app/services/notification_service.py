"""Notification service (Step 8 of the boot sequence).

Handles creating notification records when an initiative is persisted,
and processing pending notifications (sending emails via Resend).

Architecture:
  - create_notifications(): called synchronously after persist_initiative()
  - process_pending(): called by the worker or API endpoint
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.database import get_pool

logger = logging.getLogger(__name__)

# Lazy import — resend may not be configured in dev
_resend: Any = None


def _get_resend():
    global _resend
    if _resend is None:
        key = (settings.resend_api_key or "").strip()
        # Skip placeholder keys (template values like "re_...")
        if not key or key == "re_..." or len(key) < 20:
            logger.warning(
                "resend not configured — RESEND_API_KEY is missing or a placeholder"
            )
            return None
        try:
            import resend
            resend.api_key = key
            _resend = resend
        except ImportError:
            logger.warning("resend package not installed — emails will be skipped")
    return _resend


# ── SQL helpers (Management API doesn't support parameterized queries) ─────

def _sql_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


# ── Create notifications ────────────────────────────────────────────────────

async def create_notifications(
    initiative_id: int,
    applicant_user_id: str,
    initiative_code: str,
    initiative_title: str,
) -> list[dict]:
    """Create notification records after a successful initiative persistence.

    Creates:
      1. receipt_to_applicant — confirmation to the postulant
      2. notice_to_director  — alert to the innovation director

    Returns the list of created notification rows.
    """
    pool = get_pool()
    created: list[dict] = []

    async with pool.acquire() as conn:
        # 1. Receipt to applicant
        row = await conn.fetchrow(
            f"INSERT INTO notifications (initiative_id, recipient_user_id, notification_type, status) "
            f"VALUES ({initiative_id}, '{applicant_user_id}', 'receipt_to_applicant', 'pending') "
            f"RETURNING *"
        )
        created.append(dict(row))
        logger.info(
            "notification.created id=%s type=receipt_to_applicant initiative_id=%s",
            row["id"], initiative_id,
        )

        # 2. Notice to director — find directora(s) by role
        directors = await conn.fetch(
            "SELECT id, full_name FROM profiles WHERE role IN ('directora', 'admin')"
        )

        if directors:
            for director in directors:
                row = await conn.fetchrow(
                    f"INSERT INTO notifications (initiative_id, recipient_user_id, notification_type, status) "
                    f"VALUES ({initiative_id}, '{director['id']}', 'notice_to_director', 'pending') "
                    f"RETURNING *"
                )
                created.append(dict(row))
                logger.info(
                    "notification.created id=%s type=notice_to_director director=%s",
                    row["id"], director.get("full_name", director["id"]),
                )
        else:
            logger.warning(
                "notification.no_director initiative_id=%s — no hay directora/admin",
                initiative_id,
            )

    return created


# ── Process pending notifications ───────────────────────────────────────────

FETCH_PENDING = """
    SELECT n.id, n.notification_type, n.initiative_id, n.recipient_user_id, n.metadata,
           u.email AS recipient_email,
           i.initiative_code, i.title AS initiative_title
    FROM notifications n
    JOIN profiles p ON n.recipient_user_id = p.id
    JOIN auth.users u ON p.id = u.id
    LEFT JOIN initiatives i ON n.initiative_id = i.id
    WHERE n.status = 'pending'
    ORDER BY n.created_at
    LIMIT 50
"""


def _build_email(notification: dict) -> tuple[str, str]:
    """Build (subject, html_body) for a notification."""
    notif_type = notification["notification_type"]
    code = notification.get("initiative_code") or "---"
    title = notification.get("initiative_title") or "Sin titulo"

    if notif_type == "receipt_to_applicant":
        subject = f"Tu iniciativa ha sido recibida — {code}"
        body = (
            f"<p>Hola,</p>"
            f"<p>Tu iniciativa <strong>{title}</strong> ha sido registrada "
            f"con el codigo <strong>{code}</strong>.</p>"
            f"<p>El equipo de innovacion la revisara y te notificaremos "
            f"cuando avance a evaluacion.</p>"
        )
        return subject, body

    if notif_type == "notice_to_director":
        subject = f"Nueva iniciativa para evaluar — {code}"
        body = (
            f"<p>Una nueva iniciativa <strong>{title}</strong> "
            f"({code}) ha sido postulada y esta lista para revision.</p>"
            f"<p>Ingresa al panel para revisarla y activar al Evaluador.</p>"
        )
        return subject, body

    return "Notificacion", "<p>Sin contenido definido.</p>"


async def process_pending() -> dict:
    """Fetch pending notifications, send emails via Resend, update status.

    Returns a summary dict with counts.
    """
    pool = get_pool()
    summary = {"found": 0, "sent": 0, "failed": 0, "skipped": 0}
    resend = _get_resend()

    async with pool.acquire() as conn:
        pending = await conn.fetch(FETCH_PENDING)
        summary["found"] = len(pending)

        if not pending:
            return summary

        logger.info("notifications.processing count=%d", len(pending))

        for notif in pending:
            notif_id = notif["id"]
            notif_type = notif["notification_type"]
            recipient_email = notif.get("recipient_email")

            if not recipient_email:
                logger.warning(
                    "notification.no_email id=%s type=%s",
                    notif_id, notif_type,
                )
                await conn.execute(
                    f"UPDATE notifications SET status = 'failed', "
                    f"metadata = COALESCE(metadata, '{{}}'::jsonb) || "
                    f"'{{\"error\": \"No email found for recipient\"}}'::jsonb "
                    f"WHERE id = {notif_id}"
                )
                summary["failed"] += 1
                continue

            if resend is None:
                logger.warning(
                    "notification.skipped id=%s type=%s — Resend not configured",
                    notif_id, notif_type,
                )
                summary["skipped"] += 1
                continue

            try:
                subject, body = _build_email(dict(notif))

                resend.Emails.send({
                    "from": settings.email_from,
                    "to": recipient_email,
                    "subject": subject,
                    "html": body,
                })

                await conn.execute(
                    f"UPDATE notifications SET status = 'sent', sent_at = now() "
                    f"WHERE id = {notif_id}"
                )
                summary["sent"] += 1
                logger.info(
                    "notification.sent id=%s type=%s to=%s",
                    notif_id, notif_type, recipient_email,
                )
            except Exception as exc:
                error_msg = str(exc)[:500]
                escaped_err = error_msg.replace("'", "''")
                await conn.execute(
                    f"UPDATE notifications SET status = 'failed', "
                    f"metadata = COALESCE(metadata, '{{}}'::jsonb) || "
                    f"'{{\"error\": \"{escaped_err}\"}}'::jsonb "
                    f"WHERE id = {notif_id}"
                )
                summary["failed"] += 1
                logger.error(
                    "notification.failed id=%s type=%s error=%s",
                    notif_id, notif_type, error_msg,
                )

        # ── Transition initiatives to 'notificado' if all notifications sent ──
        if summary["sent"] > 0:
            await conn.execute(
                "UPDATE initiatives i SET status = 'notificado', updated_at = now() "
                "WHERE i.status = 'persistido' "
                "AND i.id IN ("
                "  SELECT DISTINCT n.initiative_id FROM notifications n "
                "  WHERE n.status = 'sent'"
                ") "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM notifications n2 "
                "  WHERE n2.initiative_id = i.id AND n2.status = 'pending'"
                ")"
            )

        return summary
