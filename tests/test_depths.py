import pytest

from gdp_validator import validate
from util import append, delete, found, sub

L, S = "layers.csv", "samples.csv"
CASES = [
    (L, "F1,0.60,3.80", "F1,0.60,0.50", ("error", "E07", "top_not_above_base", L, 3, "depth_base[m]")),
    (S, "F1-P1,F1,1.50,1.80", "F1-P1,F1,1.50,1.20", ("error", "E07", "top_not_above_base", S, 2, "depth_base[m]")),
    (L, "F1,3.80,8.00", "F1,3.80,8.50", ("error", "E07", "beyond_final_depth", L, 4, "depth_base[m]")),
    ("water.csv", "struck,5.40", "struck,9.40", ("error", "E07", "beyond_final_depth", "water.csv", 2, "depth[m]")),
    (S, "F1-P3,F1,6.00,6.30", "F1-P3,F1,8.20,8.30", ("error", "E07", "beyond_final_depth", S, 4, "depth_top[m]")),
    ("cpt/tests.csv", ",0.40,", ",11.00,",
     ("error", "E07", "beyond_final_depth", "cpt/tests.csv", 2, "predrill_depth[m]")),
    (L, "F1,3.80,8.00", "F1,3.50,8.00", ("error", "E08", "overlap", L, 4, "depth_top[m]")),
    (L, "F1,3.80,8.00", "F1,4.00,8.00", ("warning", "W01", "gap", L, 4, "depth_top[m]")),
    (L, "F1,0.00,0.60", "F1,0.10,0.60", ("warning", "W01", "not_from_surface", L, 2, "depth_top[m]")),
    (L, "F1,3.80,8.00", "F1,3.80,7.50", ("warning", "W01", "not_to_final_depth", L, 4, "depth_base[m]")),
    (L, "Cl,U2", "Cl,", ("warning", "W07", "layer_without_unit", L, 4, "unit")),
]


@pytest.mark.parametrize("file,old,new,expected", CASES, ids=[f"{c[3][2]}-{c[0]}-{c[2]}" for c in CASES])
def test_case(pkg_a, file, old, new, expected):
    sub(pkg_a, file, old, new)
    assert expected in found(validate(pkg_a))


def _issues(pkg, code):
    return [i for i in validate(pkg).issues if i.code == code]


def test_beyond_final_depth_params(pkg_a):
    sub(pkg_a, L, "F1,3.80,8.00", "F1,3.80,8.50")
    [issue] = _issues(pkg_a, "E07")
    assert issue.params == {"field": "depth_base", "value": "8.50", "final_depth": "8.00", "point_id": "F1"}


def test_overlap_params(pkg_a):
    sub(pkg_a, L, "F1,3.80,8.00", "F1,3.50,8.00")
    [issue] = _issues(pkg_a, "E08")
    assert issue.params == {"top": "3.50", "base": "8.00", "other_top": "0.60", "other_base": "3.80", "other_row": "3"}


def test_cpt_beyond_final_depth(pkg_a):
    append(pkg_a, "cpt/data/CPT1.csv", "10.40,2.00,80.0,50.0,1.1\n")
    lines = len((pkg_a / "cpt/data/CPT1.csv").read_text().splitlines())
    assert ("error", "E07", "beyond_final_depth", "cpt/data/CPT1.csv", lines, "depth[m]") in found(validate(pkg_a))


def test_w06(pkg_a):
    sub(pkg_a, L, "F1,3.80,8.00", "F1,5.00,8.00")
    sub(pkg_a, S, "F1-P3,F1,6.00,6.30", "F1-P3,F1,4.00,4.30")
    report = validate(pkg_a)
    assert ("warning", "W06", "sample_outside_layers", S, 4, "depth_top[m]") in found(report)
    [issue] = [i for i in report.issues if i.code == "W06"]
    assert issue.params == {"depth": "4.15", "sample_id": "F1-P3", "point_id": "F1"}


def test_w06_final_depth(pkg_a):
    sub(pkg_a, S, "F1-P3,F1,6.00,6.30", "F1-P3,F1,8.00,")
    assert not [i for i in validate(pkg_a).issues if i.code in ("W06", "E07")]


def test_no_w01_without_layers(pkg_a):
    append(pkg_a, "points.csv", "DP1,dp,697420.00,634990.00,52.50,6.00,,,,\n")
    assert validate(pkg_a).issues == []


def test_w01_skips_point_with_bad_row(pkg_a):
    sub(pkg_a, L, "F1,0.60,3.80", "F1,0,60,3.80")
    assert not [i for i in validate(pkg_a).issues if i.code in ("W01", "E08")]


def test_bad_depth_no_cascade(pkg_a):
    sub(pkg_a, L, "F1,0.60,3.80", "F1,0.6O,3.80")
    assert [(i.code, i.check) for i in validate(pkg_a).issues if i.path == L] == [("E04", "bad_value")]


def test_no_w07_without_units(pkg_a):
    delete(pkg_a, "units.csv")
    sub(pkg_a, L, "Cl,U2", "Cl,")
    assert not _issues(pkg_a, "W07")
