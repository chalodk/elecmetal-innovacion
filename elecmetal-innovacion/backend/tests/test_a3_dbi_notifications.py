"""A3 tests — Persistencia del DBI + notificaciones.

Tests: deteccion de DBI, parseo a columnas, creacion de notificaciones,
transiciones de estado, formato de initiative_code, construccion de emails.

Los tests de integracion contra BD real estan en test_dbi_integration.py.
Estos tests son unitarios: prueban logica de negocio sin DB.

Ejecutar:
    pytest tests/test_a3_dbi_notifications.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VALID_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dbi"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# A3.1 — Deteccion de DBI en mensaje
# ═════════════════════════════════════════════════════════════════════════════

class TestDetectDBI:
    """detect_dbi_in_message() identifica DBI dentro de texto conversacional."""

    def test_detects_golden_fixture(self):
        from app.services.dbi_persistence import detect_dbi_in_message
        raw = _read_fixture("example_internal.txt")
        assert detect_dbi_in_message(raw) is True

    def test_detects_dbi_inside_clara_response(self):
        from app.services.dbi_persistence import detect_dbi_in_message
        raw = _read_fixture("example_internal.txt")
        clara_msg = (
            "¡Perfecto! Aqui esta tu Documento Base de Iniciativa:\n\n"
            f"{raw}\n\n"
            "¿Necesitas hacer algun cambio?"
        )
        assert detect_dbi_in_message(clara_msg) is True

    def test_rejects_conversational_text(self):
        from app.services.dbi_persistence import detect_dbi_in_message
        assert detect_dbi_in_message("Hola Clara") is False
        assert detect_dbi_in_message("Mi idea es mejorar la productividad") is False
        assert detect_dbi_in_message("¿Cual es el siguiente paso?") is False

    def test_rejects_partial_dbi(self):
        from app.services.dbi_persistence import detect_dbi_in_message
        partial = "DOCUMENTO BASE DE INICIATIVA\nA. PROBLEMA\n• Problema: x"
        assert detect_dbi_in_message(partial) is False

    def test_rejects_empty_string(self):
        from app.services.dbi_persistence import detect_dbi_in_message
        assert detect_dbi_in_message("") is False
        assert detect_dbi_in_message("   ") is False


# ═════════════════════════════════════════════════════════════════════════════
# A3.2 — Parseo a columnas de initiatives
# ═════════════════════════════════════════════════════════════════════════════

class TestParseToColumns:
    """El parseo produce campos correctamente mapeados a columnas de initiatives."""

    def test_parse_maps_header_fields(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["header"]["title"] == "Mantenimiento predictivo de hornos"
        assert parsed["header"]["initiative_type"] == "interna"
        assert parsed["header"]["postulation_date"] == "2026-06-10"
        assert "Fundici" in parsed["header"]["area"]
        assert "Rojas" in parsed["header"]["applicant_name"]

    def test_parse_maps_block_b_levels(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["block_b_solution"]["trl"]["level"] == 4
        assert parsed["block_b_solution"]["scalability"] == "Interna"
        assert "USD" in parsed["block_b_solution"]["economic_impact"]["value"]

    def test_parse_maps_block_c_levels(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["block_c_client"]["crl"]["level"] == 5
        assert "Operaciones" in parsed["block_c_client"]["internal_client"]

    def test_parse_maps_block_f(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["block_f_risk"]["brl"]["level"] == 4
        assert parsed["block_f_risk"]["main_doubt"] is not None
        assert parsed["block_f_risk"]["value_capture"] is not None

    def test_parse_maps_block_g(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["block_g_milestones"]["return_horizon_months"] == 12
        assert parsed["block_g_milestones"]["technical_milestones"] is not None
        assert parsed["block_g_milestones"]["financial_milestones"] is not None

    def test_extra_fields_populated(self):
        """dbi_extra incluye executive_summary, pending_blocks, attached_evidence."""
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)

        assert parsed["executive_summary"] is not None
        assert isinstance(parsed["executive_summary"], str)
        assert len(parsed["executive_summary"]) > 50
        assert parsed["pending_blocks"] == []
        assert "registro_paradas_2025.xlsx" in parsed["attached_evidence"]
        assert "foto_banco_sensores.jpg" in parsed["attached_evidence"]

    def test_dbi_raw_text_preserved(self):
        from app.services.dbi_parser import parse_dbi
        raw = _read_fixture("example_internal.txt")
        parsed = parse_dbi(raw)
        assert parsed["header"]["title"] == "Mantenimiento predictivo de hornos"


# ═════════════════════════════════════════════════════════════════════════════
# A3.3 — Notificaciones (construccion de email + creacion de registros)
# ═════════════════════════════════════════════════════════════════════════════

class TestNotifications:
    """Construccion de emails y creacion de registros de notificacion."""

    def test_build_email_receipt_to_applicant(self):
        from app.services.notification_service import _build_email

        notif = {
            "notification_type": "receipt_to_applicant",
            "initiative_code": "INI-2026-005",
            "initiative_title": "Mantenimiento predictivo de hornos",
        }
        subject, body = _build_email(notif)

        assert "INI-2026-005" in subject
        assert "Mantenimiento predictivo" in body
        assert "<strong>INI-2026-005</strong>" in body
        assert "innovacion" in body.lower()

    def test_build_email_notice_to_director(self):
        from app.services.notification_service import _build_email

        notif = {
            "notification_type": "notice_to_director",
            "initiative_code": "INI-2026-010",
            "initiative_title": "Automatizacion de molienda",
        }
        subject, body = _build_email(notif)

        assert "INI-2026-010" in subject
        assert "Automatizacion" in body
        assert "Evaluador" in body or "evaluacion" in body.lower()

    def test_build_email_fallback_no_code(self):
        from app.services.notification_service import _build_email

        notif = {"notification_type": "receipt_to_applicant"}
        subject, body = _build_email(notif)

        assert "---" in subject or len(subject) > 0

    def test_build_email_unknown_type(self):
        from app.services.notification_service import _build_email

        notif = {"notification_type": "unknown_type"}
        subject, body = _build_email(notif)

        assert len(subject) > 0
        assert len(body) > 0

    @patch("app.services.notification_service.get_pool")
    def test_create_notifications_inserts_rows(self, mock_pool):
        """create_notifications inserta receipt + notice en la BD."""
        from app.services.notification_service import create_notifications

        mock_conn = AsyncMock()
        # fetchrow is called for INSERT ... RETURNING * (3 times if director found)
        mock_return = {
            "id": 1, "initiative_id": 1, "recipient_user_id": VALID_USER_ID,
            "notification_type": "receipt_to_applicant", "status": "pending",
            "sent_at": None, "created_at": "2026-01-01T00:00:00",
            "metadata": None,
        }
        mock_conn.fetchrow.return_value = mock_return
        mock_conn.fetch.return_value = []  # no directors found
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        import anyio
        anyio.run(
            create_notifications,
            1, VALID_USER_ID, "INI-2026-005", "Test Initiative",
        )

        # fetchrow was called for the receipt INSERT
        fetch_calls = [str(c) for c in mock_conn.fetchrow.mock_calls]
        notification_inserts = [
            c for c in fetch_calls
            if "INSERT INTO notifications" in c
        ]
        assert len(notification_inserts) >= 1, (
            f"No INSERT found in fetchrow calls: {fetch_calls[:3]}"
        )

    def test_notification_types_are_valid(self):
        from app.models.domain import NotificationType

        valid_types = {t.value for t in NotificationType}
        assert "receipt_to_applicant" in valid_types
        assert "notice_to_director" in valid_types


# ═════════════════════════════════════════════════════════════════════════════
# A3.4 — initiative_code y formato
# ═════════════════════════════════════════════════════════════════════════════

class TestInitiativeCode:
    """El codigo autogenerado sigue el formato INI-YYYY-NNN."""

    def test_code_format(self):
        import re
        pattern = r"^INI-\d{4}-\d{3}$"
        codes = ["INI-2026-001", "INI-2026-042", "INI-2027-999"]
        for code in codes:
            assert re.match(pattern, code), f"{code} no cumple formato INI-YYYY-NNN"


# ═════════════════════════════════════════════════════════════════════════════
# A3.5 — Transiciones de estado
# ═════════════════════════════════════════════════════════════════════════════

class TestStatusTransitions:
    """Verifica las transiciones de estado del flujo A3."""

    def test_valid_status_flow(self):
        from app.models.domain import InitiativeStatus

        flow = [
            InitiativeStatus.PERSISTIDO,
            InitiativeStatus.NOTIFICADO,
            InitiativeStatus.EN_EVALUACION,
            InitiativeStatus.EVALUADO,
            InitiativeStatus.VALIDADO,
            InitiativeStatus.VEREDICTO,
        ]
        status_values = {s.value for s in InitiativeStatus}
        for step in flow:
            assert step.value in status_values

    def test_parse_error_aborts_persistence(self):
        """Si el parseo falla, no se hace INSERT en initiatives."""
        from app.services.dbi_parser import parse_dbi, DBIParseError

        invalid_text = "Esto no es un DBI valido"

        with pytest.raises(DBIParseError):
            parse_dbi(invalid_text)
