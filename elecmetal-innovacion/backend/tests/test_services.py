"""Unit tests for backend services.

Tests:
  - DBI parser edge cases
  - DBI persistence mapping
  - Notification email building
  - Pagination utilities
  - Evaluator context building
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.dbi_parser import (
    parse_dbi, DBIParseError, _clean, _parse_level,
    _parse_economic_impact, _parse_uncertainty, _parse_key_condition,
    _parse_months, _parse_list, _split_fields, SENTINELS,
)
from app.services.notification_service import _build_email
from app.services.evaluator import _build_initiative_context
from app.core.pagination import (
    validate_cursor, validate_limit, paginated_response,
    build_sort_clause,
)


# ═════════════════════════════════════════════════════════════════════════════
# DBI Parser — edge cases
# ═════════════════════════════════════════════════════════════════════════════

class TestCleanSentinel:
    """_clean() maps sentinels to None."""

    def test_exact_sentinels(self):
        for s in SENTINELS:
            assert _clean(s) is None
            assert _clean(f"  {s}  ") is None

    def test_normal_text_passes_through(self):
        assert _clean("Texto valido") == "Texto valido"

    def test_empty_and_whitespace(self):
        assert _clean("") is None
        assert _clean("   ") is None
        assert _clean(None) is None


class TestParseLevel:
    """_parse_level() validates TRL/CRL/BRL 1-9."""

    def test_valid_levels(self):
        for i in range(1, 10):
            result = _parse_level(f"{i} — Evidencia: test", "TRL")
            assert result["level"] == i
            assert result["evidence"] == "test"

    def test_no_declarado(self):
        # "ninguna" is a sentinel, so _clean() maps it to None
        result = _parse_level("No declarado — Evidencia: ninguna", "TRL")
        assert result["level"] is None
        assert result["evidence"] is None  # "ninguna" is a sentinel → None

    def test_no_declarado_sin_evidencia(self):
        result = _parse_level("No declarado", "CRL")
        assert result["level"] is None
        assert result["evidence"] is None

    def test_invalid_range(self):
        with pytest.raises(DBIParseError, match="nivel invalido"):
            _parse_level("5-6 — Evidencia: test", "TRL")

    def test_invalid_out_of_range(self):
        with pytest.raises(DBIParseError, match="nivel invalido"):
            _parse_level("12 — Evidencia: test", "TRL")

    def test_invalid_text(self):
        with pytest.raises(DBIParseError, match="nivel invalido"):
            _parse_level("alto — Evidencia: test", "TRL")


class TestParseEconomicImpact:
    """_parse_economic_impact() splits by em-dash and extracts sub-keys."""

    def test_full_impact(self):
        result = _parse_economic_impact(
            "USD 120k/año — Fuente: registro 2025 — Beneficiario: Elecmetal — Clasificación: Medio"
        )
        assert result["value"] == "USD 120k/año"
        assert result["source"] == "registro 2025"
        assert result["beneficiary"] == "Elecmetal"
        assert result["classification"] == "Medio"

    def test_impact_without_classification(self):
        result = _parse_economic_impact("USD 50k/año — Fuente: estimación")
        assert result["value"] == "USD 50k/año"
        assert result["source"] == "estimación"
        assert result["beneficiary"] is None
        assert result["classification"] is None

    def test_null_impact(self):
        assert _parse_economic_impact(None) is None
        assert _parse_economic_impact("No especificado") is None


class TestParseUncertainty:
    """_parse_uncertainty() splits 'cliente X / solucion Y / modelo Z'."""

    def test_full_uncertainty(self):
        result = _parse_uncertainty("cliente baja / solución media / modelo media")
        assert result["client"] == "baja"
        assert result["solution"] == "media"
        assert result["model"] == "media"

    def test_inverted_keywords(self):
        result = _parse_uncertainty("solucion alta / cliente baja / modelo baja")
        assert result["solution"] == "alta"
        assert result["client"] == "baja"
        assert result["model"] == "baja"

    def test_empty(self):
        result = _parse_uncertainty("")
        assert result == {"client": None, "solution": None, "model": None}


class TestParseKeyCondition:
    """_parse_key_condition() extracts content from guillemets and prefix."""

    def test_with_guillemets_and_prefix(self):
        result = _parse_key_condition(
            "«Esto funciona si las alertas anticipan la falla con al menos 24 horas»"
        )
        assert result == "las alertas anticipan la falla con al menos 24 horas"

    def test_plain_text(self):
        result = _parse_key_condition("necesita validación del área usuaria")
        assert result == "necesita validación del área usuaria"

    def test_null(self):
        assert _parse_key_condition(None) is None


class TestParseMonths:
    """_parse_months() extracts integer from horizon text."""

    def test_integer(self):
        assert _parse_months("12") == 12

    def test_with_text(self):
        assert _parse_months("12 meses") == 12

    def test_null_and_empty(self):
        assert _parse_months(None) is None
        assert _parse_months("no se") is None


class TestParseList:
    """_parse_list() splits comma-separated items and filters sentinels."""

    def test_normal_list(self):
        assert _parse_list("a.xlsx, b.jpg") == ["a.xlsx", "b.jpg"]

    def test_sentinels(self):
        assert _parse_list("Ninguno") == []
        assert _parse_list("ninguna") == []
        assert _parse_list("-") == []

    def test_empty(self):
        assert _parse_list("") == []
        assert _parse_list(None) == []


class TestSplitFields:
    """_split_fields() parses bullet lines with continuation."""

    def test_basic_fields(self):
        lines = [
            "• Problema: Los hornos fallan",
            "• TRL: 4 — Evidencia: lab test",
        ]
        result = _split_fields(lines)
        assert result["problema"] == "Los hornos fallan"
        assert "trl" in result

    def test_multiline_continuation(self):
        lines = [
            "• Descripción: Primera linea",
            "segunda linea",
            "tercera linea",
            "• TRL: 4",
        ]
        result = _split_fields(lines)
        assert "Primera linea segunda linea tercera linea" in result["descripción"]


# ═════════════════════════════════════════════════════════════════════════════
# Notification email building
# ═════════════════════════════════════════════════════════════════════════════

class TestEmailBuilding:
    """_build_email() generates correct subjects and HTML bodies."""

    def test_receipt_to_applicant(self):
        notif = {
            "notification_type": "receipt_to_applicant",
            "initiative_code": "INI-2026-005",
            "initiative_title": "Mi Iniciativa",
        }
        subject, body = _build_email(notif)
        assert "INI-2026-005" in subject
        assert "Mi Iniciativa" in body
        assert "<strong>INI-2026-005</strong>" in body
        assert "equipo de innovacion" in body.lower()

    def test_notice_to_director(self):
        notif = {
            "notification_type": "notice_to_director",
            "initiative_code": "INI-2026-010",
            "initiative_title": "Otra Iniciativa",
        }
        subject, body = _build_email(notif)
        assert "INI-2026-010" in subject
        assert "Otra Iniciativa" in body
        assert "Evaluador" in body

    def test_fallback_for_missing_code(self):
        notif = {"notification_type": "receipt_to_applicant"}
        subject, body = _build_email(notif)
        assert "---" in subject

    def test_unknown_type(self):
        notif = {"notification_type": "unknown_type"}
        subject, body = _build_email(notif)
        assert subject == "Notificacion"


# ═════════════════════════════════════════════════════════════════════════════
# Evaluator context building
# ═════════════════════════════════════════════════════════════════════════════

class TestEvaluatorContext:
    """_build_initiative_context() produces evaluator-ready input."""

    def test_minimal_initiative(self):
        initiative = {
            "id": 1,
            "title": "Test",
            "initiative_type": "interna",
            "area": "Fundición",
            "applicant_name": "Juan",
            "problem": "Problema de prueba",
            "solution": "Solución de prueba",
            "economic_impact": "USD 100k",
            "trl": 4,
            "scalability": "Interna",
            "internal_client": "Operaciones",
            "external_client": None,
            "crl": 5,
            "strategic_alignment": None,
            "internal_team": "Juan + técnico",
            "external_team": None,
            "sponsor": "Carlos",
            "estimated_duration": "8 meses",
            "main_doubt": "¿Funcionará?",
            "key_condition": "alerta con 24h",
            "value_capture": "ahorro",
            "brl": 4,
            "technical_milestones": "Piloto Q1",
            "financial_milestones": "ROI positivo",
            "return_horizon": 12,
            "dbi_extra": {
                "executive_summary": "Resumen ejecutivo de prueba.",
                "block_a_extra": {
                    "why_it_matters": "Porque es crítico",
                    "who_has_it": "El equipo",
                    "current_solution": "Manual",
                },
                "block_b_extra": {
                    "differentiator_novelty_grade": "mejora relevante",
                    "competition_grade": "identificados",
                    "trl_evidence": "Prueba mayo 2026",
                    "market_repeatability": "varios",
                },
                "block_c_extra": {
                    "crl_evidence": "Reunión abril 2026",
                    "target_client_type": "área usuaria",
                },
                "block_d_extra": {"horizon": "H2"},
                "block_e_extra": {
                    "applicant_area": "Fundición Planta Colina",
                    "support_received": "espacio en planta",
                    "other_resources": "parciales",
                },
                "block_f_extra": {
                    "brl_evidence": "Registro 2025",
                    "uncertainty": {"client": "baja", "solution": "media", "model": "media"},
                },
                "pending_blocks": [],
            },
        }

        context = _build_initiative_context(initiative)

        # Verify all sections present
        assert "Test" in context
        assert "PROBLEMA" in context
        assert "SOLUCION" in context
        assert "CLIENTE" in context
        assert "EQUIPO" in context
        assert "RIESGO" in context
        assert "HITOS" in context
        assert "ALINEAMIENTO" in context

        # Verify numeric levels
        assert "TRL: 4" in context
        assert "CRL: 5" in context
        assert "BRL: 4" in context

        # Verify dbi_extra fields
        assert "Resumen ejecutivo" in context
        assert "Por que importa" in context
        assert "Evidencia TRL" in context
        assert "Incertidumbre: cliente=baja" in context

    def test_initiative_without_extra(self):
        initiative = {
            "id": 2,
            "title": "Minimal",
            "initiative_type": "interna",
            "area": "Area",
            "applicant_name": "User",
            "problem": "P",
            "solution": "S",
            "trl": 1,
            "crl": 1,
            "brl": 1,
        }
        context = _build_initiative_context(initiative)
        assert "Minimal" in context
        assert "PROBLEMA" in context


# ═════════════════════════════════════════════════════════════════════════════
# Pagination
# ═════════════════════════════════════════════════════════════════════════════

class TestPagination:
    """Pagination utilities."""

    def test_validate_cursor(self):
        assert validate_cursor(None) is None
        assert validate_cursor("") is None
        assert validate_cursor("42") == 42
        assert validate_cursor("1") == 1
        with pytest.raises(ValueError):
            validate_cursor("abc")
        with pytest.raises(ValueError):
            validate_cursor("0")
        with pytest.raises(ValueError):
            validate_cursor("-5")

    def test_validate_limit(self):
        assert validate_limit(None) == 20
        assert validate_limit("5") == 5
        assert validate_limit("200") == 100  # clamped
        assert validate_limit("0") == 20     # invalid → default
        assert validate_limit("abc") == 20

    def test_paginated_response_has_more(self):
        resp = paginated_response(
            [{"id": 1}, {"id": 2}],
            cursor_field="id",
            limit=1,
        )
        assert resp["data"] == [{"id": 1}]
        assert resp["pagination"]["has_more"] is True
        assert resp["pagination"]["next_cursor"] == "1"
        assert resp["pagination"]["limit"] == 1

    def test_paginated_response_last_page(self):
        resp = paginated_response(
            [{"id": 1}],
            cursor_field="id",
            limit=2,
        )
        assert resp["data"] == [{"id": 1}]
        assert resp["pagination"]["has_more"] is False
        assert resp["pagination"]["next_cursor"] is None

    def test_build_sort_clause_valid(self):
        order = build_sort_clause("status", "ASC", {"id", "status", "created_at"})
        assert "ORDER BY status ASC" in order

    def test_build_sort_clause_invalid_column(self):
        order = build_sort_clause("injected; DROP TABLE", "DESC", {"id", "status"})
        assert "ORDER BY created_at DESC" in order  # falls back to default

    def test_build_sort_clause_invalid_direction(self):
        order = build_sort_clause("id", "INJECT", {"id"})
        assert "DESC" in order  # falls back to default direction
