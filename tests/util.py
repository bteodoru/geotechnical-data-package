"""Helpers shared by the validator tests."""
from __future__ import annotations

import zipfile
from pathlib import Path


def unpack(gdp: Path, dest: Path) -> Path:
    with zipfile.ZipFile(gdp) as z:
        z.extractall(dest)
    return dest


def sub(pkg: Path, name: str, old: str, new: str) -> None:
    path = pkg / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in {name}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def write(pkg: Path, name: str, text: str | bytes) -> None:
    path = pkg / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_bytes(text.encode("utf-8"))


def append(pkg: Path, name: str, text: str) -> None:
    path = pkg / name
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def delete(pkg: Path, name: str) -> None:
    (pkg / name).unlink()


def found(report) -> set[tuple]:
    return {(i.level, i.code, i.check, i.path, i.row, i.column) for i in report.issues}
