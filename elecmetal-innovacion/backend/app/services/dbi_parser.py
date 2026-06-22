"""Parser deterministico del Documento Base de Iniciativa (DBI) v5.9.

Convierte el texto generado por Clara (plantilla v5.9) en una estructura
normalizada por bloque. Contrato y delimitadores documentados en
`docs/context/references/dbi-template.md`. El parseo es todo-o-nada: si faltan
anclas estructurales (bordes, bloques A/B/C) o un nivel TRL/CRL/BRL es invalido,
se levanta `DBIParseError` y no se persiste nada.
"""

from __future__ import annotations

import re
from datetime import datetime

BULLET = "\u2022"   # •
EMDASH = "\u2014"   # —
BORDER = "\u2550"   # ═
OPEN_Q = "\u00ab"   # «
CLOSE_Q = "\u00bb"  # »

# Valores que indican ausencia, no contenido (ver dbi-template.md > Centinelas).
SENTINELS = {
    "no especificado", "no aplica", "no definido", "no declarado",
    "no estimado", "por asignar", "por definir",
    "sin patrocinador identificado", "ninguno", "ninguna",
}
EMPTY_LIST_TOKENS = {"ninguno", "ninguna", "", "-"}

_META_RE = re.compile(
    r"Título:\s*(?P<title>.+?)\s*\|\s*"
    r"Fecha:\s*(?P<date>.+?)\s*\|\s*"
    r"Área:\s*(?P<area>.+?)\s*\|\s*"
    r"Postulante:\s*(?P<name>.+)"
)
_BLOCK_RE = re.compile(r"^([A-G])\.\s+(.+)$")
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y")


class DBIParseError(ValueError):
    """El texto no respeta el contrato de la plantilla DBI v5.9."""


# --------------------------------------------------------------------------- #
# Helpers de limpieza y conversion
# --------------------------------------------------------------------------- #
def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v.lower() in SENTINELS:
        return None
    return v


def _is_border(line: str) -> bool:
    s = line.strip()
    return len(s) >= 3 and set(s) == {BORDER}


def _parse_date(raw: str) -> str | None:
    v = raw.strip()
    if not v:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return v


def _parse_months(raw: str | None) -> int | None:
    if raw is None:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def _parse_list(raw: str | None) -> list[str]:
    v = (raw or "").strip()
    if v.lower() in EMPTY_LIST_TOKENS:
        return []
    return [item.strip() for item in v.split(",") if item.strip()]


def _parse_level(raw: str | None, field: str) -> dict:
    """Parsea 'N — Evidencia: ...' → {level: int|None, evidence: str|None}."""
    if raw is None or not raw.strip():
        return {"level": None, "evidence": None}
    parts = raw.split(EMDASH, 1)
    level_str = parts[0].strip()
    evidence = None
    if len(parts) > 1:
        tail = parts[1].strip()
        _, _, ev = tail.partition(":")
        evidence = _clean(ev if ev else tail)
    if level_str.lower() in {"no declarado", "no aplica", ""}:
        return {"level": None, "evidence": evidence}
    if not re.fullmatch(r"[1-9]", level_str):
        raise DBIParseError(
            f"{field}: nivel invalido '{level_str}' (debe ser un entero 1-9, no banda)"
        )
    return {"level": int(level_str), "evidence": evidence}


