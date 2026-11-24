# GDP — Geotechnical Data Package

An open file format for factual geotechnical investigation data (soils): CSV tables and TOML files in a zip (`.gdp`), with a machine-readable schema, a reference validator and a SQLite importer.

## Rules

- `gdp-0.1.schema.json` is the source of truth. The spec (`spec/gdp-0.1-spec.ro.md`), the DB DDL and the locale files must follow it; the schema wins on conflict.
- `gdp-0.1.db.sql` is generated (`python3 gdp_db.py ddl > gdp-0.1.db.sql`); never edit it by hand.
- Validator messages live only in the schema (`rules[*].checks`, English templates) and in `locales/gdp-<version>.<lang>.json`; never hardcode message text in Python.
- Check ids in `rules[*].checks` are stable once released.
- The tools are generic: no coupling to any specific consumer application.
- Code, schema, identifiers and commit messages in English.

## Layout

- `gdp_validator/` — validator library, one module per phase (documents, tables, refs, depths, lab, cpt, standards); `gdp_validate.py` — CLI.
- `gdp_db.py` — DDL generator and importer; validates every package before loading.
- `examples/` — test packages built by `make_examples.py`; both must validate with zero issues.
- `tests/` — pytest suite.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install "jsonschema>=4.18" "pytest>=8"
.venv/bin/python -m pytest
.venv/bin/python gdp_validate.py [--draft] [--format text|json] [--lang ro] PACKAGE
.venv/bin/python gdp_db.py load [--accept-newer] db.sqlite PACKAGE...
```

Python ≥ 3.11.
