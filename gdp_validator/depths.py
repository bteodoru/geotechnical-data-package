"""Depths and layering: E07, E08, W01, W06, W07."""
from __future__ import annotations

from collections import defaultdict

from .context import Context, Row

DEPTH_FIELDS = {
    "layers": ["depth_top", "depth_base"],
    "samples": ["depth_top", "depth_base"],
    "water": ["depth"],
    "cpt_tests": ["predrill_depth"],
}


def _valid_interval(row: Row) -> bool:
    v = row.values
    return row.ok and "depth_top" in v and "depth_base" in v and v["depth_base"] > v["depth_top"]


def layer_of(layers: list[Row], depth: float, final_depth: float | None) -> Row | None:
    """Layer containing `depth`: [top, base), the last layer also includes base = final_depth."""
    valid = [r for r in layers if _valid_interval(r)]
    if not valid:
        return None
    last = max(valid, key=lambda r: r.values["depth_base"])
    for r in valid:
        if r.values["depth_top"] <= depth < r.values["depth_base"]:
            return r
    if final_depth is not None and depth == last.values["depth_base"] == final_depth:
        return last
    return None


def run(ctx: Context) -> None:
    _intervals(ctx)
    _final_depth(ctx)
    layers_by_point = _layers_by_point(ctx)
    for point_id, rows in layers_by_point.items():
        _overlaps(ctx, rows)
        _coverage(ctx, point_id, rows)
    _samples_in_layers(ctx, layers_by_point)
    _units(ctx)


def _point(ctx: Context, point_id) -> Row | None:
    return None if point_id is None else ctx.row_by_key("points", "point_id", point_id)


def _intervals(ctx: Context) -> None:
    for name in ("layers", "samples"):
        t = ctx.tables.get(name)
        if t is None:
            continue
        for row in t.rows:
            v = row.values
            if "depth_top" in v and "depth_base" in v and v["depth_base"] <= v["depth_top"]:
                ctx.out.add("E07", "top_not_above_base", t.path, row.line, t.col("depth_base"),
                            base=row.cells["depth_base"], top=row.cells["depth_top"])


def _beyond(ctx, t, row, field, point_row) -> bool:
    if point_row is None or "final_depth" not in point_row.values or field not in row.values:
        return False
    if row.values[field] > point_row.values["final_depth"]:
        ctx.out.add("E07", "beyond_final_depth", t.path, row.line, t.col(field), field=field,
                    value=row.cells[field], final_depth=point_row.cells["final_depth"],
                    point_id=point_row.cells["point_id"])
        return True
    return False


def _final_depth(ctx: Context) -> None:
    for name, fields in DEPTH_FIELDS.items():
        t = ctx.tables.get(name)
        for row in (t.rows if t else []):
            point_row = _point(ctx, row.values.get("point_id"))
            for field in fields:
                _beyond(ctx, t, row, field, point_row)
    for test_id, t in ctx.cpt_data.items():
        test = ctx.row_by_key("cpt_tests", "test_id", test_id)
        point_row = _point(ctx, test.values.get("point_id")) if test else None
        for row in t.rows:                 # one issue per series: a wrong final_depth is one fact
            if _beyond(ctx, t, row, "depth", point_row):
                break


def _layers_by_point(ctx: Context) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = defaultdict(list)
    t = ctx.tables.get("layers")
    for row in (t.rows if t else []):
        if row.cells.get("point_id"):
            out[row.cells["point_id"]].append(row)
    return out


def _overlaps(ctx: Context, rows: list[Row]) -> None:
    t = ctx.tables["layers"]
    deepest = None
    for row in sorted((r for r in rows if _valid_interval(r)), key=lambda r: (r.values["depth_top"], r.line)):
        if deepest is not None and row.values["depth_top"] < deepest.values["depth_base"]:
            ctx.out.add("E08", "overlap", t.path, row.line, t.col("depth_top"),
                        top=row.cells["depth_top"], base=row.cells["depth_base"],
                        other_top=deepest.cells["depth_top"], other_base=deepest.cells["depth_base"],
                        other_row=deepest.line)
        if deepest is None or row.values["depth_base"] > deepest.values["depth_base"]:
            deepest = row


def _all_valid(rows: list[Row]) -> bool:
    return bool(rows) and all(_valid_interval(r) for r in rows)


def _coverage(ctx: Context, point_id: str, rows: list[Row]) -> None:
    if not _all_valid(rows):
        return
    t = ctx.tables["layers"]
    ordered = sorted(rows, key=lambda r: (r.values["depth_top"], r.line))
    first = ordered[0]
    if first.values["depth_top"] > 0:
        ctx.out.add("W01", "not_from_surface", t.path, first.line, t.col("depth_top"),
                    point_id=point_id, top=first.cells["depth_top"])
    deepest = first
    for row in ordered[1:]:
        if deepest.values["depth_base"] < row.values["depth_top"]:
            ctx.out.add("W01", "gap", t.path, row.line, t.col("depth_top"),
                        base=deepest.cells["depth_base"], next_top=row.cells["depth_top"], point_id=point_id)
        if row.values["depth_base"] > deepest.values["depth_base"]:
            deepest = row
    point_row = _point(ctx, point_id)
    if point_row is not None and "final_depth" in point_row.values \
            and deepest.values["depth_base"] < point_row.values["final_depth"]:
        ctx.out.add("W01", "not_to_final_depth", t.path, deepest.line, t.col("depth_base"),
                    point_id=point_id, base=deepest.cells["depth_base"], final_depth=point_row.cells["final_depth"])


def _samples_in_layers(ctx: Context, layers_by_point: dict[str, list[Row]]) -> None:
    t = ctx.tables.get("samples")
    for row in (t.rows if t else []):
        v = row.values
        layers = layers_by_point.get(v.get("point_id"), [])
        if "depth_top" not in v or not _all_valid(layers):
            continue
        ref = v["depth_top"] if v.get("depth_base") is None else (v["depth_top"] + v["depth_base"]) / 2
        point_row = _point(ctx, v["point_id"])
        final = point_row.values.get("final_depth") if point_row else None
        if final is not None and ref > final:
            continue                      # already E07 beyond_final_depth
        if layer_of(layers, ref, final) is None:
            ctx.out.add("W06", "sample_outside_layers", t.path, row.line, t.col("depth_top"),
                        depth=format(ref, "g"), sample_id=row.cells.get("sample_id", ""), point_id=v["point_id"])


def _units(ctx: Context) -> None:
    t = ctx.tables.get("layers")
    if t is None or "units" not in ctx.tables:
        return
    for row in t.rows:
        if row.ok and not row.cells.get("unit"):
            ctx.out.add("W07", "layer_without_unit", t.path, row.line, t.col("unit"))
