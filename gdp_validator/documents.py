"""manifest.toml and campaigns/<id>.toml: E01, E02 no_campaigns, E10 keys/methods, E11 fractions, W05."""
from __future__ import annotations

import datetime as dt
import re
import tomllib

from jsonschema import Draft202012Validator

from .context import Context
from .package import ignored
from .schema import SCHEMA, VERSION

MANIFEST = "manifest.toml"
CAMPAIGN_RE = re.compile(r"campaigns/([^/]+)\.toml")

VOCAB = SCHEMA["vocabularies"]
TESTS = VOCAB["tests"]
RESERVED = set(VOCAB["reserved_tests"])
FRACTIONS_REGISTRY = {k: v for k, v in VOCAB["fractions_registry"].items() if not k.startswith("$")}
STANDARDS_REGISTRY = set(VOCAB["standards_registry"])

_VALIDATORS = {
    name: Draft202012Validator(doc["schema"], format_checker=Draft202012Validator.FORMAT_CHECKER)
    for name, doc in SCHEMA["documents"].items()
}


def strip_year(standard: str) -> str:
    """'SR EN ISO 17892-12:2018' -> 'SR EN ISO 17892-12'."""
    return standard.split(":", 1)[0].strip()


def _jsonable(obj):
    """TOML dates and times become ISO strings, as JSON Schema expects."""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (dt.date, dt.time)):  # datetime is a subclass of date
        return obj.isoformat()
    return obj


def _parse(ctx: Context, path: str) -> dict | None:
    text = ctx.pkg.read_bytes(path)
    try:
        return _jsonable(tomllib.loads(text.decode("utf-8-sig")))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        ctx.out.add("E01", "toml_syntax", path, detail=str(exc))
        return None


def _dropped(error) -> bool:
    """JSON Schema errors that dedicated campaign checks report with their own codes."""
    path = list(error.absolute_path)
    head = path[0] if path else None
    schema_path = list(error.schema_path)
    if head == "standards" and "propertyNames" in schema_path:
        return True
    if head == "methods" and error.validator in ("additionalProperties", "enum"):
        return True
    return head == "fractions" and ("then" in schema_path or "else" in schema_path)


def _schema_errors(ctx: Context, path: str, doc: dict, kind: str) -> None:
    seen: set[str] = set()
    for error in sorted(_VALIDATORS[kind].iter_errors(doc), key=lambda e: list(e.absolute_path)):
        if kind == "campaign" and _dropped(error):
            continue
        parent = [str(p) for p in error.absolute_path]
        if error.validator == "required":
            present = error.instance if isinstance(error.instance, dict) else {}
            for prop in error.validator_value:
                key = ".".join(parent + [prop])
                if prop not in present and key not in seen:
                    seen.add(key)
                    ctx.out.add("E01", "required_key", path, None, key, key=key)
        else:
            key = ".".join(parent)
            ctx.out.add("E01", "schema_violation", path, None, key, key=key or "(root)", detail=error.message)


def _version_ok(version: str, accept_newer: bool) -> bool:
    if version == VERSION:
        return True
    m = re.fullmatch(r"(\d+)\.(\d+)", version)
    major, minor = (int(x) for x in VERSION.split("."))
    return bool(accept_newer and m and int(m[1]) == major and int(m[2]) > minor)


def run_manifest(ctx: Context) -> bool:
    """Validate the manifest; False means the remaining checks must be skipped."""
    if ctx.pkg.read_bytes(MANIFEST) is None:
        ctx.out.add("E01", "manifest_missing", MANIFEST)
        found = ctx.pkg.misplaced_manifests()
        if found:
            ctx.out.add("E01", "manifest_elsewhere", MANIFEST, found=", ".join(found))
        return True
    doc = _parse(ctx, MANIFEST)
    if doc is None:
        return True
    ctx.manifest = doc
    version = doc.get("version")
    if isinstance(version, str) and re.fullmatch(r"\d+\.\d+", version) and not _version_ok(version, ctx.accept_newer):
        ctx.out.add("E01", "version_unsupported", MANIFEST, None, "version", version=version, expected=VERSION)
        return False
    _schema_errors(ctx, MANIFEST, doc, "manifest")
    return True


def campaign_files(ctx: Context) -> dict[str, str]:
    """campaign id -> path, for campaigns/<id>.toml one level deep."""
    out = {}
    for name in ctx.pkg.names():
        m = CAMPAIGN_RE.fullmatch(name)
        if m and not ignored(name):
            out[m[1]] = name
    return dict(sorted(out.items()))


def run_campaigns(ctx: Context) -> None:
    files = campaign_files(ctx)
    if not files:
        ctx.out.add("E02", "no_campaigns", "campaigns/")
    for cid, path in files.items():
        doc = _parse(ctx, path)
        ctx.campaigns[cid] = doc
        if doc is None:
            continue
        _schema_errors(ctx, path, doc, "campaign")
        _check_standards(ctx, path, doc.get("standards"))
        _check_methods(ctx, path, doc.get("methods"))
        _check_fractions(ctx, path, doc.get("fractions"))


def _check_standards(ctx: Context, path: str, standards) -> None:
    if not isinstance(standards, dict):
        return
    for key, value in standards.items():
        if key not in TESTS and key not in RESERVED and not key.startswith("x_"):
            ctx.out.add("E10", "unknown_test", path, None, f"standards.{key}", key=key)
        elif isinstance(value, str) and value and not key.startswith("x_"):
            std = strip_year(value)
            if std != "unknown" and std not in STANDARDS_REGISTRY:
                ctx.out.add("W05", "unknown_standard", path, None, f"standards.{key}", standard=value)


def _check_methods(ctx: Context, path: str, methods) -> None:
    if not isinstance(methods, dict):
        return
    for key, value in methods.items():
        column = f"methods.{key}"
        if key.startswith("x_"):
            continue
        if key not in TESTS:
            ctx.out.add("E10", "unknown_test", path, None, column, key=key)
            continue
        allowed = TESTS[key]["methods"]
        if not allowed:
            ctx.out.add("E10", "unknown_method", path, None, column, allowed=[], method=value, test=key)
        elif value not in allowed:
            ctx.out.add("E10", "unknown_method", path, None, column, allowed=allowed, method=value, test=key)


def _check_fractions(ctx: Context, path: str, fractions) -> None:
    if not isinstance(fractions, dict) or not isinstance(fractions.get("source"), str):
        return
    source = fractions["source"]
    if source == "custom":
        if "upper_mm" not in fractions:
            ctx.out.add("E11", "custom_without_upper_mm", path, None, "fractions.upper_mm")
        return
    if strip_year(source) not in FRACTIONS_REGISTRY:
        ctx.out.add("E11", "fractions_source_unknown", path, None, "fractions.source", source=source)
    if "upper_mm" in fractions:
        ctx.out.add("E11", "upper_mm_not_custom", path, None, "fractions.upper_mm")
