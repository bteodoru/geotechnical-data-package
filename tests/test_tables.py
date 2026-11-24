import shutil
import zipfile

import pytest

from gdp_validator import validate
from util import found, sub, write

L = "layers.csv"
CASES = [
    (L, "depth_base[m]", "depth_base[cm]", ("error", "E03", "wrong_unit", L, 1, "depth_base[cm]")),
    ("cpt/tests.csv", "area_ratio", "area_ratio[%]", ("error", "E03", "wrong_unit", "cpt/tests.csv", 1, "area_ratio[%]")),
    (L, ",unit\n", ",unit[\n", ("error", "E03", "bad_header", L, 1, "unit[")),
    ("lab/index.csv", "rho_s[Mg/m3],clay", "rho_s[Mg/m3],gamma[kN/m3],clay",
     ("error", "E12", "both_groups", "lab/index.csv", 1, "gamma[kN/m3]")),
    ("points.csv", ",remarks\n", ",remark\n", ("warning", "W02", "unknown_column", "points.csv", 1, "remark")),
    (L, "F1,0.60,3.80", "F1,0.6O,3.80", ("error", "E04", "bad_value", L, 3, "depth_top[m]")),
    (L, "F1,0.60,3.80", 'F1,"0,60",3.80', ("error", "E04", "bad_value", L, 3, "depth_top[m]")),
    (L, "F1,0.60,3.80", "F1,0,60,3.80", ("error", "E04", "row_length", L, 3, "")),
    (L, '0.60,"Sol vegetal, cafeniu-negricios",', "0.60,,", ("error", "E04", "required_empty", L, 2, "description")),
    ("samples.csv", "F1-P1,F1,1.50", "F1-P1,F1,-1.50", ("error", "E04", "out_of_bounds", "samples.csv", 2, "depth_top[m]")),
    ("cpt/tests.csv", ",0.80,", ",1.80,", ("error", "E04", "out_of_bounds", "cpt/tests.csv", 2, "area_ratio")),
    ("samples.csv", "F1-P1,F1,1.50", "F1 P1,F1,1.50", ("error", "E04", "bad_value", "samples.csv", 2, "sample_id")),
    ("points.csv", "8.00,2026-10-14", "8.00,2026-02-30", ("error", "E04", "bad_value", "points.csv", 2, "date_start")),
    ("water.csv", "T13:10+03:00", "T13:10", ("error", "E04", "bad_value", "water.csv", 2, "datetime")),
    ("points.csv", "F1,borehole", "F1,foraj", ("error", "E10", "unknown_code", "points.csv", 2, "type")),
    ("lab/index.csv", "F1-P1,19.8,", "F1-P1,198,", ("warning", "W03", "implausible", "lab/index.csv", 2, "w[%]")),
    ("cpt/data/CPT1.csv", "0.42,1.82,", "0.42,182,", ("warning", "W03", "implausible", "cpt/data/CPT1.csv", 2, "qc[MPa]")),
]


@pytest.mark.parametrize("file,old,new,expected", CASES, ids=[f"{c[3][2]}-{c[0]}-{c[2][:10]}" for c in CASES])
def test_case(pkg_a, file, old, new, expected):
    sub(pkg_a, file, old, new)
    assert expected in found(validate(pkg_a))


def _on(report, path, row=None):
    return [i for i in report.issues if i.path == path and (row is None or i.row == row)]


def test_missing_column_no_cascade(pkg_a):
    write(pkg_a, "water.csv", "point_id,depth[m]\nF1,5.40\n")
    report = validate(pkg_a)
    assert ("error", "E03", "missing_column", "water.csv", 1, "kind") in found(report)
    assert not [i for i in _on(report, "water.csv") if i.code == "E04"]
    assert ("missing", "E03", "missing_column", "water.csv", 1, "kind") in found(validate(pkg_a, draft=True))


def test_wrong_unit_no_cascade(pkg_a):
    sub(pkg_a, L, "depth_base[m]", "depth_base[cm]")
    codes = {i.code for i in _on(validate(pkg_a), L)}
    assert not codes & {"E04", "E07", "E08", "W01"}


