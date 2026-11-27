"""CSV dialects: ',' with decimal '.' and ';' with decimal ',', detected per file from the header (spec §3; §13, design decision 25)."""
import csv
import io
import json
import sqlite3
from pathlib import Path

import gdp_db
from gdp_validator import validate
from util import found, write

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "gdp-0.1.schema.json").read_text(encoding="utf-8"))
P = "points.csv"


def _numeric(path: str) -> set[str]:
    table = next(t for t in SCHEMA["tables"].values()
                 if t["path"] == path or (path.startswith("cpt/data/") and t["path"].startswith("cpt/data/")))
    return {f["name"] for f in table["fields"] if f["type"] == "number"}


def to_semicolon(pkg: Path, path: str) -> None:
    """Rewrite one table the way a spreadsheet in a decimal-comma locale exports it:
    ';' separator, decimal comma, CRLF, BOM, no final newline."""
    rows = list(csv.reader(io.StringIO((pkg / path).read_text(encoding="utf-8"), newline="")))
    numeric = _numeric(path)
    names = [h.split("[")[0] for h in rows[0]]
    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    w.writerow(rows[0])
    for r in rows[1:]:
        w.writerow([v.replace(".", ",") if n in numeric else v for n, v in zip(names, r)])
    (pkg / path).write_bytes(b"\xef\xbb\xbf" + out.getvalue().rstrip("\r\n").encode("utf-8"))


TABLES = ["points.csv", "units.csv", "layers.csv", "water.csv", "samples.csv",
          "lab/index.csv", "cpt/tests.csv", "cpt/data/CPT1.csv"]


def test_schema_declares_two_dialects():
    assert SCHEMA["csv"]["dialects"] == [{"delimiter": ",", "decimal": "."}, {"delimiter": ";", "decimal": ","}]


def test_semicolon_package_is_valid(pkg_a):
    for path in TABLES:
        to_semicolon(pkg_a, path)
    text = (pkg_a / P).read_text(encoding="utf-8-sig")
    assert "52,40" in text and ";rotativ uscat, Ø 146 mm;" in text     # comma in text stays unquoted
    assert validate(pkg_a).issues == []


def test_dialects_mix_within_a_package(pkg_a):
    to_semicolon(pkg_a, P)
    to_semicolon(pkg_a, "lab/index.csv")
    assert validate(pkg_a).issues == []


def test_dot_decimal_in_semicolon_file(pkg_a):
    to_semicolon(pkg_a, P)
    raw = (pkg_a / P).read_bytes().replace(b"52,40", b"52.40")
    (pkg_a / P).write_bytes(raw)
    [issue] = [i for i in validate(pkg_a).issues if i.path == P]
    assert (issue.code, issue.check, issue.row, issue.column) == ("E04", "decimal_mark", 2, "elevation[m]")
    assert issue.message == "52.40: in a file separated by ; the decimal mark is ,"


def test_thousands_separator_in_semicolon_file_is_caught(pkg_a):
    to_semicolon(pkg_a, P)
    raw = (pkg_a / P).read_bytes().replace(b"697412,35", b"697.412")
    (pkg_a / P).write_bytes(raw)
    assert ("error", "E04", "decimal_mark", P, 2, "easting[m]") in found(validate(pkg_a))


def test_semicolon_values_reported_as_written(pkg_a):
    to_semicolon(pkg_a, "layers.csv")
    raw = (pkg_a / "layers.csv").read_bytes().replace(b"F1;0,60;3,80", b"F1;0,60;0,50")
    (pkg_a / "layers.csv").write_bytes(raw)
    msgs = [i.message for i in validate(pkg_a).issues if i.code == "E07"]
    assert msgs == ["depth_base (0,50) <= depth_top (0,60)"]


def test_tab_separated_file_is_one_error(pkg_a):
    text = (pkg_a / "layers.csv").read_text(encoding="utf-8").replace(",", "\t")
    write(pkg_a, "layers.csv", text)
    issues = [i for i in validate(pkg_a).issues if i.path == "layers.csv"]
    assert [(i.code, i.check, i.row) for i in issues] == [("E03", "separator_unknown", 1)]
    assert issues[0].message == "the header is a single cell: columns must be separated by , or ;"


def test_not_utf8_message(pkg_a):
    write(pkg_a, "units.csv", "unit_id,name\nU0,Pământ\n".encode("cp1250"))
    [issue] = [i for i in validate(pkg_a).issues if i.path == "units.csv"]
    assert issue.check == "not_utf8"
    assert issue.message == "file is not UTF-8: save it as CSV UTF-8"


def test_importer_reads_semicolon_files(pkg_a):
    def load(pkg):
        db = sqlite3.connect(":memory:")
        db.executescript(gdp_db.ddl())
        gdp_db.load(db, pkg)
        return db

    expected = load(pkg_a)
    queries = ["SELECT point_id, easting, elevation, final_depth, method FROM points ORDER BY point_id",
               "SELECT point_id, depth_top, depth_base FROM layers ORDER BY point_id, depth_top",
               "SELECT count(*), sum(depth), sum(qc) FROM cpt_data"]
    before = [expected.execute(q).fetchall() for q in queries]
    for path in TABLES:
        to_semicolon(pkg_a, path)
    after = [load(pkg_a).execute(q).fetchall() for q in queries]
    assert after == before
    assert isinstance(after[0][0][2], float)
