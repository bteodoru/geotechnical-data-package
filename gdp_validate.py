"""GDP v0.1 reference validator (command line).

    python3 gdp_validate.py [--draft] [--format text|json] [--lang ro] PACKAGE

Exit codes: 0 no errors, 1 errors, 2 the package cannot be opened.
"""
from __future__ import annotations

import argparse
import sys

from gdp_validator import PackageError, validate

__all__ = ["validate", "main"]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="gdp_validate.py", description="Validate a GDP package.")
    parser.add_argument("package", help=".gdp zip or package folder")
    parser.add_argument("--draft", action="store_true", help="report lacks as a completeness list")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--lang", help="message language, e.g. ro")
    args = parser.parse_args(argv)
    try:
        report = validate(args.package, draft=args.draft, lang=args.lang)
    except (PackageError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(report.to_json() if args.format == "json" else report.to_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
