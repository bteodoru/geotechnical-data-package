import shutil

from gdp_validator import validate
from util import delete, found, sub, write

T, D = "cpt/tests.csv", "cpt/data/CPT1.csv"


def test_data_file_missing(pkg_a):
    delete(pkg_a, D)
    report = validate(pkg_a)
    assert ("error", "E09", "data_file_missing", T, 2, "test_id") in found(report)
    [issue] = [i for i in report.issues if i.code == "E09"]
    assert issue.message == "test CPT1 has no file cpt/data/CPT1.csv"


def test_orphan_data_file(pkg_a):
    shutil.copy(pkg_a / D, pkg_a / "cpt/data/CPT2.csv")
    assert ("error", "E09", "orphan_data_file", "cpt/data/CPT2.csv", None, "") in found(validate(pkg_a))


def test_not_increasing(pkg_a):
    sub(pkg_a, D, "0.44,1.80,", "0.42,1.80,")
    report = validate(pkg_a)
    assert ("error", "E09", "not_increasing", D, 3, "depth[m]") in found(report)
    [issue] = [i for i in report.issues if i.code == "E09"]
    assert issue.params == {"depth": "0.42", "previous": "0.42"}
    assert not [i for i in report.issues if i.code == "E05"]


def test_area_ratio_required_with_u(pkg_a):
    sub(pkg_a, T, ",0.80,u2,", ",,u2,")
    assert ("error", "E04", "required_empty", T, 2, "area_ratio") in found(validate(pkg_a))
    assert ("missing", "E04", "required_empty", T, 2, "area_ratio") in found(validate(pkg_a, draft=True))


def test_filter_position_required_with_u(pkg_a):
    sub(pkg_a, T, ",0.80,u2,", ",0.80,,")
    assert ("error", "E04", "required_empty", T, 2, "filter_position") in found(validate(pkg_a))


def test_not_required_without_u(pkg_a):
    write(pkg_a, D, "depth[m],qc[MPa],fs[kPa]\n0.42,1.82,60.0\n0.44,1.80,60.0\n")
    sub(pkg_a, T, ",0.80,u2,", ",,,")
    assert not [i for i in validate(pkg_a).issues if i.path == T]
