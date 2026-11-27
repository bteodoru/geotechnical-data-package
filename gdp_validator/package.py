"""Uniform access to a GDP package: a .gdp zip or a folder with the same layout.

A zip without manifest.toml at its root whose content (archiver metadata aside) is one top-level
folder holding manifest.toml has that folder as package root, as Finder "Compress" and Windows
"Send to -> Compressed folder" produce. Names are always relative to the package root.
"""
from __future__ import annotations

import zipfile
import zlib
from pathlib import Path


class PackageError(Exception):
    """The package cannot be opened at all (missing path, not a zip, not a folder)."""


def ignored(name: str) -> bool:
    """Files never inspected: attachments, macOS metadata (__MACOSX/, dotfiles)."""
    parts = name.split("/")
    return parts[0] in ("__MACOSX", "attachments") or any(p.startswith(".") for p in parts)


def metadata(name: str) -> bool:
    """Archiver metadata: __MACOSX/, .DS_Store, AppleDouble ._* files."""
    parts = name.split("/")
    return parts[0] == "__MACOSX" or parts[-1] == ".DS_Store" or parts[-1].startswith("._")


class Package:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if not self.path.exists():
            raise PackageError(f"{self.path}: no such file or folder")
        self.zip = None
        self.root = ""
        if self.path.is_file():
            try:
                self.zip = zipfile.ZipFile(self.path)
            except zipfile.BadZipFile as exc:
                raise PackageError(f"{self.path}: not a zip file") from exc
            self.root = self._root()

    def _stored(self) -> list[str]:
        """Posix paths of all files as stored, before taking the package root into account."""
        if self.zip:
            return [n for n in self.zip.namelist() if not n.endswith("/")]
        return sorted(p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file())

    def _root(self) -> str:
        stored = self._stored()
        if "manifest.toml" in stored:
            return ""
        content = [n for n in stored if not metadata(n)]
        tops = {n.split("/", 1)[0] for n in content}
        if len(tops) == 1 and all("/" in n for n in content):
            top = tops.pop()
            if f"{top}/manifest.toml" in content:
                return top + "/"
        return ""

    def misplaced_manifests(self) -> list[str]:
        """Stored paths of manifest.toml files below the root, when the root has none."""
        if self.read_bytes("manifest.toml") is not None:
            return []
        return sorted(n for n in self._stored() if n.endswith("/manifest.toml") and not metadata(n))

    def names(self) -> list[str]:
        """Posix paths of the files in the package, relative to its root (directory entries excluded)."""
        return [n[len(self.root):] for n in self._stored() if n.startswith(self.root)]

    def read_bytes(self, name: str) -> bytes | None:
        try:
            return self.zip.read(self.root + name) if self.zip else (self.path / name).read_bytes()
        except (KeyError, FileNotFoundError, IsADirectoryError):
            return None
        except (zipfile.BadZipFile, zlib.error, EOFError) as exc:
            raise PackageError(f"{self.path}: {name} is corrupt ({exc})") from exc

    def read_text(self, name: str) -> str | None:
        """UTF-8 text with an optional BOM; raises UnicodeDecodeError for other encodings."""
        raw = self.read_bytes(name)
        return None if raw is None else raw.decode("utf-8-sig")
