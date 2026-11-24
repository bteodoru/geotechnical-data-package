import json

from conftest import EXAMPLES
from gdp_validate import main
from util import delete


def test_ok(capsys):
    assert main([str(EXAMPLES / "proiect_A.gdp")]) == 0
    assert capsys.readouterr().out.strip().endswith("0 errors, 0 warnings")


def test_errors_and_draft(pkg_a, capsys):
    delete(pkg_a, "manifest.toml")
    assert main([str(pkg_a)]) == 1
    assert "manifest.toml:: E01 manifest.toml not found" in capsys.readouterr().out
    assert main(["--draft", str(pkg_a)]) == 0


def test_unopenable(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2
    assert main(["--lang", "xx", str(EXAMPLES / "proiect_A.gdp")]) == 2


def test_json(pkg_a, capsys):
    delete(pkg_a, "manifest.toml")
    code = main(["--format", "json", str(pkg_a)])
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is (code == 0)
    assert data["issues"][0]["check"] == "manifest_missing"
