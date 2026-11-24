import pytest

from gdp_validator import validate
from util import delete, found, sub

M = "manifest.toml"
C = "campaigns/C2026.toml"
UUID_LINE = 'uuid           = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"\n'
STD_CPT = 'cpt              = "SR EN ISO 22476-1"'
ATT = 'atterberg    = "fall_cone"'
SRC = 'source = "SR EN ISO 14688-1"'

CASES = [
    ("pkg_a", M, 'format  = "gdp"', "format  = gdp", ("error", "E01", "toml_syntax", M, None, "")),
    ("pkg_a", C, "year         = 2026", "year = = 2026", ("error", "E01", "toml_syntax", C, None, "")),
    ("pkg_a", M, UUID_LINE, "", ("error", "E01", "required_key", M, None, "project.uuid")),
    ("pkg_a", M, '"3f2a9c1e-', '"zz2a9c1e-', ("error", "E01", "schema_violation", M, None, "project.uuid")),
    ("pkg_a", C, "year         = 2026", "year         = 3026", ("error", "E01", "schema_violation", C, None, "year")),
    ("pkg_a", C, STD_CPT, STD_CPT + '\nvane = "X"', ("error", "E10", "unknown_test", C, None, "standards.vane")),
    ("pkg_a", C, ATT, ATT + '\nvane = "a"', ("error", "E10", "unknown_test", C, None, "methods.vane")),
    ("pkg_a", C, ATT, 'atterberg    = "thread"', ("error", "E10", "unknown_method", C, None, "methods.atterberg")),
    ("pkg_a", C, ATT, ATT + '\nwater_content = "oven"',
     ("error", "E10", "unknown_method", C, None, "methods.water_content")),
    ("pkg_a", C, SRC, 'source = "STAS 1243"', ("error", "E11", "fractions_source_unknown", C, None, "fractions.source")),
    ("pkg_a", C, SRC, 'source = "custom"', ("error", "E11", "custom_without_upper_mm", C, None, "fractions.upper_mm")),
    ("pkg_a", C, SRC, SRC + "\nupper_mm = { clay = 0.002, silt = 0.063, sand = 2.0, gravel = 63.0 }",
     ("error", "E11", "upper_mm_not_custom", C, None, "fractions.upper_mm")),
    ("pkg_a", C, STD_CPT, 'cpt              = "SR EN ISO 22476-12"',
     ("warning", "W05", "unknown_standard", C, None, "standards.cpt")),
    ("pkg_b", "campaigns/C2016.toml", ", gravel = 70.0", "",
     ("error", "E01", "required_key", "campaigns/C2016.toml", None, "fractions.upper_mm.gravel")),
]


def _apply(request, pkg, file, old, new):
    p = request.getfixturevalue(pkg)
    sub(p, file, old, new)
    return p


@pytest.mark.parametrize("pkg,file,old,new,expected", CASES, ids=[c[4][2] + "-" + c[2][:12] for c in CASES])
def test_case(request, pkg, file, old, new, expected):
    assert expected in found(validate(_apply(request, pkg, file, old, new)))


def test_accepted_keys(pkg_a):
    sub(pkg_a, C, STD_CPT, 'cpt              = "SR EN ISO 22476-1:2012"\noedometer = "unknown"\nx_vane = "X"')
    sub(pkg_a, C, ATT, ATT + '\nx_vane = "a"')
    sub(pkg_a, C, SRC, 'source = "SR EN ISO 14688-1:2018"')
    assert validate(pkg_a).issues == []


def test_unknown_method_message(pkg_a):
    sub(pkg_a, C, ATT, 'atterberg    = "thread"')
    [issue] = [i for i in validate(pkg_a).issues if i.check == "unknown_method"]
    assert issue.message == "method thread is not valid for atterberg (allowed: fall_cone, casagrande)"


@pytest.mark.parametrize("old,new", [
    (STD_CPT, STD_CPT + '\nvane = "X"'),
    (ATT, 'atterberg    = "thread"'),
    (ATT, ATT + '\nvane = "a"'),
    (SRC, SRC + "\nupper_mm = { clay = 0.002, silt = 0.063, sand = 2.0, gravel = 63.0 }"),
    (SRC, 'source = "custom"'),
])
def test_dropped_errors_not_duplicated(pkg_a, old, new):
    sub(pkg_a, C, old, new)
    assert not [i for i in validate(pkg_a).issues if i.code == "E01"]


def test_version(pkg_a):
    sub(pkg_a, M, 'version = "0.1"', 'version = "0.2"')
    assert found(validate(pkg_a)) == {("error", "E01", "version_unsupported", M, None, "version")}
    assert not [i for i in validate(pkg_a, accept_newer=True).issues if i.code == "E01"]


@pytest.mark.parametrize("version", ["0.0", "1.0"])
def test_version_not_accepted(pkg_a, version):
    sub(pkg_a, M, 'version = "0.1"', f'version = "{version}"')
    assert ("error", "E01", "version_unsupported", M, None, "version") in found(validate(pkg_a, accept_newer=True))


def test_no_campaigns(pkg_a):
    delete(pkg_a, C)
    assert ("error", "E02", "no_campaigns", "campaigns/", None, "") in found(validate(pkg_a))
    assert ("missing", "E02", "no_campaigns", "campaigns/", None, "") in found(validate(pkg_a, draft=True))


@pytest.mark.parametrize("file,old,new,check", [
    (M, UUID_LINE, "", "required_key"),
    (C, SRC, 'source = "custom"', "custom_without_upper_mm"),
])
def test_draft_missing(pkg_a, file, old, new, check):
    sub(pkg_a, file, old, new)
    assert [i.level for i in validate(pkg_a, draft=True).issues if i.check == check] == ["missing"]
