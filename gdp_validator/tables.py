"""Table files: inventory (E02 no_points, W02 files), headers (E03, W02, E12), cells (E04, E10 codes, W03)."""
from __future__ import annotations

import csv
import datetime as dt
import io
import re

from .context import Context, Row, Table, canonical_header
from .documents import CAMPAIGN_RE, MANIFEST
from .schema import SCHEMA

HEADER_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(\[(?P<unit>[^\]]+)\])?$")
NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
INTEGER_RE = re.compile(r"^[+-]?\d+$")
CPT_DATA_RE = re.compile(r"cpt/data/([^/]+)\.csv")

TYPES = SCHEMA["types"]
VOCAB = SCHEMA["vocabularies"]
RANGES = next(r for r in SCHEMA["rules"] if r["code"] == "W03")["ranges"]
FIXED_TABLES = {name: t for name, t in SCHEMA["tables"].items() if "{" not in t["path"]}


def _ignored(name: str) -> bool:
    parts = name.split("/")
    return parts[0] in ("__MACOSX", "attachments") or any(p.startswith(".") for p in parts)


def _num(x) -> str:
    return format(x, "g")


def run(ctx: Context) -> None:
    names = [n for n in ctx.pkg.names() if not _ignored(n)]
    known = {MANIFEST} | {t["path"] for t in FIXED_TABLES.values()}
    for name in names:
        if name in known or CAMPAIGN_RE.fullmatch(name) or CPT_DATA_RE.fullmatch(name):
            continue
        ctx.out.add("W02", "unknown_file", name, file=name)

    present = set(names)
    for table, spec in FIXED_TABLES.items():
        if spec["path"] in present:
            t = read_table(ctx, table, spec["path"])
            if t is not None:
                ctx.tables[table] = t
    for name in sorted(names):
        m = CPT_DATA_RE.fullmatch(name)
        if m:
            t = read_table(ctx, "cpt_data", name)
            if t is not None:
                ctx.cpt_data[m[1]] = t

    points = ctx.tables.get("points")
    if "points.csv" not in present or (points is not None and not points.rows):
        ctx.out.add("E02", "no_points", "points.csv")


def read_table(ctx: Context, table: str, path: str) -> Table | None:
    try:
        text = ctx.pkg.read_text(path)
        reader = csv.reader(io.StringIO(text, newline=""))
        records = [(reader.line_num, rec) for rec in reader]
    except (UnicodeDecodeError, csv.Error) as exc:
        ctx.out.add("E03", "unreadable", path, detail=str(exc))
        return None

    fields = {f["name"]: f for f in SCHEMA["tables"][table]["fields"]}
    header_cells = [c.strip() for c in records[0][1]] if records else []
    keys, header, usable = _header(ctx, table, path, fields, header_cells)

    t = Table(table, path, header, [], usable)
    for line, rec in records[1:]:
        cells = [c.strip() for c in rec]
        if not any(cells):
            continue
        row = Row(line=line, cells=dict(zip(keys, cells)), values={})
        t.rows.append(row)
        if len(cells) != len(keys):
            ctx.out.add("E04", "row_length", path, line, found=len(cells), expected=len(keys))
            row.ok = False
            continue
        for name in fields:
            if name in usable:
                _cell(ctx, t, row, fields[name], row.cells.get(name, ""))
    return t


def _header(ctx, table, path, fields, cells):
    keys: list[str] = []
    header: dict[str, str] = {}
    usable: set[str] = set()
    for cell in cells:
        m = HEADER_RE.match(cell)
        if not m:
            ctx.out.add("E03", "bad_header", path, 1, cell, cell=cell)
            keys.append(cell)
            continue
        name, unit = m["name"], m["unit"] or ""
        if name.startswith("x_") or name not in fields:
            if not name.startswith("x_"):
                ctx.out.add("W02", "unknown_column", path, 1, cell, column=cell)
            keys.append(cell)
            continue
        if name in header:
            ctx.out.add("E03", "duplicate_column", path, 1, cell, name=name)
            keys.append(cell)
            continue
        keys.append(name)
        header[name] = cell
        expected = fields[name].get("unit") or ""
        if unit != expected:
            ctx.out.add("E03", "wrong_unit", path, 1, cell, name=name, found=unit, expected=expected)
        else:
            usable.add(name)
    for name, f in fields.items():
        if f.get("required") is True and name not in header:
            ctx.out.add("E03", "missing_column", path, 1, canonical_header(table, name),
                        column=canonical_header(table, name))
    for group in SCHEMA["tables"][table].get("exclusive_groups", []):
        firsts = [next((c for c in option if c in header), None) for option in group["options"]]
        firsts = [c for c in firsts if c]
        if len(firsts) > 1:
            ctx.out.add(group["rule"], "both_groups", path, 1, header[firsts[1]], first=firsts[0], second=firsts[1])
    return keys, header, usable


def _parse(ftype: str, raw: str):
    """Parsed value, or raise ValueError."""
    if ftype == "number":
        if not NUMBER_RE.match(raw):
            raise ValueError
        return float(raw)
    if ftype == "integer":
        if not INTEGER_RE.match(raw):
            raise ValueError
        return int(raw)
    if ftype == "bool":
        if raw not in ("true", "false"):
            raise ValueError
        return raw == "true"
    pattern = TYPES[ftype].get("pattern")
    if pattern and not re.match(pattern, raw):
        raise ValueError
    if ftype == "date":
        dt.date.fromisoformat(raw)
    elif ftype == "datetime":
        if dt.datetime.fromisoformat(raw).tzinfo is None:
            raise ValueError
    return raw


def _cell(ctx: Context, t: Table, row: Row, f: dict, raw: str) -> None:
    name = f["name"]
    column = t.col(name)
    if raw == "":
        if f.get("required") is True:
            ctx.out.add("E04", "required_empty", t.path, row.line, column, column=name)
            row.ok = False
        return
    try:
        value = _parse(f["type"], raw)
    except ValueError:
        ctx.out.add("E04", "bad_value", t.path, row.line, column, value=raw, type=f["type"], column=name)
        row.ok = False
        return
    if isinstance(value, float):
        lo, hi = f.get("minimum"), f.get("maximum")
        if (lo is not None and value < lo) or (hi is not None and value > hi):
            ctx.out.add("E04", "out_of_bounds", t.path, row.line, column, column=name, value=raw,
                        min="-inf" if lo is None else _num(lo), max="inf" if hi is None else _num(hi))
            row.ok = False
            return
        if name in RANGES:
            lo, hi = RANGES[name]
            if not lo <= value <= hi:
                ctx.out.add("W03", "implausible", t.path, row.line, column, column=name, value=raw,
                            min=_num(lo), max=_num(hi))
    vocab = VOCAB.get(f.get("vocabulary", ""))
    if isinstance(vocab, list) and value not in vocab:
        ctx.out.add("E10", "unknown_code", t.path, row.line, column, allowed=vocab, value=raw,
                    vocabulary=f["vocabulary"])
        row.ok = False
        return
    row.values[name] = value
