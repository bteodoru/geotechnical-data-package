"""Issues, their collection during a run, and the final report."""
from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass, field

from .schema import check_spec, render, rule_level, template

LEVEL_ORDER = {"error": 0, "warning": 1, "missing": 2}


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    check: str
    path: str
    row: int | None
    column: str
    params: dict[str, str]
    message: str
    allowed: tuple[str, ...] | None = None

    def line(self) -> str:
        row = "" if self.row is None else str(self.row)
        return f"{self.path}:{row}:{self.column} {self.code} {self.message}"


def _sort_key(i: Issue):
    return (LEVEL_ORDER[i.level], i.path, i.row or 0, i.column, i.code, i.check)


class Collector:
    def __init__(self, draft: bool, locale: dict | None):
        self.draft = draft
        self.locale = locale
        self.issues: list[Issue] = []

    def add(self, code: str, check: str, path: str, row: int | None = None, column: str = "",
            allowed=None, **params) -> None:
        spec = check_spec(code, check)
        if spec.get("missing"):
            level = "missing" if self.draft else "error"
        else:
            level = rule_level(code)
        params = {k: str(v) for k, v in params.items()}
        if allowed is not None:
            allowed = tuple(str(a) for a in allowed)
            fields = {f for _, f, _, _ in string.Formatter().parse(template(code, check, self.locale)) if f}
            if "allowed" in fields and "allowed" not in params:
                params["allowed"] = ", ".join(allowed)
        message = render(code, check, params, self.locale)
        self.issues.append(Issue(level, code, check, path, row, column, params, message, allowed))


@dataclass
class Report:
    package: str
    draft: bool
    issues: list[Issue] = field(default_factory=list)

    def __post_init__(self):
        self.issues = sorted(self.issues, key=_sort_key)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def missing(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "missing"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_text(self) -> str:
        lines = [i.line() for i in self.errors + self.warnings]
        if self.missing:
            lines.append("missing:")
            lines += [i.line() for i in self.missing]
        summary = f"{len(self.errors)} errors, {len(self.warnings)} warnings"
        if self.draft:
            summary += f", {len(self.missing)} missing"
        return "\n".join(lines + [summary]) + "\n"

    def to_json(self) -> str:
        issues = []
        for i in self.issues:
            d = asdict(i)
            if i.allowed is None:
                del d["allowed"]
            else:
                d["allowed"] = list(i.allowed)
            issues.append(d)
        data = {"package": self.package, "draft": self.draft, "ok": self.ok, "issues": issues}
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
