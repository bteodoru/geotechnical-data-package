"""manifest.toml and campaigns/<id>.toml."""
from __future__ import annotations

from .context import Context

MANIFEST = "manifest.toml"


def run_manifest(ctx: Context) -> bool:
    """Validate the manifest; False means the remaining checks must be skipped."""
    if ctx.pkg.read_bytes(MANIFEST) is None:
        ctx.out.add("E01", "manifest_missing", MANIFEST)
        return True
    return True
