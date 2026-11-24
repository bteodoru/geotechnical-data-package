import pytest

from gdp_validator import documents, tables
from gdp_validator.context import Context
from gdp_validator.package import Package
from gdp_validator.report import Collector
from gdp_validator import validate
from util import found, sub, write

CASES = [
    ("pkg_a", "samples.csv", "F1-P2,F1,3.00", "F1-P1,F1,3.00",
     ("error", "E05", "duplicate_key", "samples.csv", 3, "sample_id")),
    ("pkg_a", "layers.csv", "F1,0.60,3.80", "F1,0.00,3.80", ("error", "E05", "duplicate_key", "layers.csv", 3, "point_id")),
    ("pkg_a", "layers.csv", "CPT1,0.00,0.60", "CPT9,0.00,0.60", ("error", "E06", "unresolved", "layers.csv", 5, "point_id")),
    ("pkg_a", "layers.csv", "siCl,U1", "siCl,U7", ("error", "E06", "unresolved", "layers.csv", 3, "unit")),
    ("pkg_a", "lab/index.csv", "F1-P3,27.1", "F1-P9,27.1",
     ("error", "E06", "unresolved", "lab/index.csv", 4, "sample_id")),
    ("pkg_b", "points.csv", "F1,borehole,C2016", "F1,borehole,C2015",
     ("error", "E06", "campaign_unresolved", "points.csv", 2, "campaign")),
    ("pkg_b", "points.csv", "F2,borehole,C2026", "F2,borehole,",
     ("error", "E06", "campaign_required", "points.csv", 3, "campaign")),
]


@pytest.mark.parametrize("pkg,file,old,new,expected", CASES, ids=[c[4][2] + "-" + c[2] for c in CASES])
def test_case(request, pkg, file, old, new, expected):
    p = request.getfixturevalue(pkg)
    sub(p, file, old, new)
    assert expected in found(validate(p))


def test_duplicate_key_params(pkg_a):
    sub(pkg_a, "layers.csv", "F1,0.60,3.80", "F1,0.00,3.80")
    [issue] = [i for i in validate(pkg_a).issues if i.code == "E05"]
    assert issue.params == {"key": "F1/0.00", "first_row": "2"}


def test_unresolved_message(pkg_a):
    sub(pkg_a, "layers.csv", "CPT1,0.00,0.60", "CPT9,0.00,0.60")
    [issue] = [i for i in validate(pkg_a).issues if i.code == "E06"]
    assert issue.message == "point_id CPT9 not found in points"


def test_campaign_required_draft(pkg_b):
    sub(pkg_b, "points.csv", "F2,borehole,C2026", "F2,borehole,")
    [issue] = [i for i in validate(pkg_b, draft=True).issues if i.check == "campaign_required"]
    assert issue.level == "missing" and issue.params == {"point_id": "F2", "count": "2"}


def test_sample_campaign_unresolved(pkg_b):
    write(pkg_b, "samples.csv", "sample_id,point_id,campaign,depth_top[m],depth_base[m],kind\n"
                                "F1-P1,F1,V2026,2.00,2.30,undisturbed\n"
                                "F2-P1,F2,,2.50,2.80,undisturbed\n"
                                "F2-P2,F2,,6.00,6.30,undisturbed\n")
    assert ("error", "E06", "campaign_unresolved", "samples.csv", 2, "campaign") in found(validate(pkg_b))


def _ctx(path):
    ctx = Context(pkg=Package(path), out=Collector(False, None))
    documents.run_manifest(ctx)
    documents.run_campaigns(ctx)
    tables.run(ctx)
    return ctx


def test_effective_campaign(pkg_a, pkg_b):
    b = _ctx(pkg_b)
    assert b.sample_campaign("F1-P1") == "C2016"
    assert b.sample_campaign("F2-P1") == "C2026"
    assert b.sample_campaign("nope") is None
    a = _ctx(pkg_a)
    assert a.point_campaign("CPT1") == "C2026"
    assert a.sample_campaign("F1-P1") == "C2026"
