"""Tests del parser del DBI contra el golden fixture (paso 7).

Ver docs/context/references/dbi-template.md > Golden fixture.
"""

import json
from pathlib import Path

import pytest

from app.services.dbi_parser import DBIParseError, parse_dbi

FIXTURES = Path(__file__).parent / "fixtures" / "dbi"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_golden_internal_matches_expected():
    raw = _read("example_internal.txt")
    expected = json.loads(_read("example_internal.expected.json"))
    assert parse_dbi(raw) == expected


def test_levels_are_normalized_to_int():
    parsed = parse_dbi(_read("example_internal.txt"))
    assert parsed["block_b_solution"]["trl"]["level"] == 4
    assert parsed["block_c_client"]["crl"]["level"] == 5
    assert parsed["block_f_risk"]["brl"]["level"] == 4


def test_sentinels_become_null():
    parsed = parse_dbi(_read("example_internal.txt"))
    assert parsed["block_c_client"]["external_client"] is None  # "No aplica"
    assert parsed["block_d_alignment"]["focus"] is None         # "por asignar"


def test_pending_blocks_detected_empty():
    parsed = parse_dbi(_read("example_internal.txt"))
    assert parsed["pending_blocks"] == []
    assert parsed["attached_evidence"] == [
        "registro_paradas_2025.xlsx",
        "foto_banco_sensores.jpg",
    ]


def test_invalid_trl_level_raises():
    raw = _read("example_internal.txt").replace("• TRL: 4", "• TRL: 12")
    with pytest.raises(DBIParseError):
        parse_dbi(raw)


def test_band_trl_is_rejected():
    raw = _read("example_internal.txt").replace("• TRL: 4", "• TRL: 5-6")
    with pytest.raises(DBIParseError):
        parse_dbi(raw)


def test_missing_borders_raises():
    with pytest.raises(DBIParseError):
        parse_dbi("DOCUMENTO BASE DE INICIATIVA\nA. PROBLEMA\n\u2022 Problema: x")


def test_missing_required_block_raises():
    raw = _read("example_internal.txt").replace("C. CLIENTE", "X. OTRO")
    with pytest.raises(DBIParseError):
        parse_dbi(raw)
