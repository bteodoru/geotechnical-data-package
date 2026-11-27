# GDP — Geotechnical Data Package

GDP (Geotechnical Data Package) is a format for the factual data of a geotechnical investigation. People can read and write it by hand, with the tools they already use (a text editor or a spreadsheet), and software, AI assistants included, can validate it automatically and help generate it. Two established formats already cover this data. AGS 4 is widely used, but its syntax and its dependence on a data dictionary make it hard to write or check by hand. DIGGS is comprehensive, but its XML/GML representation is verbose and hard to write, read or check by hand. GDP aims to be simpler than both: a package is a folder of plain CSV tables, distributed as a zip file and described by a small TOML manifest and one file per investigation campaign.

Compared with AGS 4 and DIGGS:

| | AGS 4 | DIGGS 2.6 | GDP |
|---|---|---|---|
| Layout | one or more `.ags` files, each with several groups (GROUP/HEADING/UNIT/TYPE rows) | one XML/GML document: `samplingFeature`, `sample`, `observation`, `measurement`… with nested properties | one CSV per table |
| Names | abbreviated codes (`GEOL_TOP`) | namespaced XML elements (`totalMeasuredDepth`) | readable names with the unit in the header (`depth_top[m]`) |
| Keys | `LOCA_ID` for locations; composite keys in child groups (`LOCA_ID`, `GEOL_TOP`, `GEOL_BASE`) | `gml:id` on identifiable objects, referenced with `xlink:href="#id"` | one identifier per entity, unique in the project |
| Units | declared per group in the UNIT row | given with measured values (`uom="m"`), depending on the data type | fixed per field, written once in the header |
| Context | standards in `STND`, methods in test fields (`*_METH`) | a `procedure` with each test | per campaign: standards, methods and grain-size limits declared once |
| Manual authoring | possible, with the data dictionary at hand | possible, but verbose | designed for a text editor or a spreadsheet |

**Status: v0.1, draft.** Soils only; rock mechanics is out of scope for now. The schema is normative and in English; the specification text is currently written in Romanian.

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
└── attachments/           optional: source documents (PDF, GEF…), referenced by source_file
```

The main rules:

- **One standard and one method per test, per campaign.** Each campaign file declares the standard and the method of every test it contains. A different standard or method means a different campaign. A sample can override the campaign of its point, for example a verification duplicate tested elsewhere.
- **A package is a complete snapshot of one project.** The project has a mandatory `project.uuid`, generated once and kept across package versions. Importing a package replaces everything stored for that project, so many packages can share one database without key collisions.
- **Spreadsheet-friendly CSV.** A table may use either of the two dialects that spreadsheets write, depending on regional settings: `,` with a decimal point, or `;` with a decimal comma. Each file's dialect is read from its header row. Dates are ISO (`2026-10-14`) and files are UTF-8, so a table prepared with the GDP columns and saved as "CSV UTF-8" is valid as it is.
- **Fixed SI units.** Each unit is written in the header (`depth[m]`, `qc[MPa]`), spelled as in UCUM, and there is no unit option.
- **Only measured quantities are stored.** Derived values such as IP, IC or qt are recomputed, so they cannot be inconsistent.
- **Extensions.** Custom columns take the `x_` prefix and are ignored by readers that do not know them.
- **Source documents.** Any point, layer, water observation, sample, lab row or CPT test can name its source in `attachments/` (`source_file`, optionally `#page=N`), so every value can be checked against the page it came from.
- **Linear works.** Points can also carry a chainage and an offset from an alignment (`station[m]`, `offset[m]`, `alignment`). The alignment is only named, not described in the package, so the chainage is informative and the coordinates remain authoritative.

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

## Relation to AGS and DIGGS

GDP builds mainly on AGS 4. From it, GDP takes the organisation of data into one table per kind of record, the link from records to their source documents (`FILE_FSET`), and linear referencing: `LOCA_CNGE`, `LOCA_OFFS` and `LOCA_ALID` become `station`, `offset` and `alignment`, with a fixed unit and a sign convention added. AGS 4 also groups locations by investigation phase (`LOCA_CLST`). GDP campaigns play a similar role, but they also carry the standards and methods of their tests, and a sample can belong to a different campaign than its location. DIGGS 2.6 describes the same kind of location with a `Locality` (`route`, `station`, `offset`, `offsetDirection`), which any sampling feature can have, boreholes included. GDP's signed offset converts to the DIGGS pair `offset` and `offsetDirection`, so GDP locations can be mapped to either format, although the structures are not identical. GDP is meant to work alongside AGS 4 and DIGGS rather than replace them.

## License

- The **specification text** ([`spec/`](spec/)) is licensed under [CC BY 4.0](spec/LICENSE).
- The **code, schema, locale files and examples** are licensed under the [MIT License](LICENSE).
