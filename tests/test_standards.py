from gdp_validator import validate
from util import found, sub, write

C = "campaigns/C2026.toml"
B16 = "campaigns/C2016.toml"


def _one(report, check):
    [issue] = [i for i in report.issues if i.check == check]
    return issue


def test_standard_missing_lab(pkg_a):
    sub(pkg_a, C, 'atterberg        = "SR EN ISO 17892-12"\n', "")
    report = validate(pkg_a)
    assert ("error", "E11", "standard_missing", C, None, "standards.atterberg") in found(report)
    issue = _one(report, "standard_missing")
    assert issue.allowed == ("SR EN ISO 17892-12", "unknown")
    assert issue.message == "atterberg has data in campaign C2026 but no standard is declared"
    assert _one(validate(pkg_a, draft=True), "standard_missing").level == "missing"


def test_standard_missing_cpt(pkg_a):
    sub(pkg_a, C, 'cpt              = "SR EN ISO 22476-1"\n', "")
    assert ("error", "E11", "standard_missing", C, None, "standards.cpt") in found(validate(pkg_a))


def test_standard_missing_other_campaign(pkg_b):
    sub(pkg_b, B16, 'grain_size    = "unknown"\n', "")
    assert ("error", "E11", "standard_missing", B16, None, "standards.grain_size") in found(validate(pkg_b))


def test_sample_override(pkg_b):
    sub(pkg_b, B16, 'grain_size    = "unknown"\n', "")
    write(pkg_b, "samples.csv", "sample_id,point_id,campaign,depth_top[m],depth_base[m],kind\n"
                                "F1-P1,F1,C2026,2.00,2.30,undisturbed\n"
                                "F2-P1,F2,,2.50,2.80,undisturbed\n"
                                "F2-P2,F2,,6.00,6.30,undisturbed\n")
    assert not [i for i in validate(pkg_b).issues if i.code == "E11"]


def test_fractions_missing(pkg_a):
    sub(pkg_a, C, '\n[fractions]\nsource = "SR EN ISO 14688-1"', "")
    report = validate(pkg_a)
    assert ("error", "E11", "fractions_missing", C, None, "fractions.source") in found(report)
    assert _one(report, "fractions_missing").allowed == ("SR EN ISO 14688-1", "custom")
