"""Uniform access to a GDP package: a .gdp zip or a folder with the same layout."""
from __future__ import annotations

import zipfile
from pathlib import Path


class PackageError(Exception):
    """The package cannot be opened at all (missing path, not a zip, not a folder)."""


class Package:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if not self.path.exists():
            raise PackageError(f"{self.path}: no such file or folder")
        self.zip = None
        if self.path.is_file():
            try:
                self.zip = zipfile.ZipFile(self.path)
            except zipfile.BadZipFile as exc:
                raise PackageError(f"{self.path}: not a zip file") from exc

    def names(self) -> list[str]:
        """Posix paths of the files in the package (directory entries excluded)."""
        if self.zip:
            return [n for n in self.zip.namelist() if not n.endswith("/")]
        return sorted(p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file())

    def read_bytes(self, name: str) -> bytes | None:
        try:
            return self.zip.read(name) if self.zip else (self.path / name).read_bytes()
        except (KeyError, FileNotFoundError, IsADirectoryError):
            return None

    def read_text(self, name: str) -> str | None:
        """UTF-8 text with an optional BOM; raises UnicodeDecodeError for other encodings."""
        raw = self.read_bytes(name)
        return None if raw is None else raw.decode("utf-8-sig")
