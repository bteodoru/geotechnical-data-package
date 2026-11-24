"""Addendum-1 proposals adopted on 2026-11-24: P3 (UCUM), P4 (station/offset), P6 (source_file)."""
import sqlite3

import pytest

import gdp_db
from gdp_validator import validate
from gdp_validator.schema import SCHEMA
from util import found, sub, write

# Unit symbols checked against UCUM (case-sensitive). Add a symbol here only after checking it.
UCUM_CHECKED = {"%", "MPa", "Mg/m3", "cm2", "deg", "kN/m3", "kPa", "m"}

P_HEADER = "point_id,type,easting[m],northing[m],elevation[m],final_depth[m],date_start,date_end,method,remarks"
F1_ROW = 'F1,borehole,697412.35,634988.10,52.40,8.00,2026-10-14,2026-10-14,"rotativ uscat, Ø 146 mm",'


def _fields(table):
    return {f["name"]: f for f in SCHEMA["tables"][table]["fields"]}


# P3 -----------------------------------------------------------------------------------------

def test_unit_system_declared():
    assert SCHEMA["unit_system"]["name"] == "UCUM"
    assert SCHEMA["unit_system"]["variant"] == "case-sensitive"


def test_units_are_checked_ucum():
    units = {f["unit"] for t in SCHEMA["tables"].values() for f in t["fields"] if f.get("unit")}
    assert units <= UCUM_CHECKED


# P4 -----------------------------------------------------------------------------------------

def test_station_fields():
    f = _fields("points")
    assert (f["station"]["type"], f["station"]["unit"], f["station"]["required"]) == ("number", "m", False)
    assert (f["offset"]["type"], f["offset"]["unit"], f["offset"]["required"]) == ("number", "m", False)
    assert f["station"]["required_if"] == {"field": "offset"}
    assert (f["alignment"]["type"], f["alignment"]["required"]) == ("text", False)


def _linear(pkg, station, offset, alignment="dig"):
    sub(pkg, "points.csv", P_HEADER, P_HEADER + ",station[m],offset[m],alignment")
    sub(pkg, "points.csv", F1_ROW, F1_ROW + f",{station},{offset},{alignment}")
    sub(pkg, "points.csv", "refuz la 10.20 m", "refuz la 10.20 m,,,")


def test_station_offset_accepted(pkg_a):
    _linear(pkg_a, "12345.60", "-7.50")
    assert validate(pkg_a).issues == []


def test_offset_requires_station(pkg_a):
    _linear(pkg_a, "", "-7.50")
    assert ("error", "E04", "required_empty", "points.csv", 2, "station[m]") in found(validate(pkg_a))
    assert ("missing", "E04", "required_empty", "points.csv", 2, "station[m]") in found(validate(pkg_a, draft=True))


def test_station_without_offset_accepted(pkg_a):
    _linear(pkg_a, "12345.60", "", "")
    assert validate(pkg_a).issues == []


# P6 -----------------------------------------------------------------------------------------

SOURCE_TABLES = {"points", "layers", "water", "samples", "lab_index", "cpt_tests"}


def test_source_file_fields():
    have = {t for t in SCHEMA["tables"] if "source_file" in _fields(t)}
    assert have == SOURCE_TABLES
    for t in SOURCE_TABLES:
        f = _fields(t)["source_file"]
        assert (f["type"], f["required"], f["references"]) == ("file_ref", False, "attachment")


def _lab_source(pkg, value):
    sub(pkg, "lab/index.csv", ",gravel[%],remarks\n", ",gravel[%],remarks,source_file\n")
    sub(pkg, "lab/index.csv", ",28,58,14,0,\n", f",28,58,14,0,,{value}\n")
    sub(pkg, "lab/index.csv", ",31,56,13,0,\n", ",31,56,13,0,,\n")
    sub(pkg, "lab/index.csv", ",48,44,8,0,\n", ",48,44,8,0,,\n")


@pytest.mark.parametrize("value", ["buletin.pdf", "buletin.pdf#page=3", "lab/buletin.pdf"])
def test_source_file_resolves(pkg_a, value):
    write(pkg_a, "attachments/buletin.pdf", b"%PDF-1.4")
    write(pkg_a, "attachments/lab/buletin.pdf", b"%PDF-1.4")
    _lab_source(pkg_a, value)
    assert validate(pkg_a).issues == []


def test_source_file_unresolved(pkg_a):
    _lab_source(pkg_a, "buletin.pdf#page=3")
    report = validate(pkg_a)
    assert ("error", "E06", "source_unresolved", "lab/index.csv", 2, "source_file") in found(report)
    [issue] = [i for i in report.issues if i.check == "source_unresolved"]
    assert issue.message == "source file buletin.pdf not found in attachments/"


@pytest.mark.parametrize("value", ["buletin.pdf#p3", "buletin.pdf#page=0", "#page=2"])
def test_source_file_bad_fragment(pkg_a, value):
    write(pkg_a, "attachments/buletin.pdf", b"%PDF-1.4")
    _lab_source(pkg_a, value)
    assert ("error", "E04", "bad_value", "lab/index.csv", 2, "source_file") in found(validate(pkg_a))


def test_db_loads_source_and_station(pkg_a):
    write(pkg_a, "attachments/buletin.pdf", b"%PDF-1.4")
    _lab_source(pkg_a, "buletin.pdf#page=3")
    _linear(pkg_a, "12345.60", "-7.50")
    db = sqlite3.connect(":memory:")
    db.executescript(gdp_db.ddl())
    gdp_db.load(db, pkg_a)
    assert db.execute("SELECT source_file FROM lab_index WHERE sample_id='F1-P1'").fetchone()[0] == "buletin.pdf#page=3"
    assert db.execute("SELECT station, offset, alignment FROM points WHERE point_id='F1'").fetchone() == \
        (12345.6, -7.5, "dig")
