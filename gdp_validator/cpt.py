"""CPT tests and series: E09, required_if (E04)."""
from __future__ import annotations

from .context import Context
from .schema import SCHEMA

TESTS_PATH = SCHEMA["tables"]["cpt_tests"]["path"]
REQUIRED_IF = [(f["name"], f["required_if"]["data_column"])
               for f in SCHEMA["tables"]["cpt_tests"]["fields"] if "required_if" in f]


def run(ctx: Context) -> None:
    names = set(ctx.pkg.names())
    tests = ctx.tables.get("cpt_tests")
    if tests is None and TESTS_PATH in names:
        test_ids = None                       # unreadable: already reported
    else:
        test_ids = {r.values["test_id"] for r in (tests.rows if tests else []) if "test_id" in r.values}

    for row in (tests.rows if tests else []):
        test_id = row.values.get("test_id")
        if test_id is None:
            continue
        path = f"cpt/data/{test_id}.csv"
        if test_id not in ctx.cpt_data and path not in names:
            ctx.out.add("E09", "data_file_missing", tests.path, row.line, tests.col("test_id"), test_id=test_id)
        data = ctx.cpt_data.get(test_id)
        for field, data_column in REQUIRED_IF:
            if data is None or data_column not in data.usable:
                continue
            if field in tests.header and field not in tests.usable:
                continue                      # wrong unit: already reported
            if not row.cells.get(field):
                ctx.out.add("E04", "required_empty", tests.path, row.line, tests.col(field), column=field)

    for test_id, t in ctx.cpt_data.items():
        if test_ids is not None and test_id not in test_ids:
            ctx.out.add("E09", "orphan_data_file", t.path, None, "", test_id=test_id)
        deepest = None
        for row in t.rows:
            if "depth" not in row.values:
                continue
            if deepest is not None and row.values["depth"] <= deepest.values["depth"]:
                ctx.out.add("E09", "not_increasing", t.path, row.line, t.col("depth"),
                            depth=row.cells["depth"], previous=deepest.cells["depth"])
            else:
                deepest = row
