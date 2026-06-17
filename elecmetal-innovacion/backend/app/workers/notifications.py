"""
Worker de notificaciones.

Lee `notifications WHERE status = 'pending'` cada N segundos,
obtiene email desde auth.users, construye contenido segun notification_type,
dispara envio por Resend y actualiza estado.

Iniciado por Railway como proceso separado:
  python -m app.workers.notifications
"""

import asyncio
import asyncpg
import resend
import structlog

from app.core.config import settings

log = structlog.get_logger()

POLL_INTERVAL = 30  # segundos entre pasadas

resend.api_key = settings.resend_api_key

FETCH_PENDING = """
    SELECT n.id, n.notification_type, n.initiative_id, n.metadata,
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

MARK_SENT = "UPDATE notifications SET status = 'sent', sent_at = now() WHERE id = $1"

MARK_FAILED = """
    UPDATE notifications
    SET status = 'failed',
        metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('error', $2)
    WHERE id = $1
"""


def build_email(notification: asyncpg.Record) -> tuple[str, str]:
    """Retorna (subject, html_body) segun el tipo de notificacion."""
    notif_type = notification["notification_type"]

    if notif_type == "receipt_to_applicant":
        code = notification["initiative_code"] or "—"
        title = notification["initiative_title"] or "Sin titulo"
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
        code = notification["initiative_code"] or "—"
        title = notification["initiative_title"] or "Sin titulo"
        subject = f"Nueva iniciativa para evaluar — {code}"
        body = (
            f"<p>Una nueva iniciativa <strong>{title}</strong> "
            f"({code}) ha sido postulada y esta lista para revision.</p>"
            f"<p>Ingresa al panel para revisarla y activar al Evaluador.</p>"
        )
        return subject, body

    return "Notificacion", "<p>Sin contenido definido.</p>"


async def process_pending(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        pending = await conn.fetch(FETCH_PENDING)
        if not pending:
            return

        log.info("notifications.found", count=len(pending))
        for notif in pending:
            notif_id = str(notif["id"])
            try:
                subject, body = build_email(notif)
                resend.Emails.send({
                    "from": settings.email_from,
                    "to": notif["recipient_email"],
                    "subject": subject,
                    "html": body,
                })
                await conn.execute(MARK_SENT, notif["id"])
                log.info("notification.sent", id=notif_id, type=notif["notification_type"])
            except Exception as exc:
                await conn.execute(MARK_FAILED, notif["id"], str(exc)[:500])
                log.error("notification.failed", id=notif_id, error=str(exc))


async def run() -> None:
    log.info("worker.start", poll_interval=POLL_INTERVAL)
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=3)
    try:
        while True:
            try:
                await process_pending(pool)
            except Exception as exc:
                log.error("worker.error", error=str(exc))
            await asyncio.sleep(POLL_INTERVAL)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())
