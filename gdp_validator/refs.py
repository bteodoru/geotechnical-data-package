"""Keys and references: E05, E06."""
from __future__ import annotations

from .context import Context
from .schema import SCHEMA


def run(ctx: Context) -> None:
    for name, t in ctx.tables.items():
        spec = SCHEMA["tables"][name]
        _primary_key(ctx, t, spec)
        _foreign_keys(ctx, t, spec)
        _campaigns(ctx, t)


def _primary_key(ctx, t, spec) -> None:
    key = spec.get("primary_key")
    if not key or spec.get("strictly_increasing") in key:
        return
    seen: dict[tuple, int] = {}
    for row in t.rows:
        if not all(f in row.values for f in key):
            continue
        k = tuple(row.values[f] for f in key)
        if k in seen:
            ctx.out.add("E05", "duplicate_key", t.path, row.line, t.col(key[0]),
                        key="/".join(row.cells[f] for f in key), first_row=seen[k])
        else:
            seen[k] = row.line


def _foreign_keys(ctx, t, spec) -> None:
    for fk in spec.get("foreign_keys", []):
        [field] = fk["fields"]
        target = fk["reference"]["table"]
        [target_field] = fk["reference"]["fields"]
        target_table = ctx.tables.get(target)
        if target_table is None:
            if SCHEMA["tables"][target]["path"] in ctx.pkg.names():
                continue                      # present but unreadable: already reported
            keys = set()
        elif target_field not in target_table.usable:
            continue                          # key column unusable: already reported
        else:
            keys = {r.values[target_field] for r in target_table.rows if target_field in r.values}
        for row in t.rows:
            value = row.values.get(field)
            if value is not None and value not in keys:
                ctx.out.add("E06", "unresolved", t.path, row.line, t.col(field),
                            column=field, value=row.cells[field], table=target)


def _campaigns(ctx, t) -> None:
    fields = [f["name"] for f in SCHEMA["tables"][t.name]["fields"] if f.get("references") == "campaign"]
    for field in fields:
        for row in t.rows:
            value = row.values.get(field)
            if value is not None and value not in ctx.campaigns:
                ctx.out.add("E06", "campaign_unresolved", t.path, row.line, t.col(field), value=value)
    if t.name == "points" and len(ctx.campaigns) >= 2:
        for row in t.rows:
            if "point_id" in row.values and not row.cells.get("campaign"):
                ctx.out.add("E06", "campaign_required", t.path, row.line, t.col("campaign"),
                            point_id=row.values["point_id"], count=len(ctx.campaigns))
