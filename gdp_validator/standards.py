"""Campaign declarations against the data: E11 standard_missing, fractions_missing."""
from __future__ import annotations

from collections import defaultdict

from .context import Context
from .documents import FRACTIONS_REGISTRY, TESTS
from .schema import SCHEMA

LAB_TESTS = {f["name"]: f["test"] for f in SCHEMA["tables"]["lab_index"]["fields"] if "test" in f}


def tests_with_data(ctx: Context) -> dict[str, set[str]]:
    """campaign id -> test keys that have data in rows of that campaign."""
    out: dict[str, set[str]] = defaultdict(set)
    lab = ctx.tables.get("lab_index")
    for row in (lab.rows if lab else []):
        campaign = ctx.sample_campaign(row.values["sample_id"]) if "sample_id" in row.values else None
        if campaign:
            out[campaign] |= {test for field, test in LAB_TESTS.items() if field in row.values}
    cpt = ctx.tables.get("cpt_tests")
    for row in (cpt.rows if cpt else []):
        campaign = ctx.point_campaign(row.values["point_id"]) if "point_id" in row.values else None
        if campaign:
            out[campaign].add("cpt")
    return out


def run(ctx: Context) -> None:
    for campaign, tests in sorted(tests_with_data(ctx).items()):
        doc = ctx.campaigns.get(campaign)
        if doc is None:
            continue
        path = f"campaigns/{campaign}.toml"
        standards = doc.get("standards", {})
        if isinstance(standards, dict):
            for test in sorted(tests - set(standards)):
                ctx.out.add("E11", "standard_missing", path, None, f"standards.{test}",
                            allowed=[TESTS[test]["reference_standard"], "unknown"], test=test, campaign=campaign)
        if "grain_size" in tests and "fractions" not in doc:
            ctx.out.add("E11", "fractions_missing", path, None, "fractions.source",
                        allowed=list(FRACTIONS_REGISTRY) + ["custom"], campaign=campaign)
