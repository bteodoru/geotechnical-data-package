# Changelog

## Unreleased

Specification text aligned with the schema (English and Romanian):

- Keys: layers are identified by point and top depth; E05 lists the primary keys of each table.
- Unknown files: readers ignore them, the validator reports them (W02).
- E04 includes the bounds check (`out_of_bounds`): `final_depth` and `depth_top` ≥ 0, `area_ratio` in [0, 1].
- Types: `file_ref` added to the list in §3.
- Geotechnical units are part of the core (`units.csv`); `units` is linked from `layers.unit`, not through `point_id`.
- §13: design decisions 26–29 (package root in a zip, unknown columns not read, misplaced manifest, identifiers up to 64 characters).

Planned:

- `vertical_datum` required when any point has an `elevation`, checked by the validator as an error.

## 0.1.0 (draft)

First public version of GDP, for review and feedback. The format may still change.

- Specification v0.1 in English, with a Romanian translation: package structure, manifest and campaign files, core tables (points, units, layers, water, samples), profiles `lab_index` and `cpt`, 19 validation rules.
- Machine-readable schema `gdp-0.1.schema.json`, normative over the text: tables, fields, units (UCUM), vocabularies, registries, validation rules and message templates.
- Two CSV dialects (`,` with decimal point, `;` with decimal comma), detected per file; ISO dates; UTF-8.
- Reference validator (library and command line) with draft mode, text and JSON output, Romanian messages.
- SQLite importer for many projects in one database, with generated DDL.
- Two example packages and a pytest suite.
- Scope: soils only.
