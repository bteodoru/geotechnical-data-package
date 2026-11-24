"""lab_index rows: E10 wL_below_wP, W04."""
from __future__ import annotations

from .context import Context

FRACTIONS = ("clay", "silt", "sand", "gravel")


def run(ctx: Context) -> None:
    t = ctx.tables.get("lab_index")
    if t is None:
        return
    for row in t.rows:
        v = row.values
        if "wL" in v and "wP" in v and v["wL"] < v["wP"]:
            ctx.out.add("E10", "wL_below_wP", t.path, row.line, t.col("wL"), wL=row.cells["wL"], wP=row.cells["wP"])
        if not row.ok or not any(f in v for f in FRACTIONS):
            continue
        total = sum(v.get(f, 0.0) for f in FRACTIONS)
        if abs(total - 100) > 1:
            ctx.out.add("W04", "fractions_sum", t.path, row.line, "", sum=format(round(total, 6), "g"))
