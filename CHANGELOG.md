# Changelog

## 0.1.0 (draft)

First public version of GDP, for review and feedback. The format may still change.

- Specification v0.1 in English, with a Romanian translation: package structure, manifest and campaign files, core tables (points, units, layers, water, samples), profiles `lab_index` and `cpt`, 19 validation rules.
- Machine-readable schema `gdp-0.1.schema.json`, normative over the text: tables, fields, units (UCUM), vocabularies, registries, validation rules and message templates.
- Two CSV dialects (`,` with decimal point, `;` with decimal comma), detected per file; ISO dates; UTF-8.
- Reference validator (library and command line) with draft mode, text and JSON output, Romanian messages.
- SQLite importer for many projects in one database, with generated DDL.
- Two example packages and a pytest suite.
- Scope: soils only.