def test_duplicate_column(pkg_a):
    write(pkg_a, "water.csv", "point_id,kind,depth[m],depth[m]\nF1,struck,5.40,5.40\n")
    assert ("error", "E03", "duplicate_column", "water.csv", 1, "depth[m]") in found(validate(pkg_a))


def test_unreadable(pkg_a):
    write(pkg_a, "units.csv", "unit_id,name\nU0,Pământ\n".encode("cp1250"))
    assert ("error", "E03", "unreadable", "units.csv", None, "") in found(validate(pkg_a))


def test_decimal_comma_quoted(pkg_a):
    sub(pkg_a, L, "F1,0.60,3.80", 'F1,"0,60",3.80')
    [issue] = _on(validate(pkg_a), L, 3)
    assert issue.check == "bad_value"
    assert issue.params == {"value": "0,60", "type": "number", "column": "depth_top"}
    assert issue.message == "0,60 is not a valid number"


def test_decimal_comma_unquoted(pkg_a):
    sub(pkg_a, L, "F1,0.60,3.80", "F1,0,60,3.80")
    [issue] = _on(validate(pkg_a), L, 3)
    assert issue.check == "row_length" and issue.params == {"found": "7", "expected": "6"}


def test_soil_symbol_open(pkg_a):
    sub(pkg_a, L, "siCl", "XYZ")
    assert validate(pkg_a).issues == []


def test_unknown_code_message(pkg_a):
    sub(pkg_a, "points.csv", "F1,borehole", "F1,foraj")
    [issue] = [i for i in validate(pkg_a).issues if i.check == "unknown_code"]
    assert issue.message == "foraj is not in point_type (allowed: borehole, cpt, dp, trial_pit, well)"


def test_excel_csv(pkg_a):
    write(pkg_a, "water.csv", "﻿point_id,kind,depth[m],datetime,remarks\r\nF1,struck,5.40,,\r\n,,,,\r\n"
                              "F1,stable,x,,\r\n\r\n")
    assert set(map(lambda i: (i.level, i.code, i.check, i.path, i.row, i.column), _on(validate(pkg_a), "water.csv"))) \
        == {("error", "E04", "bad_value", "water.csv", 4, "depth[m]")}


def test_header_whitespace(pkg_a):
    sub(pkg_a, "water.csv", "kind,depth[m]", "kind, depth[m] ")
    assert validate(pkg_a).issues == []


def test_unknown_file(pkg_a):
    for name in ["notes.txt", "attachments/foto.jpg", ".DS_Store", "cpt/.DS_Store", "__MACOSX/._points.csv"]:
        write(pkg_a, name, "x")
    assert found(validate(pkg_a)) == {("warning", "W02", "unknown_file", "notes.txt", None, "")}


def test_unknown_file_accept_newer(pkg_a):
    sub(pkg_a, "manifest.toml", 'version = "0.1"', 'version = "0.2"')
    write(pkg_a, "profile_x/data.csv", "a\n1\n")
    report = validate(pkg_a, accept_newer=True)
    assert ("warning", "W02", "unknown_file", "profile_x/data.csv", None, "") in found(report)
    assert report.ok


def test_finder_zip(pkg_a, tmp_path):
    zpath = tmp_path / "finder.gdp"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("lab/", "")
        z.writestr("cpt/data/", "")
        for f in sorted(pkg_a.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pkg_a).as_posix())
        z.writestr(".DS_Store", "x")
        z.writestr("__MACOSX/._manifest.toml", "x")
    assert validate(zpath).issues == []


def test_no_points(pkg_a):
    write(pkg_a, "points.csv", "point_id,type,easting[m],northing[m],final_depth[m]\n")
    assert ("error", "E02", "no_points", "points.csv", None, "") in found(validate(pkg_a))
    assert ("missing", "E02", "no_points", "points.csv", None, "") in found(validate(pkg_a, draft=True))


def test_manifest_only(pkg_a, tmp_path):
    only = tmp_path / "only"
    only.mkdir()
    shutil.copy(pkg_a / "manifest.toml", only / "manifest.toml")
    assert found(validate(only)) == {("error", "E02", "no_points", "points.csv", None, ""),
                                     ("error", "E02", "no_campaigns", "campaigns/", None, "")}
