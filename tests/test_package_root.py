"""Package root inside a zip: a single top-level folder holding manifest.toml (Finder "Compress", Windows "Send to")."""
import sqlite3
import zipfile
from pathlib import Path

import gdp_db
from gdp_validator import validate
from util import found, sub


def _zip(pkg: Path, dest: Path, prefix: str, extra: dict[str, bytes] | None = None, dirs: bool = False) -> Path:
    with zipfile.ZipFile(dest, "w") as z:
        if dirs:
            z.writestr(prefix, b"")
        for f in sorted(p for p in pkg.rglob("*") if p.is_file()):
            rel = f.relative_to(pkg).as_posix()
            if dirs and "/" in rel:
                z.writestr(prefix + rel.rsplit("/", 1)[0] + "/", b"")
            z.write(f, prefix + rel)
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return dest


FINDER_METADATA = {
    "__MACOSX/proiect_A/._points.csv": b"\x00\x05\x16\x07",
    "__MACOSX/proiect_A/lab/._index.csv": b"\x00\x05\x16\x07",
    "proiect_A/.DS_Store": b"\x00\x00\x00\x01Bud1",
    "proiect_A/._layers.csv": b"\x00\x05\x16\x07",
}


def test_finder_zip_is_valid(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "finder.zip", "proiect_A/", FINDER_METADATA, dirs=True)
    assert validate(z).issues == []


def test_windows_zip_is_valid(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "windows.zip", "proiect_A/")
    assert validate(z).issues == []


def test_paths_are_relative_to_the_root(pkg_a, tmp_path):
    sub(pkg_a, "layers.csv", "F1,0.60,3.80", "F1,0.60,0.50")
    z = _zip(pkg_a, tmp_path / "finder.zip", "proiect_A/", FINDER_METADATA, dirs=True)
    assert ("error", "E07", "top_not_above_base", "layers.csv", 3, "depth_base[m]") in found(validate(z))


def _only_hint(report, found):
    assert [(i.level, i.code, i.check, i.path, i.row, i.column, i.params) for i in report.issues] == [
        ("error", "E01", "manifest_elsewhere", "manifest.toml", None, "", {"found": found})]


def test_two_top_level_folders(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "two.zip", "proiect_A/", {"altceva/note.txt": b"x"})
    report = validate(z)
    _only_hint(report, "proiect_A/manifest.toml")
    assert report.issues[0].message == "manifest.toml is not at the package root; found at proiect_A/manifest.toml"
    _only_hint(validate(z, draft=True), "proiect_A/manifest.toml")


def test_manifest_two_levels_deep(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "deep.zip", "lucrari/proiect_A/")
    _only_hint(validate(z), "lucrari/proiect_A/manifest.toml")
    _only_hint(validate(z, draft=True), "lucrari/proiect_A/manifest.toml")


def test_folder_holding_the_package_in_a_subfolder(pkg_a, tmp_path):
    outer = tmp_path / "lucrari"
    outer.mkdir()
    pkg_a.rename(outer / "proiect_A")
    _only_hint(validate(outer), "proiect_A/manifest.toml")
    _only_hint(validate(outer, draft=True), "proiect_A/manifest.toml")


def test_no_manifest_anywhere_unchanged(pkg_a):
    (pkg_a / "manifest.toml").unlink()
    assert ("error", "E01", "manifest_missing", "manifest.toml", None, "") in found(validate(pkg_a))
    assert ("missing", "E01", "manifest_missing", "manifest.toml", None, "") in found(validate(pkg_a, draft=True))


def test_metadata_alone_does_not_hide_a_second_folder(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "loose.zip", "proiect_A/", {"readme.txt": b"x"})
    assert any(i.check == "manifest_elsewhere" for i in validate(z).issues)


def test_importer_reads_finder_zip(pkg_a, tmp_path):
    z = _zip(pkg_a, tmp_path / "finder.zip", "proiect_A/", FINDER_METADATA, dirs=True)
    db = sqlite3.connect(":memory:")
    db.executescript(gdp_db.ddl())
    gdp_db.load(db, z)
    assert db.execute("SELECT count(*) FROM points").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM cpt_data").fetchone()[0] > 0
