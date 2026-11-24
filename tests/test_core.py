import json

import pytest

from conftest import EXAMPLES
from gdp_validator import Issue, PackageError, Report, validate
from gdp_validator.schema import render
from util import delete, found


def test_render_fallback():
    params = {"base": "3.20", "top": "3.40"}
    assert render("E07", "top_not_above_base", params, None) == "depth_base (3.20) <= depth_top (3.40)"
    loc = {"rules.E07.checks.top_not_above_base": {"message": "depth_base ({base}) ≤ depth_top ({top})"}}
    assert render("E07", "top_not_above_base", params, loc) == "depth_base (3.20) ≤ depth_top (3.40)"
    assert render("E07", "top_not_above_base", params, {}) == "depth_base (3.20) <= depth_top (3.40)"


def test_manifest_missing(pkg_a):
    delete(pkg_a, "manifest.toml")
    assert ("error", "E01", "manifest_missing", "manifest.toml", None, "") in found(validate(pkg_a))
    draft = validate(pkg_a, draft=True)
    assert ("missing", "E01", "manifest_missing", "manifest.toml", None, "") in found(draft)
    assert draft.ok


def test_package_errors(tmp_path):
    with pytest.raises(PackageError):
        validate(tmp_path / "nope")
    txt = tmp_path / "x.gdp"
    txt.write_text("not a zip")
    with pytest.raises(PackageError):
        validate(txt)


@pytest.mark.parametrize("name", ["proiect_A.gdp", "proiect_B.gdp"])
def test_examples_clean(name):
    assert validate(EXAMPLES / name).issues == []


def _issue(level="error", code="E07", check="top_not_above_base", path="layers.csv", row=14,
           column="depth_base[m]", allowed=None):
    params = {"base": "3.20", "top": "3.40"}
    return Issue(level, code, check, path, row, column, params, "depth_base (3.20) <= depth_top (3.40)", allowed)


def test_report_text():
    text = Report("p.gdp", False, [_issue()]).to_text().splitlines()
    assert text[0] == "layers.csv:14:depth_base[m] E07 depth_base (3.20) <= depth_top (3.40)"
    assert text[-1] == "1 errors, 0 warnings"


def test_report_text_empty_row():
    issue = Issue("error", "E01", "manifest_missing", "manifest.toml", None, "", {}, "manifest.toml not found", None)
    assert Report("p", False, [issue]).to_text().splitlines()[0] == "manifest.toml:: E01 manifest.toml not found"


def test_report_text_draft():
    missing = Issue("missing", "E01", "manifest_missing", "manifest.toml", None, "", {}, "manifest.toml not found", None)
    lines = Report("p", True, [_issue(), missing]).to_text().splitlines()
    assert lines[1] == "missing:"
    assert lines[2] == "manifest.toml:: E01 manifest.toml not found"
    assert lines[-1] == "1 errors, 0 warnings, 1 missing"


def test_report_json():
    data = json.loads(Report("p.gdp", False, [_issue(), _issue(row=3, allowed=("a", "b"))]).to_json())
    assert set(data) == {"package", "draft", "ok", "issues"}
    assert data["package"] == "p.gdp" and data["ok"] is False and data["draft"] is False
    second, first = data["issues"]  # sorted by row: 3 before 14
    assert set(first) == {"level", "code", "check", "path", "row", "column", "params", "message"}
    assert second["allowed"] == ["a", "b"]


def test_report_sorting_and_ok():
    w = _issue(level="warning", code="W01", row=2)
    m = _issue(level="missing", row=1)
    e2, e1 = _issue(row=20), _issue(row=3)
    report = Report("p", True, [w, m, e2, e1])
    assert [i.row for i in report.issues] == [3, 20, 2, 1]
    assert not report.ok
    assert Report("p", True, [w, m]).ok
