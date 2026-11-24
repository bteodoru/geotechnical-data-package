import json
import string
from pathlib import Path

from gdp_validate import main
from gdp_validator.schema import SCHEMA
from util import sub

ROOT = Path(__file__).resolve().parent.parent
LOCALE = json.loads((ROOT / "locales/gdp-0.1.ro.json").read_text(encoding="utf-8"))["entries"]


def _resolve(path: str) -> bool:
    obj = SCHEMA
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list):
            match = [x for x in obj if (isinstance(x, dict) and part in (x.get("name"), x.get("code"))) or x == part]
            if not match:
                return False
            obj = match[0]
        else:
            return False
    return True


def _fields(template: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(template) if f}


def _checks():
    for rule in SCHEMA["rules"]:
        for cid, spec in rule["checks"].items():
            yield f"rules.{rule['code']}.checks.{cid}", spec["message"]


def test_keys_resolve():
    assert [k for k in LOCALE if not _resolve(k)] == []


def test_all_checks_translated():
    assert [k for k, _ in _checks() if not LOCALE.get(k, {}).get("message")] == []


def test_same_placeholders():
    assert [k for k, en in _checks() if k in LOCALE and _fields(LOCALE[k]["message"]) != _fields(en)] == []


def test_e01_message():
    assert "fișierele de campanie" in LOCALE["rules.E01"]["message"]


def test_cli_ro(pkg_a, capsys):
    sub(pkg_a, "layers.csv", "F1,0.60,3.80", "F1,0.60,0.50")
    main(["--lang", "ro", str(pkg_a)])
    assert "layers.csv:3:depth_base[m] E07 depth_base (0.50) ≤ depth_top (0.60)" in capsys.readouterr().out
