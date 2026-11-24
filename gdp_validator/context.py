"""State shared by the validation phases."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .package import Package
from .report import Collector
from .schema import SCHEMA


@dataclass
class Row:
    line: int
    cells: dict[str, str]
    values: dict[str, Any]
    ok: bool = True


@dataclass
class Table:
    name: str
    path: str
    header: dict[str, str]          # canonical field name -> header cell as written
    rows: list[Row]
    usable: set[str]

    def col(self, name: str) -> str:
        if name in self.header:
            return self.header[name]
        return canonical_header(self.name, name)


def canonical_header(table: str, name: str) -> str:
    for f in SCHEMA["tables"][table]["fields"]:
        if f["name"] == name:
            return f"{name}[{f['unit']}]" if f.get("unit") else name
    return name


@dataclass
class Context:
    pkg: Package
    out: Collector
    accept_newer: bool = False
    manifest: dict | None = None
    campaigns: dict[str, dict | None] = field(default_factory=dict)
    tables: dict[str, Table] = field(default_factory=dict)
    cpt_data: dict[str, Table] = field(default_factory=dict)
