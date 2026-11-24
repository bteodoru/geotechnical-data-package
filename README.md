# GDP — Geotechnical Data Package

GDP is an open file format for **factual geotechnical investigation data**: investigation points, described layering, groundwater, samples, laboratory index tests and CPT/CPTu. A package is a zip (`.gdp`) of plain CSV tables and small TOML files. It is readable without special tools and easy to produce from scripts or spreadsheets. A machine-readable schema lets software validate it, and helps both people and AI tools build it.

GDP keeps the idea behind AGS 4, a common exchange format for geotechnical data, but replaces its syntax:

| | AGS 4 | GDP |
|---|---|---|
| Layout | one file, many groups, GROUP/HEADING/UNIT/TYPE rows | one CSV per table |
| Names | 4-letter codes (`GEOL_TOP`) | readable names with the unit in the header (`depth_top[m]`) |
| Keys | composite keys | one identifier per entity, unique in the project |
| Context | repeated per row | per campaign: standards, methods and grain-size limits declared once |

**Status: v0.1, draft.** Soils only; rock mechanics is out of scope for now. The specification is currently written in Romanian.

## Package structure

```
project.gdp  (zip)
├── manifest.toml          identity: format, version, project (uuid), producer, profiles
├── campaigns/<id>.toml    procedural context per campaign: [standards], [methods], [fractions]
├── points.csv             investigation points (borehole, cpt, dp, trial_pit, well)
├── units.csv              optional: geotechnical units
├── layers.csv             described layering, each layer optionally in a unit
├── water.csv              groundwater observations
├── samples.csv            samples
├── lab/index.csv          profile lab_index: one row per sample (w, wL, wP, rho|gamma, rho_s|gamma_s, fractions)
├── cpt/tests.csv          profile cpt: one row per test
├── cpt/data/<test_id>.csv one dense series per test
└── attachments/           optional
```

The main rules:

- **Fixed SI units.** Each unit is written in the header (`depth[m]`, `qc[MPa]`), and there is no unit option.
- **Only measured quantities are stored.** Derived values such as IP, IC, qt or Ic are recomputed, so they cannot be inconsistent.
- **Extensions.** Custom columns take the `x_` prefix and are ignored by readers that do not know them.

A few rows of `points.csv`:

```csv
point_id,type,easting[m],northing[m],elevation[m],final_depth[m],date_start,date_end,method,remarks
F1,borehole,697412.35,634988.10,52.40,8.00,2026-10-14,2026-10-14,"rotary, dry, Ø 146 mm",
CPT1,cpt,697414.80,634986.55,52.38,10.20,2026-10-15,2026-10-15,,refusal at 10.20 m
```

A campaign file:

```toml
year = 2026

[standards]
water_content = "SR EN ISO 17892-1"
atterberg     = "SR EN ISO 17892-12"
cpt           = "SR EN ISO 22476-1"

[methods]
atterberg = "fall_cone"

[fractions]
source = "SR EN ISO 14688-1"
```

Two complete packages are in [`examples/`](examples/).

## Repository

| Path | What |
|---|---|
| [`gdp-0.1.schema.json`](gdp-0.1.schema.json) | The source of truth: tables, fields, types, units, keys, vocabularies, registries, validation rules and message templates. |
| [`spec/gdp-0.1-spec.ro.md`](spec/gdp-0.1-spec.ro.md) | Specification (Romanian). |
| [`locales/`](locales/) | Optional localizations: labels, synonyms and validator messages (Romanian). |
| [`gdp_validator/`](gdp_validator/), [`gdp_validate.py`](gdp_validate.py) | Reference validator: library and command line. |
| [`gdp_db.py`](gdp_db.py) | Imports packages into a multi-project SQLite database (DDL in [`gdp-0.1.db.sql`](gdp-0.1.db.sql), generated). |

## Validator

Requires Python ≥ 3.11.

```bash
python3 -m venv .venv && .venv/bin/pip install "jsonschema>=4.18"
.venv/bin/python gdp_validate.py examples/proiect_A.gdp
```

The validator applies all 19 rules of the schema: errors E01–E12 and warnings W01–W07. It reports every problem with its location:

```
layers.csv:3:depth_base[m] E07 depth_base (0.50) <= depth_top (0.60)
points.csv:2:type E10 foraj is not in point_type (allowed: borehole, cpt, dp, trial_pit, well)
2 errors, 0 warnings
```

Options:

- `--draft` reports what is still missing (a required column, a declared standard, a campaign) as a completeness list instead of errors. Contradictions remain errors.
- `--format json` gives a stable, machine-readable report.
- `--lang ro` gives Romanian messages.

Exit codes: 0 no errors, 1 errors, 2 the package cannot be opened.

From Python:

```python
from gdp_validate import validate

report = validate("examples/proiect_A.gdp", draft=True)
for issue in report.missing:
    print(issue.path, issue.row, issue.column, issue.message, issue.allowed)
```

Importing into SQLite (packages with errors are refused):

```bash
.venv/bin/python gdp_db.py load db.sqlite examples/proiect_A.gdp examples/proiect_B.gdp
```

Tests: `.venv/bin/pip install "pytest>=8" && .venv/bin/python -m pytest`.

## License

- The **specification text** ([`spec/`](spec/)) is licensed under [CC BY 4.0](spec/LICENSE).
- The **code, schema, locale files and examples** are licensed under the [MIT License](LICENSE).
