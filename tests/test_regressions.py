"""Findings of the final whole-branch review, each reproduced before the fix."""
import zipfile

from gdp_validate import main
from gdp_validator import validate
from util import append, delete, found, sub, write


def _codes(report, code, path=None):
    return [i for i in report.issues if i.code == code and (path is None or i.path == path)]


def test_w06_without_sample_id_column_does_not_crash(pkg_a):
    sub(pkg_a, "samples.csv", "sample_id,", "sampleid,")
    sub(pkg_a, "points.csv", "52.40,8.00", "52.40,10.00")
    append(pkg_a, "samples.csv", "F1-P4,F1,9.00,9.30,undisturbed,\n")
    report = validate(pkg_a)
    assert ("error", "E03", "missing_column", "samples.csv", 1, "sample_id") in found(report)


def test_row_length_in_points_no_e06_flood(pkg_a):
    sub(pkg_a, "points.csv", "52.40,8.00", "52.40,8,00")
    report = validate(pkg_a)
    assert len(_codes(report, "E04")) == 1
    assert _codes(report, "E06") == []


def test_row_length_in_cpt_tests_no_orphan(pkg_a):
    sub(pkg_a, "cpt/tests.csv", ",0.80,", ",0,80,")
    assert _codes(validate(pkg_a), "E09") == []


def test_missing_points_no_e06(pkg_a):
    delete(pkg_a, "points.csv")
    assert _codes(validate(pkg_a), "E06") == []


def test_header_only_points_no_e06(pkg_a):
    write(pkg_a, "points.csv", "point_id,type,easting[m],northing[m],final_depth[m]\n")
    assert _codes(validate(pkg_a), "E06") == []


def test_unusable_test_id_no_orphan(pkg_a):
    sub(pkg_a, "cpt/tests.csv", "test_id,", "testid,")
    assert _codes(validate(pkg_a), "E09") == []


def test_cpt_beyond_final_depth_once_per_file(pkg_a):
    sub(pkg_a, "points.csv", "52.38,10.20", "52.38,5.00")
    assert len(_codes(validate(pkg_a), "E07", "cpt/data/CPT1.csv")) == 1


def test_duplicate_unitless_column_first_wins(pkg_a):
    write(pkg_a, "water.csv", "point_id,kind,depth[m],kind\nF1,struck,5.40,\n")
    report = validate(pkg_a)
    assert ("error", "E03", "duplicate_column", "water.csv", 1, "kind") in found(report)
    assert _codes(report, "E04", "water.csv") == []


def test_required_key_reported_once(pkg_a, pkg_b):
    sub(pkg_a, "manifest.toml", 'uuid           = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"\n', "")
    sub(pkg_a, "manifest.toml", 'name           = "Clădire socială, extindere anexă"\n', "")
    assert sorted(i.column for i in validate(pkg_a).issues if i.check == "required_key") == \
        ["project.name", "project.uuid"]
    sub(pkg_b, "campaigns/C2016.toml", ", silt = 0.05, sand = 2.0, gravel = 70.0", "")
    assert len([i for i in validate(pkg_b).issues if i.check == "required_key"]) == 3


def test_campaign_dotfile_ignored(pkg_a):
    write(pkg_a, "campaigns/._C2026.toml", b"\x00\x05\x16\x07")
    assert validate(pkg_a).issues == []


def test_method_for_test_without_methods(pkg_a):
    sub(pkg_a, "campaigns/C2026.toml", 'atterberg    = "fall_cone"', 'atterberg    = "fall_cone"\nwater_content = "oven"')
    [issue] = [i for i in validate(pkg_a).issues if i.check == "unknown_method"]
    assert issue.allowed == ()
    assert "n, o" not in issue.message


def test_draft_allowed_for_vocabulary_columns(pkg_a, pkg_b):
    sub(pkg_a, "points.csv", "F1,borehole", "F1,")
    [issue] = [i for i in validate(pkg_a, draft=True).issues if i.check == "required_empty"]
    assert issue.allowed == ("borehole", "cpt", "dp", "trial_pit", "well")
    sub(pkg_b, "points.csv", "F2,borehole,C2026", "F2,borehole,")
    [issue] = [i for i in validate(pkg_b, draft=True).issues if i.check == "campaign_required"]
    assert issue.allowed == ("C2016", "C2026")


def test_draft_allowed_for_required_if(pkg_a):
    sub(pkg_a, "cpt/tests.csv", ",0.80,u2,", ",0.80,,")
    [issue] = [i for i in validate(pkg_a, draft=True).issues if i.check == "required_empty"]
    assert issue.allowed == ("u1", "u2", "u3")


def test_corrupt_zip_member_exit_2(pkg_a, tmp_path):
    zpath = tmp_path / "bad.gdp"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(pkg_a.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pkg_a).as_posix())
    data = bytearray(zpath.read_bytes())
    i = data.index(b"Pagani")
    data[i] = ord("X")
    zpath.write_bytes(bytes(data))
    assert main([str(zpath)]) == 2
