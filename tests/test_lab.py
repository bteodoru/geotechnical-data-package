import pytest

from gdp_validator import validate
from util import found, sub

LAB = "lab/index.csv"


def test_wl_below_wp(pkg_a):
    sub(pkg_a, LAB, "F1-P1,19.8,38,21", "F1-P1,19.8,18,21")
    report = validate(pkg_a)
    assert ("error", "E10", "wL_below_wP", LAB, 2, "wL[%]") in found(report)
    [issue] = [i for i in report.issues if i.check == "wL_below_wP"]
    assert issue.message == "wL (18) < wP (21)"


def test_fractions_sum(pkg_a):
    sub(pkg_a, LAB, ",28,58,14,0,", ",28,58,10,0,")
    assert ("warning", "W04", "fractions_sum", LAB, 2, "") in found(validate(pkg_a))


@pytest.mark.parametrize("new,expected", [(",28,58,14.8,0,", None), (",,,,,", None), (",28,58,,,", "86")])
def test_w04_tolerance(pkg_a, new, expected):
    sub(pkg_a, LAB, ",28,58,14,0,", new)
    sums = [i.params["sum"] for i in validate(pkg_a).issues if i.code == "W04"]
    assert sums == ([] if expected is None else [expected])
