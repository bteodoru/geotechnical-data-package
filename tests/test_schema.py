import json
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "gdp-0.1.schema.json").read_text(encoding="utf-8"))

EXPECTED = {
    "E01": {"manifest_missing", "manifest_elsewhere", "toml_syntax", "schema_violation", "required_key", "version_unsupported"},
    "E02": {"no_points", "no_campaigns"},
    "E03": {"missing_column", "wrong_unit", "duplicate_column", "bad_header", "unreadable", "not_utf8",
            "separator_unknown"},
    "E04": {"bad_value", "required_empty", "out_of_bounds", "row_length", "decimal_mark",
            "bad_date", "bad_datetime"},
    "E05": {"duplicate_key"},
    "E06": {"unresolved", "campaign_unresolved", "campaign_required", "source_unresolved"},
    "E07": {"top_not_above_base", "beyond_final_depth"},
    "E08": {"overlap"},
    "E09": {"data_file_missing", "orphan_data_file", "not_increasing"},
    "E10": {"unknown_code", "wL_below_wP", "unknown_test", "unknown_method"},
    "E11": {"standard_missing", "fractions_missing", "fractions_source_unknown",
            "custom_without_upper_mm", "upper_mm_not_custom"},
    "E12": {"both_groups"},
    "W01": {"gap", "not_from_surface", "not_to_final_depth"},
    "W02": {"unknown_column", "unknown_file"},
    "W03": {"implausible"},
    "W04": {"fractions_sum"},
    "W05": {"unknown_standard"},
    "W06": {"sample_outside_layers"},
    "W07": {"layer_without_unit"},
}

MISSING = {
    ("E01", "manifest_missing"), ("E01", "required_key"),
    ("E02", "no_points"), ("E02", "no_campaigns"),
    ("E03", "missing_column"), ("E04", "required_empty"), ("E06", "campaign_required"),
    ("E11", "standard_missing"), ("E11", "fractions_missing"), ("E11", "custom_without_upper_mm"),
}


def _checks():
    for rule in SCHEMA["rules"]:
        for cid, spec in rule["checks"].items():
            yield rule["code"], cid, spec


def test_check_ids():
    assert {r["code"]: set(r["checks"]) for r in SCHEMA["rules"]} == EXPECTED


def test_missing_flags():
    assert {(c, i) for c, i, s in _checks() if s.get("missing")} == MISSING
    for code, cid, spec in _checks():
        assert set(spec) <= {"message", "missing"}, (code, cid)
        assert isinstance(spec["message"], str) and spec["message"], (code, cid)


def test_placeholders():
    for code, cid, spec in _checks():
        for _, field, fmt, conv in string.Formatter().parse(spec["message"]):
            if field is None:
                continue
            assert field.isidentifier() and not fmt and conv is None, (code, cid, field)


def test_e01_text():
    e01 = next(r for r in SCHEMA["rules"] if r["code"] == "E01")
    assert e01["text"] == ("manifest.toml and the campaign files are valid TOML and match their schemas "
                           "(format, version, project.uuid, project.id, project.name, project.crs).")


def test_required_if():
    fields = {f["name"]: f for f in SCHEMA["tables"]["cpt_tests"]["fields"]}
    assert fields["area_ratio"]["required_if"] == {"data_column": "u"}
    assert fields["filter_position"]["required_if"] == {"data_column": "u"}


def test_ddl_unchanged():
    out = subprocess.run([sys.executable, "gdp_db.py", "ddl"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    assert out == (ROOT / "gdp-0.1.db.sql").read_text(encoding="utf-8")
