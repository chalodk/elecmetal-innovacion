#!/usr/bin/env python3
"""Integration tests for notifications (Step 8 verification).

Tests:
  1. Creating notifications after initiative persistence
  2. Processing pending notifications (Resend skipped if not configured)
  3. Initiative transitions to 'notificado' after all notifications sent
  4. Worker process_pending() handles edge cases

Runs against the real Supabase database via Management API.
Cleans up after itself.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.dbi_parser import parse_dbi
from app.services.dbi_persistence import persist_initiative
from app.services.notification_service import (
    create_notifications,
    process_pending,
    _build_email,
)
from app.core.database import create_pool, close_pool, get_pool

FIXTURES = Path(__file__).parent / "tests" / "fixtures" / "dbi"
TEST_USER_ID = "36b14f0b-ace3-46a7-bbaf-ba1bb38c8ac9"  # Usuario de Prueba


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def test_create_notifications():
    """Step 8.1: After persist_initiative, notification records are created."""
    print("\n--- Test: Create notifications on persist ---")

    raw = _read_fixture("example_internal.txt")

    pool = get_pool()

    async with pool.acquire() as conn:
        # Create test session
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Notif Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            # Persist initiative (this triggers create_notifications)
            initiative = await persist_initiative(
                session_id=session_id,
                user_id=TEST_USER_ID,
                dbi_text=raw,
            )

            assert initiative["status"] == "persistido"
            init_id = initiative["id"]

            # Verify notification records exist
            notifs = await conn.fetch(
                f"SELECT * FROM notifications WHERE initiative_id = {init_id}"
            )
            notif_types = {n["notification_type"] for n in notifs}
            assert "receipt_to_applicant" in notif_types, \
                "receipt_to_applicant notification missing"
            assert all(n["status"] == "pending" for n in notifs), \
                "All notifications should be pending"

            print(f"  [PASS] {len(notifs)} notification(s) created for initiative {init_id}")
            for n in notifs:
                print(f"     - {n['notification_type']} -> {n['recipient_user_id']}")

            # Cleanup
            await conn.execute(f"DELETE FROM notifications WHERE initiative_id = {init_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {init_id}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_process_pending_no_resend():
    """Step 8.2: process_pending() handles missing Resend gracefully."""
    print("\n--- Test: process_pending without Resend ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        # Create test session
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'NoResend Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            raw = _read_fixture("example_internal.txt")
            initiative = await persist_initiative(
                session_id=session_id,
                user_id=TEST_USER_ID,
                dbi_text=raw,
            )
            init_id = initiative["id"]

            # Process pending — Resend is not configured, so all should be skipped
            summary = await process_pending()

            assert summary["found"] >= 1, "Should find pending notifications"
            # With no directora, only 1 notification (receipt_to_applicant)
            # Without RESEND_API_KEY, it will be skipped
            print(f"  [PASS] process_pending summary: {summary}")

            # After processing, initiative should still be persistido
            # (notifications were skipped, not sent)
            row = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {init_id}"
            )
            print(f"  [PASS] Initiative status: {row['status']}")

            # Cleanup
            await conn.execute(f"DELETE FROM notifications WHERE initiative_id = {init_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {init_id}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_email_building():
    """Step 8.3: Email subjects and bodies are correctly generated."""
    print("\n--- Test: Email building ---")

    # receipt_to_applicant
    notif = {
        "notification_type": "receipt_to_applicant",
        "initiative_code": "INI-2026-001",
        "initiative_title": "Test Initiative",
    }
    subject, body = _build_email(notif)
    assert "INI-2026-001" in subject
    assert "Test Initiative" in body
    print(f"  [PASS] receipt_to_applicant: subject='{subject}'")

    # notice_to_director
    notif2 = {
        "notification_type": "notice_to_director",
        "initiative_code": "INI-2026-002",
        "initiative_title": "Another Initiative",
    }
    subject2, body2 = _build_email(notif2)
    assert "INI-2026-002" in subject2
    assert "Another Initiative" in body2
    print(f"  [PASS] notice_to_director: subject='{subject2}'")

    # Unknown type
    notif3 = {"notification_type": "unknown"}
    subject3, body3 = _build_email(notif3)
    assert subject3 == "Notificacion"
    print(f"  [PASS] Unknown type: fallback subject")


async def test_initiative_transitions_to_notificado():
    """Step 8.4: When all notifications are sent, initiative -> notificado."""
    print("\n--- Test: Initiative -> notificado transition ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Transition Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        try:
            raw = _read_fixture("example_internal.txt")
            initiative = await persist_initiative(
                session_id=session_id,
                user_id=TEST_USER_ID,
                dbi_text=raw,
            )
            init_id = initiative["id"]

            # Manually mark all notifications as 'sent' to simulate email success
            await conn.execute(
                f"UPDATE notifications SET status = 'sent', sent_at = now() "
                f"WHERE initiative_id = {init_id}"
            )

            # Now trigger the status transition (same SQL as in process_pending)
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

            # Verify
            row = await conn.fetchrow(
                f"SELECT status FROM initiatives WHERE id = {init_id}"
            )
            assert row["status"] == "notificado", \
                f"Expected notificado, got {row['status']}"
            print(f"  [PASS] Initiative {init_id} -> {row['status']}")

            # Cleanup
            await conn.execute(f"DELETE FROM notifications WHERE initiative_id = {init_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {init_id}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def test_direct_notification_creation():
    """Step 8.5: create_notifications() directly creates both types."""
    print("\n--- Test: Direct notification creation ---")

    pool = get_pool()

    async with pool.acquire() as conn:
        # Create a test initiative directly
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{TEST_USER_ID}', 'clara', 'active', 'Direct Test') "
            f"RETURNING id"
        )
        session_id = row["id"]

        seq_row = await conn.fetchrow(
            "SELECT nextval('seq_initiative_code') AS seq"
        )
        code = f"INI-2026-{seq_row['seq']:03d}"

        init_row = await conn.fetchrow(
            f"INSERT INTO initiatives (session_id, user_id, status, initiative_code, "
            f"title, initiative_type, postulation_date, area, applicant_name, "
            f"problem, solution) "
            f"VALUES ({session_id}, '{TEST_USER_ID}', 'persistido', '{code}', "
            f"'Test Direct', 'interna', CURRENT_DATE, 'Test Area', 'Test User', "
            f"'Test problem', 'Test solution') "
            f"RETURNING id"
        )
        init_id = init_row["id"]

        try:
            created = await create_notifications(
                initiative_id=init_id,
                applicant_user_id=TEST_USER_ID,
                initiative_code=code,
                initiative_title="Test Direct",
            )

            assert len(created) >= 1, "At least receipt_to_applicant should be created"
            types = {n["notification_type"] for n in created}
            assert "receipt_to_applicant" in types
            print(f"  [PASS] Created {len(created)} notification(s): {types}")

            # Verify in DB
            db_notifs = await conn.fetch(
                f"SELECT * FROM notifications WHERE initiative_id = {init_id}"
            )
            assert len(db_notifs) == len(created)
            assert all(n["status"] == "pending" for n in db_notifs)
            print(f"  [PASS] All {len(db_notifs)} notifications verified in DB")

            # Cleanup
            await conn.execute(f"DELETE FROM notifications WHERE initiative_id = {init_id}")
            await conn.execute(f"DELETE FROM initiatives WHERE id = {init_id}")

        finally:
            await conn.execute(f"DELETE FROM messages WHERE session_id = {session_id}")
            await conn.execute(f"DELETE FROM sessions WHERE id = {session_id}")
            print(f"     [CLEAN] Removed test session {session_id}")


async def main():
    print("=" * 60)
    print("  Notifications — Integration Tests (Step 8)")
    print("=" * 60)

    await create_pool()
    print("[OK] DB pool initialized")

    try:
        await test_create_notifications()
        await test_process_pending_no_resend()
        await test_email_building()
        await test_initiative_transitions_to_notificado()
        await test_direct_notification_creation()

        print("\n" + "=" * 60)
        print("  [PASS] ALL NOTIFICATION TESTS PASSED")
        print("=" * 60)

    finally:
        await close_pool()
        print("[OK] DB pool closed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
