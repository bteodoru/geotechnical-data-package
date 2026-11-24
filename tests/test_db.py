import sqlite3

import pytest

import gdp_db
from conftest import EXAMPLES
from util import sub, write


def _db():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(gdp_db.ddl())
    return db


def test_load_examples():
    db = _db()
    for name in ("proiect_A.gdp", "proiect_B.gdp"):
        gdp_db.load(db, EXAMPLES / name)
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert db.execute("SELECT count(*) FROM points").fetchone()[0] == 4


def test_refuses_invalid(pkg_a):
    sub(pkg_a, "layers.csv", "F1,0.60,3.80", "F1,0.60,0.50")
    db = _db()
    with pytest.raises(ValueError, match=r"layers\.csv:3:depth_base\[m\] E07"):
        gdp_db.load(db, pkg_a)
    assert db.execute("SELECT count(*) FROM projects").fetchone()[0] == 0


def test_accept_newer(pkg_a):
    sub(pkg_a, "manifest.toml", 'version = "0.1"', 'version = "0.2"')
    write(pkg_a, "profile_x/data.csv", "a\n1\n")
    db = _db()
    with pytest.raises(ValueError, match="E01"):
        gdp_db.load(db, pkg_a)
    gdp_db.load(db, pkg_a, accept_newer=True)
    assert db.execute("SELECT format_version FROM projects").fetchone()[0] == "0.2"


def test_cli_accept_newer(pkg_a, tmp_path, capsys):
    sub(pkg_a, "manifest.toml", 'version = "0.1"', 'version = "0.2"')
    gdp_db.main(["load", "--accept-newer", str(tmp_path / "x.sqlite"), str(pkg_a)])
    assert "IS-2026-014" in capsys.readouterr().out
