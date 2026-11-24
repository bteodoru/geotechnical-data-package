"""validate(): runs the phases in order and builds the report."""
from __future__ import annotations

from pathlib import Path

from . import documents, refs, tables
from .context import Context
from .package import Package
from .report import Collector, Report
from .schema import load_locale


def validate(path, draft: bool = False, lang: str | None = None, accept_newer: bool = False) -> Report:
    pkg = Package(path)
    locale = load_locale(lang) if lang else None
    ctx = Context(pkg=pkg, out=Collector(draft, locale), accept_newer=accept_newer)
    if documents.run_manifest(ctx):
        documents.run_campaigns(ctx)
        tables.run(ctx)
        refs.run(ctx)
    return Report(Path(path).name, draft, ctx.out.issues)
