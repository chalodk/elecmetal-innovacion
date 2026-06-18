"""Notification worker (Step 8 of the boot sequence).

Polls `notifications WHERE status = 'pending'` on an interval,
sends emails via Resend, and updates status.

Uses the Management API bridge (ApiPool) for DB access — compatible
with IPv4-only networks.

Can run as a standalone process:
    python -m app.workers.notifications

Or triggered via API endpoint:
    POST /api/v1/notifications/process
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure backend is on sys.path when run as standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.database import create_pool, close_pool
from app.services.notification_service import process_pending

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.environ.get("NOTIFICATION_POLL_INTERVAL", "30"))


async def run_once() -> dict:
    """Single pass: initialize pool, process pending, close pool."""
    await create_pool()
    try:
        summary = await process_pending()
        return summary
    finally:
        await close_pool()


async def run_loop() -> None:
    """Continuous polling loop for the worker process."""
    logger.info("notification_worker.start poll_interval=%d", POLL_INTERVAL)
    await create_pool()
    try:
        while True:
            try:
                summary = await process_pending()
                if summary["found"] > 0:
                    logger.info(
                        "notification_worker.cycle found=%d sent=%d failed=%d skipped=%d",
                        summary["found"], summary["sent"],
                        summary["failed"], summary["skipped"],
                    )
            except Exception as exc:
                logger.error("notification_worker.error error=%s", exc)
            await asyncio.sleep(POLL_INTERVAL)
    finally:
        await close_pool()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_loop())