def _parse_graded(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    parts = raw.split(EMDASH, 1)
    grade = _clean(parts[0])
    text = _clean(parts[1]) if len(parts) > 1 else None
    return grade, text


def _parse_economic_impact(raw: str | None) -> dict | None:
    if _clean(raw) is None:
        return None
    parts = [p.strip() for p in raw.split(EMDASH)]
    result = {"value": _clean(parts[0]), "source": None,
              "beneficiary": None, "classification": None}
    keymap = {
        "fuente": "source",
        "beneficiario": "beneficiary",
        "clasificación": "classification", "clasificacion": "classification",
    }
    for part in parts[1:]:
        key, _, val = part.partition(":")
        mapped = keymap.get(key.strip().lower())
        if mapped:
            result[mapped] = _clean(val)
    return result


def _parse_market_size(raw: str | None) -> dict | None:
    if _clean(raw) is None:
        return None
    factors = [f.strip() for f in raw.split("/") if f.strip()]
    return {"factors": factors}


def _parse_uncertainty(raw: str | None) -> dict:
    result = {"client": None, "solution": None, "model": None}
    keymap = {
        "cliente": "client",
        "solución": "solution", "solucion": "solution",
        "modelo": "model",
    }
    for frag in (raw or "").split("/"):
        m = re.match(r"\s*(\w+)\s+(.+)", frag)
        if m:
            mapped = keymap.get(m.group(1).lower())
            if mapped:
                result[mapped] = _clean(m.group(2))
    return result


def _parse_key_condition(raw: str | None) -> str | None:
    v = (raw or "").strip()
    if v.startswith(OPEN_Q) and v.endswith(CLOSE_Q):
        v = v[1:-1].strip()
    m = re.match(r"(?i)esto funciona si\s+(.*)", v)
    if m:
        v = m.group(1).strip()
    return _clean(v)


def _split_fields(block_lines: list[str]) -> dict[str, str]:
    """Lineas '• Label: value' → {label_normalizado: value}, con continuacion."""
    fields: dict[str, str] = {}
    current: str | None = None
    for line in block_lines:
        s = line.strip()
        if s.startswith(BULLET):
            body = s[len(BULLET):].strip()
            if ":" not in body:
                current = None
                continue
            label, _, value = body.partition(":")
            current = label.strip().lower()
            fields[current] = value.strip()
        elif current and s:
            fields[current] += " " + s
    return fields


def _get(fields: dict[str, str], *keys: str) -> str | None:
    for k in keys:
        if k in fields:
            return fields[k]
    return None


# --------------------------------------------------------------------------- #
# Parser principal
# --------------------------------------------------------------------------- #
def parse_dbi(text: str) -> dict:
    lines = text.splitlines()
    borders = [i for i, ln in enumerate(lines) if _is_border(ln)]
    if len(borders) < 2:
        raise DBIParseError("Faltan las lineas de borde '═' que delimitan el DBI")

    header_lines = lines[borders[0] + 1: borders[1]]
    body_lines = lines[borders[1] + 1:]
    inner_borders = [i for i, ln in enumerate(body_lines) if _is_border(ln)]
    if inner_borders:
        body_lines = body_lines[: inner_borders[-1]]

    header = _parse_header(header_lines)
    executive_summary, blocks, attached_raw, pending_raw = _parse_body(body_lines)

    for required in ("A", "B", "C"):
        if required not in blocks:
            raise DBIParseError(f"Falta el bloque obligatorio '{required}'")

    fa = _split_fields(blocks.get("A", []))
    fb = _split_fields(blocks.get("B", []))
    fc = _split_fields(blocks.get("C", []))
    fd = _split_fields(blocks.get("D", []))
    fe = _split_fields(blocks.get("E", []))
    ff = _split_fields(blocks.get("F", []))
    fg = _split_fields(blocks.get("G", []))

    dif_grade, dif_text = _parse_graded(_get(fb, "diferenciador y grado de novedad"))
    comp_grade, comp_text = _parse_graded(_get(fb, "competencia / sustitutos"))
    market_key = next((k for k in fb if k.startswith("tamaño de mercado")), None)

    return {
        "header": header,
        "executive_summary": _clean(executive_summary),
        "block_a_problem": {
            "problem": _clean(_get(fa, "problema")),
            "why_it_matters": _clean(_get(fa, "por qué importa", "por que importa")),
            "who_has_it": _clean(_get(fa, "quién lo tiene", "quien lo tiene")),
            "current_solution": _clean(_get(fa, "cómo se resuelve hoy", "como se resuelve hoy")),
        },
        "block_b_solution": {
            "description": _clean(_get(fb, "descripción", "descripcion")),
            "differentiator_novelty_grade": dif_grade,
            "differentiator_text": dif_text,
            "competition_grade": comp_grade,
            "competition_text": comp_text,
            "economic_impact": _parse_economic_impact(_get(fb, "impacto económico", "impacto economico")),
            "market_size": _parse_market_size(fb[market_key]) if market_key else None,
            "trl": _parse_level(_get(fb, "trl"), "TRL"),
            "scalability": _clean(_get(fb, "escalabilidad")),
            "market_repeatability": _clean(_get(fb, "mercado / repetibilidad")),
        },
        "block_c_client": {
            "internal_client": _clean(_get(fc, "interno")),
            "external_client": _clean(_get(fc, "externo")),
            "target_client_type": _clean(_get(fc, "tipo de cliente objetivo")),
            "crl": _parse_level(_get(fc, "crl"), "CRL"),
        },
        "block_d_alignment": {
            "focus": _clean(_get(fd, "foco")),
            "horizon": _clean(_get(fd, "horizonte")),
        },
        "block_e_team": {
            "applicant_area": _clean(_get(fe, "área del postulante", "area del postulante")),
            "internal_team": _clean(_get(fe, "equipo interno")),
            "external_team": _clean(_get(fe, "equipo externo")),
            "sponsor": _clean(_get(fe, "patrocinador")),
            "support_received": _clean(_get(fe, "apoyo recibido")),
            "other_resources": _clean(_get(fe, "otros recursos necesarios")),
            "estimated_duration": _clean(_get(fe, "duración estimada", "duracion estimada")),
        },
        "block_f_risk": {
            "main_doubt": _clean(_get(ff, "duda principal")),
            "key_condition": _parse_key_condition(_get(ff, "condición clave", "condicion clave")),
            "value_capture": _clean(_get(ff, "captura de valor")),
            "uncertainty": _parse_uncertainty(_get(ff, "incertidumbre")),
            "brl": _parse_level(_get(ff, "brl"), "BRL"),
        },
        "block_g_milestones": {
            "technical_milestones": _clean(_get(fg, "técnicos/operativos", "tecnicos/operativos")),
            "financial_milestones": _clean(_get(fg, "económicos/financieros", "economicos/financieros")),
            "return_horizon_months": _parse_months(_get(fg, "horizonte de retorno")),
        },
        "attached_evidence": _parse_list(attached_raw),
        "pending_blocks": _parse_list(pending_raw),
    }


def _parse_header(header_lines: list[str]) -> dict:
    title = date = area = name = tipo = None
    for line in header_lines:
        s = line.strip()
        m = _META_RE.search(s)
        if m:
            title = _clean(m.group("title"))
            date = _parse_date(m.group("date"))
            area = _clean(m.group("area"))
            name = _clean(m.group("name"))
        elif s.lower().startswith("tipo:"):
            tipo = s.split(":", 1)[1].strip()
    if title is None:
        raise DBIParseError(
            "Encabezado: falta la linea de metadatos (Título | Fecha | Área | Postulante)"
        )
    return {
        "title": title,
        "postulation_date": date,
        "area": area,
        "applicant_name": name,
        "initiative_type": tipo.lower() if tipo else None,
    }


def _parse_body(body_lines: list[str]):
    executive_summary: str | None = None
    attached_raw: str | None = None
    pending_raw: str | None = None
    blocks: dict[str, list[str]] = {}
    current: str | None = None

    i, n = 0, len(body_lines)
    while i < n:
        raw = body_lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue

        block_match = _BLOCK_RE.match(s)
        if block_match:
            current = block_match.group(1)
            blocks[current] = []
            i += 1
            continue

        upper = s.upper()
        if upper.startswith("RESUMEN EJECUTIVO:"):
            current = None
            executive_summary = s.split(":", 1)[1].strip()
            j = i + 1
            while j < n:
                nxt = body_lines[j].strip()
                if not nxt or nxt.startswith(BULLET) or _BLOCK_RE.match(nxt):
                    break
                executive_summary += " " + nxt
                j += 1
            i = j
            continue
        if upper.startswith("EVIDENCIA ADJUNTA:"):
            current = None
            attached_raw = s.split(":", 1)[1].strip()
            i += 1
            continue
        if upper.startswith("BLOQUES PENDIENTES:"):
            current = None
            pending_raw = s.split(":", 1)[1].strip()
            i += 1
            continue

        if current:
            blocks[current].append(raw)
        i += 1

    return executive_summary, blocks, attached_raw, pending_raw
