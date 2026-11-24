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
    _index: dict = field(default_factory=dict, repr=False)

    def row_by_key(self, table: str, key_field: str, value) -> Row | None:
        """First row of `table` whose parsed `key_field` equals `value`."""
        k = (table, key_field)
        if k not in self._index:
            t = self.tables.get(table)
            idx: dict = {}
            for r in (t.rows if t else []):
                if key_field in r.values:
                    idx.setdefault(r.values[key_field], r)
            self._index[k] = idx
        return self._index[k].get(value)

    def _campaign_or_single(self, value) -> str | None:
        if value is not None:
            return value if value in self.campaigns else None
        return next(iter(self.campaigns)) if len(self.campaigns) == 1 else None

    def point_campaign(self, point_id: str) -> str | None:
        """Effective campaign of a point: points.campaign ?? the only campaign."""
        row = self.row_by_key("points", "point_id", point_id)
        return None if row is None else self._campaign_or_single(row.values.get("campaign"))

    def sample_campaign(self, sample_id: str) -> str | None:
        """Derivation sample_campaign: samples.campaign ?? points.campaign ?? the only campaign."""
        row = self.row_by_key("samples", "sample_id", sample_id)
        if row is None:
            return None
        if row.values.get("campaign") is not None:
            return self._campaign_or_single(row.values["campaign"])
        point = row.values.get("point_id")
        return None if point is None else self.point_campaign(point)
