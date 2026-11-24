"""The GDP schema, locale files and message rendering."""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "gdp-0.1.schema.json"
SCHEMA: dict = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VERSION: str = SCHEMA["version"]

_RULES = {r["code"]: r for r in SCHEMA["rules"]}


def rule_level(code: str) -> str:
    return _RULES[code]["level"]


def check_spec(code: str, check: str) -> dict:
    return _RULES[code]["checks"][check]


def load_locale(lang: str) -> dict:
    path = SCHEMA_PATH.parent / "locales" / f"gdp-{VERSION}.{lang}.json"
    if not path.is_file():
        raise ValueError(f"no locale file for language {lang!r} ({path.name})")
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


def template(code: str, check: str, locale: dict | None) -> str:
    entry = (locale or {}).get(f"rules.{code}.checks.{check}") or {}
    return entry.get("message") or check_spec(code, check)["message"]


def render(code: str, check: str, params: dict[str, str], locale: dict | None) -> str:
    return template(code, check, locale).format_map(params)
