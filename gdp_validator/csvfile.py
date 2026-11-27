"""CSV dialects of GDP tables (schema "csv"): detected per file from the header row."""
from __future__ import annotations

import csv
import io
import re

from .schema import SCHEMA

DIALECTS: list[dict] = SCHEMA["csv"]["dialects"]
NUMBER_RE = {
    d["decimal"]: re.compile(r"^[+-]?(\d+{0}?\d*|{0}\d+)([eE][+-]?\d+)?$".format(re.escape(d["decimal"])))
    for d in DIALECTS
}


def dialect(text: str) -> dict:
    """The dialect whose delimiter is the only one present in the header row; otherwise the first."""
    header = text.split("\n", 1)[0]
    present = [d for d in DIALECTS if d["delimiter"] in header]
    return present[0] if len(present) == 1 else DIALECTS[0]


def records(text: str) -> tuple[dict, list[tuple[int, list[str]]]]:
    """The file's dialect and its records, each with the line number where it ends. Raises csv.Error."""
    d = dialect(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=d["delimiter"])
    return d, [(reader.line_num, rec) for rec in reader]


def parse_number(raw: str, decimal: str) -> float:
    """A number written with the given decimal mark; raises ValueError otherwise."""
    if not NUMBER_RE[decimal].match(raw):
        raise ValueError(raw)
    return float(raw.replace(decimal, "."))


def other_decimal(raw: str, decimal: str) -> bool:
    """True when raw is a number written with another dialect's decimal mark."""
    return any(rx.match(raw) for mark, rx in NUMBER_RE.items() if mark != decimal)
