# GDP (Geotechnical Data Package) — core v0.1 (draft)

Version 0.1 (draft), 2026-11-28 · Bogdan Teodoru

The machine-readable schema [`gdp-0.1.schema.json`](../gdp-0.1.schema.json) is normative: where this text and the schema disagree, the schema prevails. A Romanian translation of this text is in [`gdp-0.1-spec.ro.md`](gdp-0.1-spec.ro.md).

## 1. Purpose and principles

GDP (Geotechnical Data Package) is a format for the factual data of a geotechnical investigation. People can read and write it by hand, with the tools they already use (a text editor or a spreadsheet), and software, AI assistants included, can validate it automatically and help generate it. Two established formats already cover this data. AGS 4 is widely used, but its syntax and its dependence on a data dictionary make it hard to write or check by hand. DIGGS is comprehensive, but its XML/GML representation is verbose and hard to write, read or check by hand. GDP aims to be simpler than both: a package is a folder of plain CSV tables, distributed as a zip file and described by a small TOML manifest and one file per investigation campaign.

The v0.1 core covers the factual data of an investigation: investigation points, layering, groundwater, samples, laboratory index tests and CPT/CPTu. Interpretation (geotechnical units, characteristic values, ground model) stays outside the core. The format is limited to soils; rocks belong to rock mechanics and are out of scope for now. The package extension is `.gdp`.

- **CSV, spreadsheet-friendly.** Tables are plain CSV files, in one of the two dialects that spreadsheets write depending on regional settings: `,` with a decimal point, or `;` with a decimal comma. A table prepared with the columns of this specification, with ISO dates and saved as "CSV UTF-8", is valid without regional settings and without a converter (section 8). The format has no xlsx form.
- **One table = one file.** No GROUP/UNIT/TYPE rows and no unnecessary quotes.
- **Readable names, with the unit in the header:** `depth_top[m]`, not `GEOL_TOP`. Unit symbols are written in UCUM, case-sensitive variant (`Mg/m3`, `kN/m3`, `cm2`, `deg`).
- **Simple keys.** Each entity has a single identifier, unique in the project. There are no composite keys.
- **Only measured quantities are stored.** Derived quantities (IP, IC, qt, Rf, Bq, Ic) are recomputed, so they cannot be inconsistent.
- **Small core + separately versioned profiles** (`cpt`, `lab_index`). The package declares which profiles it uses.
- **Extensible without negotiation.** Custom columns take the `x_` prefix and are ignored by readers that do not know them.

## 2. Package structure

A `.gdp` package is a zip with fixed paths. `manifest.toml`, `points.csv` and at least one file in `campaigns/` are required. The other files appear only if there is data for them. If the zip has no `manifest.toml` at its root but holds a single folder that has one, as Finder "Compress" and Windows "Send to → Compressed folder" produce, that folder is the package root; archiver metadata (`__MACOSX/`, `.DS_Store`, `._*`) is ignored, and paths in messages are relative to the package root. The rule is for zips only, where the extra level comes from the archiver: a folder given to the validator or the importer must be the package root itself. When `manifest.toml` is missing from the root but exists elsewhere in the package, the validator says where (E01) and runs no other checks.

```
project.gdp
├── manifest.toml          identity: format, project, producer, profiles
├── campaigns/
│   ├── C2016.toml         procedural context: standards, methods, fractions
│   └── C2026.toml
├── points.csv             investigation points (boreholes, CPTs, pits…)
├── units.csv              geotechnical units (horizons)
├── layers.csv             described layering
├── water.csv              groundwater observations
├── samples.csv            samples
├── lab/
│   └── index.csv          profile lab_index: water content, limits, densities, fractions
├── cpt/
│   ├── tests.csv          profile cpt: one row per test
│   └── data/
│       ├── CPT1.csv       dense series of test CPT1
│       └── CPT2.csv
└── attachments/           optional: PDFs, photos, original logs, referenced by source_file
```

The files are linked through these keys:

```
points.point_id ─┬─ layers, water, samples, cpt/tests
                 │
units.unit_id    ── layers.unit
samples.sample_id ── lab/index
cpt/tests.test_id ── cpt/data/<test_id>.csv        (the key is the file name)
points.campaign  ─┬─ campaigns/<campaign>.toml     (the key is the file name)
samples.campaign ─┘
```

The unit of a sample, or of a depth in a CPT series, is not written anywhere. It is derived: point + depth → layer → unit (section 5.5).

A reader ignores files it does not know. So a v0.2 package with a new profile remains readable for a v0.1 reader.

## 3. General conventions

The rules below apply to all tables.

| Aspect                  | Rule                                                                                                                                                                                          |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Text encoding           | UTF-8. A BOM is accepted, because Excel writes one for "CSV UTF-8".                                                                                                                           |
| Separator, decimal mark | Two dialects: `,` between fields with `.` as decimal mark, or `;` between fields with `,` as decimal mark. The dialect is detected from the first row of each file: it is the one whose separator is the only one present in the header (column names do not contain `,` or `;`), otherwise the first. The decimal mark is tied to the separator, so `1.234` in a file separated by `;` is an error. No thousands separator. Quotes only when the value contains the separator, quotes or a line break (RFC 4180). The files of one package may use different dialects; software that writes GDP uses the first dialect. |
| Header                  | First row. The column name is exactly the one in the specification, with the unit in square brackets: `depth_top[m]`. Dimensionless quantities have no brackets.                              |
| Units                   | SI, fixed by the specification for each column. The unit in the header must match the specified one (v0.1 does no conversions).                                                               |
| Missing value           | Empty cell. `-999`, `N/A`, `-` are not used.                                                                                                                                                  |
| Types                   | `id`, `text`, `number`, `integer`, `date` (`YYYY-MM-DD`, ISO form only), `datetime` (ISO 8601 with UTC offset, `2026-10-14T09:30+03:00`), `bool` (`true`/`false`), `code` (from a code list). |
| Identifiers             | Characters `A–Z a–z 0–9 _ - .`, no spaces, at most 64 characters, case-sensitive. They are also used as file names. Identifiers that start with a letter are recommended (`F1`, `P1`, `F1-P2bis`), so that spreadsheets do not turn them into dates or numbers and do not drop leading zeros. |
| Depths                  | Metres below ground level at the point, positive downwards. An interval is `[depth_top, depth_base)`, with `depth_top < depth_base`. The last interval of a point also includes its base, when the base equals `final_depth`. |
| Elevations              | Metres relative to the vertical datum declared in the manifest (for example Marea Neagră 1975, the Romanian Black Sea datum).                                                                 |
| Coordinates             | One CRS per project, declared in the manifest as an EPSG code (for example `EPSG:3844`, Stereo 70). The columns are named `easting` and `northing`, to avoid the X/Y ambiguity of Stereo 70.  |
| Verticality             | v0.1 assumes vertical points. Inclined boreholes are an open decision.                                                                                                                        |
| Custom columns          | Prefix `x_` (for example `x_lab_ref`). They are not validated and are kept in conversions.                                                                                                    |

## 4. Manifest and campaigns

The context of a package is in two places. `manifest.toml` says what the package is, and each `campaigns/<id>.toml` file says how the data of one campaign were obtained. Units and the choice between ρ and γ are declared in neither: they are in the column headers.

The examples in this specification come from a Romanian project and are kept as they are: descriptions in Romanian, Stereo 70 coordinates and SR EN ISO standard designations; text in a package can be in any language.

### 4.1 `manifest.toml`

The manifest has about 20 lines and does not grow with the data. The key `project.uuid` identifies the project globally. It is generated once, when the project is created, and does not change in later versions of the package. Without GDP tools it can be obtained with `uuidgen` (macOS, Linux) or with `New-Guid` in PowerShell (Windows). `project.id` remains the internal, readable code of the project.

A package is always a **complete snapshot** of the project, not a difference from an earlier version. A database that imports the package replaces everything it held for that `project.uuid`. The version is recognised by `producer.date`. In the database, the key of each entity becomes the pair (project, local identifier), for example (`project.uuid`, `point_id`).

```toml
format  = "gdp"          # required
version = "0.1"          # core version; required

[project]
uuid           = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"  # required; generated once
id             = "IS-2026-014"                         # required
name           = "Clădire socială, extindere anexă"    # required
location       = "Iași, jud. Iași"
client         = ""
crs            = "EPSG:3844"                           # required
vertical_datum = "Marea Neagră 1975"                   # required if there are elevations

[producer]
organisation = ""
author       = ""
date         = 2026-11-24       # date the package was generated
software     = "exemplu 1.4"    # optional, useful for debugging

[profiles]
cpt       = "0.1"
lab_index = "0.1"
```

### 4.2 `campaigns/<id>.toml`

A campaign is a stage of the investigation: a different period, purpose or contractor. Each file declares the complete procedural context of the campaign, with no default values and no inheritance from other files. The file name is the campaign identifier.

```toml
# campaigns/C2026.toml
description  = "Studiu geotehnic pentru autorizare"
organisation = "Laborator Y"
year         = 2026

[standards]
water_content    = "SR EN ISO 17892-1"
bulk_density     = "SR EN ISO 17892-2"
particle_density = "SR EN ISO 17892-3"
grain_size       = "SR EN ISO 17892-4"
atterberg        = "SR EN ISO 17892-12"
cpt              = "SR EN ISO 22476-1"

[methods]
bulk_density = "linear_measurement"
grain_size   = "sieving_hydrometer"
atterberg    = "fall_cone"

[fractions]
source = "SR EN ISO 14688-1"
```

```toml
# campaigns/C2016.toml — old data, partial information
description  = "Studiu geotehnic preliminar"
organisation = "Laborator X"
year         = 2016

[standards]
water_content = "unknown"
atterberg     = "unknown"
grain_size    = "unknown"

[methods]
atterberg = "casagrande"

[fractions]
source   = "custom"
upper_mm = { clay = 0.005, silt = 0.05, sand = 2.0, gravel = 70.0 }   # illustrative values
```

| Section        | Content                                                                                                                                                                                         |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| top-level keys | `description`, `organisation`, `year`, all optional.                                                                                                                                            |
| `[standards]`  | The standard of each test that has data in the campaign, as text. For old data without this information, `"unknown"` is written explicitly. A test with data but no standard is an error (E11). |
| `[methods]`    | The method of determination, where the standard allows several. Optional; missing = unspecified.                                                                                                |
| `[fractions]`  | The standard that defines the limits of the grain-size fractions. For a known standard, `source` is enough, and the limits are taken from the implementation's reference table. With `source = "custom"`, the upper limits are given in `upper_mm`, in mm. |

### 4.3 Linking data to campaigns

- A point names a campaign in `points.campaign`. The layers, water observations, samples and CPT tests of the point belong to the same campaign.
- A sample can have its own campaign, in `samples.campaign`. When it is filled in, it replaces the point's campaign for that sample and for its laboratory tests. This is the case of verification duplicates: `F1-P2bis` from verification campaign V2026, for example.
- When the package has a single campaign, the `campaign` columns may stay empty. When it has several, every point must name one (E06).

The resulting rule: **within a campaign, a test is done with one standard and one method.** Any other combination means another campaign.

### 4.4 Vocabulary: test keys and method codes

The vocabulary is closed. A campaign file uses only the keys and codes below, plus extensions with the `x_` prefix. A method code exists only where the standard describes distinct methods.

**A test key is the unit for which a campaign declares one standard and one method.** What can vary from one test to another in the same campaign is not declared in the campaign. If it defines the type of test, it is part of the key; if it is a test condition (for example the consolidation stress), it is a column in the profile data. For strength tests, the drainage condition is part of the key (`triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`…): UU and CU have different standards (SR EN ISO 17892-8 and 17892-9) and often appear in the same campaign. Separate keys do not mean separate tables: a profile can hold several keys in one table, with a column that names the key of each row.

| Key                | Quantities                       | Reference standard | `method` codes                                                                                   |
| ------------------ | -------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------ |
| `water_content`    | `w`                              | SR EN ISO 17892-1  | — (a single method)                                                                              |
| `bulk_density`     | `rho` / `gamma`                  | SR EN ISO 17892-2  | `linear_measurement`, `immersion`, `fluid_displacement`                                          |
| `particle_density` | `rho_s` / `gamma_s`              | SR EN ISO 17892-3  | `fluid_pycnometer`, `gas_pycnometer`                                                             |
| `grain_size`       | `clay`, `silt`, `sand`, `gravel` | SR EN ISO 17892-4  | `sieving`, `sieving_hydrometer`, `sieving_pipette`, `hydrometer`, `pipette`, `laser_diffraction` |
| `atterberg`        | `wL`, `wP`                       | SR EN ISO 17892-12 | `fall_cone`, `casagrande` (the method refers to wL)                                              |
| `cpt`              | profile `cpt`                    | SR EN ISO 22476-1  | —                                                                                                |

The methods are those described in each standard: three for density ([ISO 17892-2](https://www.iso.org/standard/55244.html)), two pycnometers ([ISO 17892-3](https://www.iso.org/standard/55245.html)), sieving and two sedimentation methods ([ISO 17892-4](https://www.iso.org/standard/55246.html)), the fall cone and the Casagrande cup ([ISO 17892-12](https://www.iso.org/standard/72017.html)). Three further rules:

- **`fall_cone` does not distinguish between the 80 g/30° cone and the 60 g/60° cone.** The 2004 version of the standard adopted both because they give practically the same value of wL ([ISO/TS 17892-12:2004](https://www.iso.org/standard/38525.html)), so the difference does not justify a separate code.
- **Grain-size codes describe the complete combination** (`sieving_hydrometer`), not a list, so that the value stays plain text. `laser_diffraction` is not part of SR EN ISO 17892-4 and is declared with its own standard.
- **An undeclared method is unspecified.** There is no `unknown` code for methods.

**Reserved keys** for future profiles, with no method codes yet: `oedometer`, `unconfined_compression`, `triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`, `direct_shear_cu`, `direct_shear_cd`, `permeability`, `compaction`, `organic_content`, `carbonate_content`, `swelling`, `collapse`. The last two cover soils with high swelling and shrinkage and soils sensitive to wetting (collapsible soils), specific to Romanian practice. Their standards are still to be set.

**Standards are text.** They are written as on the cover, without the year (`SR EN ISO 17892-12`); the year may be added after a colon (`SR EN ISO 17892-12:2018`). The reference implementation keeps a registry of known standards. An unrecognised standard gives a warning (W05), not an error, so that new or old standards do not block the package.

TOML was chosen over YAML because it has no indentation traps and does not silently turn `no` into a boolean.

## 5. Core tables

The core has five tables, with 40 columns in total, of which 18 are required. All are linked to `points` through `point_id`.

### 5.1 `points.csv`: investigation points

One row per point: borehole, CPT, dynamic probe, trial pit or well.

| Column           | Type     | Required    | Description                                                                                                                                                                                                            |
| ---------------- | -------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `point_id`       | id       | yes         | Identifier, unique in the project (`F1`, `CPT1`).                                                                                                                                                                      |
| `type`           | code     | yes         | `borehole`, `cpt`, `dp`, `trial_pit`, `well`.                                                                                                                                                                          |
| `campaign`       | id       | no          | The campaign the point belongs to, with the file `campaigns/<id>.toml`. May stay empty only when the package has a single campaign.                                                                                    |
| `easting[m]`     | number   | yes         | Easting in the CRS of the manifest.                                                                                                                                                                                    |
| `northing[m]`    | number   | yes         | Northing in the CRS of the manifest.                                                                                                                                                                                   |
| `elevation[m]`   | number   | recommended | Ground elevation at the point.                                                                                                                                                                                         |
| `final_depth[m]` | number   | yes         | Final depth reached.                                                                                                                                                                                                   |
| `station[m]`     | number   | no          | Chainage along the alignment of a linear work (embankment, road, canal), in metres: km 12+345.60 is written `12345.60`. Required if `offset` is present.                                                               |
| `offset[m]`      | number   | no          | Distance from the alignment, positive to the right looking towards increasing station, negative to the left.                                                                                                           |
| `alignment`      | text     | no          | Name of the alignment that `station` refers to, when the project has several (`dig`, `canal`). The alignment is not described in the package, so the chainage is informative and the coordinates remain authoritative. |
| `date_start`     | date     | no          | Start date.                                                                                                                                                                                                            |
| `date_end`       | date     | no          | End date.                                                                                                                                                                                                              |
| `method`         | text     | no          | Method and equipment, free text ("rotativ uscat, Ø 146 mm").                                                                                                                                                           |
| `source_file`    | file_ref | no          | Source document in `attachments/` (5.6).                                                                                                                                                                               |
| `remarks`        | text     | no          | Remarks.                                                                                                                                                                                                               |

### 5.2 `layers.csv`: layering

One row per layer described at a point. The layers of a point do not overlap. Lenses and interbeds are described as separate layers, but they take the unit that hosts them.

| Column          | Type     | Required | Description                                                  |
| --------------- | -------- | -------- | ------------------------------------------------------------ |
| `point_id`      | id       | yes      | Reference to `points`.                                       |
| `depth_top[m]`  | number   | yes      | Top of the layer.                                            |
| `depth_base[m]` | number   | yes      | Base of the layer.                                           |
| `description`   | text     | yes      | The complete description, as it appears in the borehole log. |
| `soil_symbol`   | code     | no       | SR EN ISO 14688-2 symbol (`clSi`, `saGr`, `Mg`).             |
| `unit`          | id       | no       | The geotechnical unit the layer belongs to, from `units`.    |
| `source_file`   | file_ref | no       | Source document in `attachments/` (5.6).                     |

### 5.3 `water.csv`: groundwater

One row per observation. This way the same structure covers both the level struck while drilling and repeated readings in a piezometer.

| Column        | Type     | Required | Description                                                                              |
| ------------- | -------- | -------- | ---------------------------------------------------------------------------------------- |
| `point_id`    | id       | yes      | Reference to `points`.                                                                   |
| `kind`        | code     | yes      | `struck` (struck while drilling), `stable` (stabilised), `reading` (monitoring reading). |
| `depth[m]`    | number   | yes      | Depth of the water level.                                                                |
| `datetime`    | datetime | no       | Time of the observation.                                                                 |
| `source_file` | file_ref | no       | Source document in `attachments/` (5.6).                                                 |
| `remarks`     | text     | no       | Remarks ("aparție lentă, 20 min").                                                       |

### 5.4 `samples.csv`: samples

One row per sample. `sample_id` is unique in the whole project, not only in the borehole. This is the main difference from the composite key of AGS (LOCA_ID + SAMP_TOP + SAMP_REF + SAMP_TYPE + SAMP_ID). A sample tested in parallel or for verification is recorded as a separate sample, with a suffix (F1-P2a, F1-P2bis).

| Column          | Type     | Required | Description                                                                                                         |
| --------------- | -------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `sample_id`     | id       | yes      | Identifier, unique in the project (`F1-P1`).                                                                        |
| `point_id`      | id       | yes      | Reference to `points`.                                                                                              |
| `campaign`      | id       | no       | Replaces the point's campaign for this sample (for example a verification duplicate). Empty = the point's campaign. |
| `depth_top[m]`  | number   | yes      | Sampling depth, or top of the interval.                                                                             |
| `depth_base[m]` | number   | no       | Base of the interval. Empty = point sample.                                                                         |
| `kind`          | code     | yes      | `undisturbed`, `disturbed`, `core`, `water`.                                                                        |
| `source_file`   | file_ref | no       | Source document in `attachments/` (5.6).                                                                            |
| `remarks`       | text     | no       | Remarks.                                                                                                            |

### 5.5 `units.csv`: geotechnical units

A unit groups layers with similar properties, which are treated together in the overall description, in the ground model (NP 074, the Romanian code for geotechnical reports) and when characteristic values are set. The neutral term `unit` avoids the dispute between unit, horizon and stratum, and corresponds to the geotechnical units of the ground model in the new Eurocode 7. The table is optional: a package without `units.csv` holds only the described layering.

| Column        | Type | Required | Description                                                          |
| ------------- | ---- | -------- | -------------------------------------------------------------------- |
| `unit_id`     | id   | yes      | Identifier, unique in the project (`U1`, `U2`).                      |
| `name`        | text | yes      | Name of the unit ("Argile prăfoase și prafuri argiloase loessoide"). |
| `description` | text | no       | Overall description.                                                 |
| `remarks`     | text | no       | Remarks.                                                             |

A unit has no order column. The order at an investigation point follows from the depths of the layers, and the order between points follows from elevations (`elevation` minus depth). A unit may be absent from an investigation point, or be the first at one point and the third at another.

The unit is derived, not written, for samples and CPT series:

1. The reference depth of a sample is the midpoint of the interval `[depth_top, depth_base]`, or `depth_top` for a point sample.
2. The sample belongs to the layer of the point in which this depth falls. Layer intervals are `[top, base)`, so a boundary between layers belongs to the layer below. Exception: the base of the last layer, when it equals final_depth, belongs to the last layer.
3. The sample takes the unit of the layer.

For CPT series, each depth falls in a layer of the CPT point. The layering of a CPT point is the one interpreted from the test and is entered in `layers` as for any other point. Excluding a sample from the calculation of characteristic values is a design decision and belongs to the interpretation profile, not to the samples table.

### 5.6 Source documents: `source_file`

The tables `points`, `layers`, `water`, `samples`, `lab_index` and `cpt_tests` have the optional column `source_file`, which names the document the row comes from: the borehole log, the laboratory report, the original GEF file. The value is the path relative to `attachments/` (`buletin_lab_2026.pdf`, `fise/F1.pdf`). For a PDF the page may also be given, after `#page=` (`buletin_lab_2026.pdf#page=3`, the first page being 1). The file must exist in the package (E06). This way every value can be checked against the document it was taken from, including when it was extracted automatically.

## 6. Profile `cpt` (v0.1)

The profile separates the test metadata from the dense series. The metadata are in a small table; each series has its own file, with no key repeated on its rows. A 30 m CPTu recorded every 2 cm has about 1,500 rows, that is about 50 KB as CSV and less than 20 KB in the zip.

### 6.1 `cpt/tests.csv`

| Column              | Type     | Required     | Description                                                                                 |
| ------------------- | -------- | ------------ | ------------------------------------------------------------------------------------------- |
| `test_id`           | id       | yes          | Identifier of the test. It also gives the name of the data file.                            |
| `point_id`          | id       | yes          | Reference to `points` (usually of type `cpt`). The test inherits the campaign of the point. |
| `date`              | date     | yes          | Date of the test.                                                                           |
| `cone_area[cm2]`    | number   | yes          | Cone area: 10 or 15.                                                                        |
| `area_ratio`        | number   | yes for CPTu | Area ratio _a_, needed for qt = qc + u2(1 − a).                                             |
| `filter_position`   | code     | yes for CPTu | `u1`, `u2`, `u3`.                                                                           |
| `predrill_depth[m]` | number   | no           | Predrilled depth, without data.                                                             |
| `equipment`         | text     | no           | Penetrometer and cone ("Geomil 200 kN, con S15CFIIP").                                      |
| `source_file`       | file_ref | no           | Source document in `attachments/`, for example the original GEF file (5.6).                 |
| `remarks`           | text     | no           | Remarks (refusal, deviation from the vertical).                                             |

### 6.2 `cpt/data/<test_id>.csv`

One row per depth. The file holds only data; all metadata are in `tests.csv`.

| Column             | Type   | Required | Description                                                     |
| ------------------ | ------ | -------- | --------------------------------------------------------------- |
| `depth[m]`         | number | yes      | Penetration length, strictly increasing.                        |
| `qc[MPa]`          | number | yes      | Measured cone resistance (uncorrected).                         |
| `fs[kPa]`          | number | yes      | Sleeve friction.                                                |
| `u[kPa]`           | number | no       | Pore water pressure at the position given in `filter_position`. |
| `inclination[deg]` | number | no       | Inclination from the vertical.                                  |

qt, Rf, Bq, Qt, Fr and Ic are not stored. They are obtained from the columns above and from `area_ratio`.

Series enter the package through importers from instrument formats, not by typing. The first proposed importer is GEF (the Dutch text format for CPT).

Dissipation tests and seismic SCPT are not part of v0.1.

## 7. Profile `lab_index` (v0.1)

One row per sample, with one column for each measured quantity. This is the form in which laboratories already work in Excel. The profile covers the index properties used in almost every investigation; mechanical tests (oedometer, shear, triaxial) will be separate profiles.

| Column                             | Type     | Description                                                                    |
| ---------------------------------- | -------- | ------------------------------------------------------------------------------ |
| `sample_id`                        | id       | Reference to `samples`. Required.                                              |
| `w[%]`                             | number   | Natural water content.                                                         |
| `wL[%]`                            | number   | Liquid limit.                                                                  |
| `wP[%]`                            | number   | Plastic limit.                                                                 |
| `rho[Mg/m3]` or `gamma[kN/m3]`     | number   | Bulk density, or bulk unit weight, in the natural state.                       |
| `rho_s[Mg/m3]` or `gamma_s[kN/m3]` | number   | Particle density, or unit weight of the solid particles.                       |
| `clay[%]`                          | number   | Fraction below the `clay` limit of the `[fractions]` of the sample's campaign. |
| `silt[%]`                          | number   | Between the `clay` and `silt` limits.                                          |
| `sand[%]`                          | number   | Between the `silt` and `sand` limits.                                          |
| `gravel[%]`                        | number   | Between the `sand` and `gravel` limits.                                        |
| `source_file`                      | file_ref | The laboratory report in `attachments/` (5.6).                                 |
| `remarks`                          | text     | Remarks.                                                                       |

The header decides between density and unit weight. A `lab_index` file holds either the pair `rho`/`rho_s` or the pair `gamma`/`gamma_s`, never both (E12). For the conversion between them, the specification fixes g = 9.81 m/s², so that all implementations give the same result. The standard and the method do not appear in the table: they belong to the campaign of the sample (section 4.2).

IP, IC, e, n, Sr and ρd (or γd) were deliberately left out, because they are calculated from the columns above. The complete grain-size curve will be a separate profile, with one series per sample, built on the same model as the CPT series.

## 8. Spreadsheets (informative)

This section adds no rules. It describes the pitfalls met when a table is prepared in a spreadsheet (Excel, LibreOffice, Numbers) and exported as CSV.

- **The table.** The header from the specification on the first row and the data from row 2, with no merged cells, no total rows and no unit on a separate row. Each table is exported separately, with the file name from the specification.
- **The separator and the decimal mark need no settings.** The export uses the regional settings of the system, so `,` with `.` or `;` with `,`. Both dialects are valid (3).
- **Dates** are exported in the displayed format, for example `14.10.2026`, which is not valid. Date columns are formatted `yyyy-mm-dd` before export.
- **Encoding.** Choose "CSV UTF-8". Plain "CSV" writes in the local encoding of the system (MacRoman, Windows-1250, Windows-1252), and diacritics are lost.
- **Values are exported as displayed.** A column formatted with one decimal loses the rest, and a number displayed as `1,23E+05` comes out as 123000. Trailing zeros disappear (`52.40` becomes `52.4`), which is valid.
- **An existing CSV is not corrected in Excel.** On opening, Excel interprets the dates and writes them back in the local format on saving. A file without a BOM may be read in the wrong encoding, and the text is corrupted without the validator being able to notice (`Ø` becomes `√ò`). An existing CSV is corrected in a text editor. To view one in Excel, use the import (Data → From Text/CSV), with UTF-8 encoding.
- **Identifiers** that start with a digit (`1-2`, `3.10`, `007`) may become dates or numbers, and leading zeros are lost. Identifiers that start with a letter are recommended (3).
- **Separators are not replaced with search and replace.** Commas in text, for example `rotativ uscat, Ø 146 mm`, would change without a trace. It is not needed, because both dialects are valid.

## 9. Validation rules

Validation has 19 rules: 12 errors, which make the package invalid, and 7 warnings. All of them can be checked mechanically. No rule requires reading a separate document.

| Code | Level   | Rule                                                                                                                                                                                  |
| ---- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E01  | error   | `manifest.toml` exists and has `format`, `version`, `project.uuid` (a valid UUID), `project.id`, `project.name`, `project.crs`. The manifest and the campaign files are valid TOML and match their schemas; test keys and methods belong to E10, fractions to E11. |
| E02  | error   | `points` has at least one row, and `campaigns/` has at least one file.                                                                                                                |
| E03  | error   | Each table present is CSV in UTF-8, in one of the two dialects (3), and has all the required columns, with exact name and unit.                                                       |
| E04  | error   | Values can be read as the column type (numbers with the decimal mark of the file's dialect, dates in ISO form), and required fields are not empty.                                    |
| E05  | error   | `point_id`, `unit_id`, `sample_id` and `test_id` are unique in their tables.                                                                                                          |
| E06  | error   | All references resolve: every `point_id` in `layers` exists in `points`, every `layers.unit` exists in `units`, every `campaign` in `points` and `samples` has the file `campaigns/<campaign>.toml`, and so on. With several campaigns, every point names one. Every `source_file` names an existing file in `attachments/`. |
| E07  | error   | `depth_top < depth_base`, and all depths are within [0, `final_depth`] of the point.                                                                                                  |
| E08  | error   | The layers of a point do not overlap.                                                                                                                                                 |
| E09  | error   | Every `test_id` has its data file, and every data file has a `test_id`. In each file, `depth` is strictly increasing.                                                                 |
| E10  | error   | Values in `code` columns are in the code list, and `wL ≥ wP`. The keys in `[standards]` and `[methods]` and the method codes come from the vocabulary in 4.4 or have the `x_` prefix. |
| E11  | error   | For each test with data, the campaign of the row declares the standard in `[standards]` (a standard or `"unknown"`). If there are grain-size fractions, `[fractions].source` is a known standard, or `"custom"` with a complete `upper_mm`. |
| E12  | error   | `lab_index` holds either `rho`/`rho_s` or `gamma`/`gamma_s`, not both pairs.                                                                                                          |
| W01  | warning | There are gaps between the layers of a point, or the layering does not start at 0 or does not reach `final_depth`.                                                                    |
| W02  | warning | An unknown column without the `x_` prefix. It is probably a typing error.                                                                                                             |
| W03  | warning | Values outside plausible ranges: `w > 150 %`, `qc > 100 MPa`, `rho` outside [1.2, 2.6] Mg/m³ (the equivalent in kN/m³ for `gamma`).                                                   |
| W04  | warning | The sum of the grain-size fractions differs from 100 % by more than ±1 %.                                                                                                             |
| W05  | warning | A standard in `[standards]` is not in the registry of the implementation. It may be a new standard, an old one or a misspelling.                                                      |
| W06  | warning | The reference depth of a sample falls in no layer of the point, so its unit cannot be derived.                                                                                        |
| W07  | warning | The package has `units.csv`, but a layer has no `unit`.                                                                                                                               |

The reference validator reports each problem with the file, the row and the column. Example: `layers.csv:14:depth_base[m] E07 depth_base (3.20) ≤ depth_top (3.40)`.

**Sub-checks and messages.** In the schema (`rules[*].checks`), each rule has one or more sub-checks, each with a stable identifier and an English message template with parameters in braces: E07 has `top_not_above_base` and `beyond_final_depth`, for example. A locale file translates the template under the key `rules.<code>.checks.<id>`; without a translation the English template is used. This way another implementation produces the same messages by reading only the schema.

**Locations.** The row is the physical line in the file, with the header on line 1. Problems in the header have row 1; problems that concern a whole file, or a TOML file, have no row. The column is the header cell as written (`depth_base[m]`), the canonical name when the column is missing, and in TOML the dotted key (`fractions.upper_mm`).

**Draft mode.** The validator tells _missing items_ apart from _contradictions_. A missing item is resolved by adding information: the manifest, a required key, a campaign, a required column or value, the campaign of a point when the package has several, the standard of a test with data, the `[fractions]` section, `upper_mm` for `custom`. Sub-checks of this kind have `"missing": true` in the schema. A contradiction means that something already written is wrong: a unit, a type, a duplicate key, a reference to something that does not exist, `wL < wP`, overlapping layers. In normal mode, missing items are errors. In draft mode they become a completeness report and do not make the package invalid, while contradictions remain errors. Each missing item names the file, the row and the field and, where the value comes from a closed list, the allowed values (`allowed`), for example the reference standard or `"unknown"` for a test. Software that builds packages can ask the user the question directly from it.

**Output formats.** In text, one line per problem: errors first, then warnings, then, in draft mode, missing items after a `missing:` line; the last line is a summary (`2 errors, 1 warnings, 3 missing`). In JSON, an object with `package`, `draft`, `ok` and the `issues` list; each issue has `level` (`error`, `warning`, `missing`), `code`, `check`, `path`, `row`, `column`, `params` (the values exactly as written in the file), `message` and, where relevant, `allowed`.

**Exit codes.** The command line (`gdp_validate.py [--draft] [--format text|json] [--lang ro] PACKAGE`) returns 0 without errors, 1 with errors and 2 when the package cannot be opened. Warnings and missing items do not change the code.

**Versions.** The validator checks only its own version. Any other version in the manifest gives E01 `version_unsupported`, and the other checks are not run, because the validator cannot judge rules it does not know. The importer can still load a package with the same major version and a newer minor version (`--accept-newer`): it checks it with the rules it knows, reports unknown files as warnings (W02) and imports it if it has no errors.

## 10. Complete example: a borehole and a CPTu

The example is fictitious, but has plausible values for Iași, in north-eastern Romania: loess over marly clay. The package has 10 files: manifest.toml and campaigns/C2026.toml from section 4, plus those below. There is a single campaign, so the optional `campaign` columns are absent.

`points.csv`. The method of the borehole is in quotes because it contains a comma.

```csv
point_id,type,easting[m],northing[m],elevation[m],final_depth[m],date_start,date_end,method,remarks
F1,borehole,697412.35,634988.10,52.40,8.00,2026-10-14,2026-10-14,"rotativ uscat, Ø 146 mm",
CPT1,cpt,697414.80,634986.55,52.38,10.20,2026-10-15,2026-10-15,,refuz la 10.20 m
```

`layers.csv`

```csv
point_id,depth_top[m],depth_base[m],description,soil_symbol,unit
F1,0.00,0.60,"Sol vegetal, cafeniu-negricios",,U0
F1,0.60,3.80,"Argilă prăfoasă loessoidă, gălbuie, plastic vârtoasă, cu concrețiuni calcaroase",siCl,U1
F1,3.80,8.00,"Argilă marnoasă vânătă, plastic consistentă spre vârtoasă",Cl,U2
```

`units.csv`

```csv
unit_id,name,description,remarks
U0,Sol vegetal,,
U1,Argile prăfoase și prafuri argiloase loessoide,"Gălbui, plastic vârtoase, sensibile la umezire",
U2,Argile marnoase,"Vânăt-cenușii, plastic consistente spre vârtoase",
```

`water.csv`

```csv
point_id,kind,depth[m],datetime,remarks
F1,struck,5.40,2026-10-14T13:10+03:00,
F1,stable,4.95,2026-10-15T09:00+03:00,citire după 20 h
```

`samples.csv`

```csv
sample_id,point_id,depth_top[m],depth_base[m],kind,remarks
F1-P1,F1,1.50,1.80,undisturbed,
F1-P2,F1,3.00,3.30,undisturbed,
F1-P3,F1,6.00,6.30,undisturbed,
```

`lab/index.csv`

```csv
sample_id,w[%],wL[%],wP[%],rho[Mg/m3],rho_s[Mg/m3],clay[%],silt[%],sand[%],gravel[%],remarks
F1-P1,19.8,38,21,1.86,2.69,28,58,14,0,
F1-P2,22.4,41,22,1.90,2.70,31,56,13,0,
F1-P3,27.1,58,26,1.94,2.73,48,44,8,0,
```

`cpt/tests.csv`

```csv
test_id,point_id,date,cone_area[cm2],area_ratio,filter_position,predrill_depth[m],equipment,remarks
CPT1,CPT1,2026-10-15,10,0.80,u2,0.40,Pagani TG 63-150,
```

`cpt/data/CPT1.csv`, first rows. The complete file has 490 rows, from 0.42 m to 10.20 m, at 2 cm intervals.

```csv
depth[m],qc[MPa],fs[kPa],u[kPa],inclination[deg]
0.42,1.84,62.1,2.3,0.4
0.44,1.91,64.8,2.1,0.4
0.46,1.97,66.0,2.2,0.4
0.48,2.05,67.9,2.0,0.5
```

The same project in AGS 4 would have the groups PROJ, TRAN, UNIT, TYPE, ABBR, LOCA, GEOL, WSTK, SAMP, LNMC, LLPL, LDEN, LPDN, GRAG, SCPG and SCPT. Every value would be in quotes, and every SCPT row would repeat `LOCA_ID` and `SCPG_TESN`.

## 11. Mapping to AGS 4

The core has an AGS 4 counterpart for each table. A bidirectional converter is therefore feasible from the start, with losses only where AGS has fields that the core does not provide: these go into `x_` columns. The mapping is preliminary, made without the dictionary, and must be checked field by field against the AGS 4.1 dictionary.

| GDP                     | AGS 4                        | Notes                                                                                                                                                                                                                      |
| ----------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest`, `campaigns` | PROJ, TRAN, UNIT, TYPE, ABBR | The AGS metadata and dictionaries reduce to a few keys. The closest equivalent of campaigns is `LOCA_CLST`, a grouping of locations by investigation phase, without standards or methods: `points.campaign` ↔ `LOCA_CLST`. |
| `points`                | LOCA                         | `easting`/`northing` → LOCA_NATE/LOCA_NATN, `elevation` → LOCA_GL, `final_depth` → LOCA_FDEP. `station` → LOCA_CNGE (text in AGS, of the form `500+123.23`, with no declared unit; the converter turns it into metres), `offset` → LOCA_OFFS (AGS fixes neither the unit nor the sign convention), `alignment` → LOCA_ALID. Checked in the standard AGS 4.0.4, 4.1 and 4.1.1 dictionaries. |
| `layers`                | GEOL                         | `depth_top`/`depth_base` → GEOL_TOP/GEOL_BASE, `description` → GEOL_DESC, `unit` → GEOL_GEOL (the closest equivalent).                                                                                                     |
| `units`                 | —                            | AGS 4 has no table of units. Units correspond to the elements of the ground model in AGSi.                                                                                                                                 |
| `water`                 | WSTK, WSTD, MOND             | `struck`/`stable` → WSTK/WSTD, `reading` → MOND.                                                                                                                                                                           |
| `samples`               | SAMP                         | The composite key of AGS reduces to `sample_id`. On import, `F1-P1` is generated.                                                                                                                                          |
| `lab_index`             | LNMC, LLPL, LDEN, LPDN, GRAG | Five AGS groups are gathered in one row per sample.                                                                                                                                                                        |
| `cpt_tests`             | SCPG                         | `area_ratio` → the cone area ratio in SCPG.                                                                                                                                                                                |
| `cpt/data/*`            | SCPT                         | SCPT_DPTH, SCPT_RES, SCPT_FRES, SCPT_PWP2. A single group becomes one file per test.                                                                                                                                       |

## 12. Machine-readable schema and database

The specification has a single source, `gdp-0.1.schema.json`. The validator, the documentation of the tables and the database schema are derived from it. The schema is language-neutral: names, descriptions and rules are in English. Labels, synonyms and error messages in a given language are in optional locale files, `locales/gdp-0.1.<lang>.json`. Their keys are paths in the schema, for example `tables.lab_index.fields.w`. An element with no locale entry keeps its canonical name. Synonyms (`W`, `Wn`, `umiditate`) serve mainly an AI that maps source documents onto the canonical fields. The file contains:

- the tables, with fields, types, units, primary and foreign keys;
- the JSON Schemas for `manifest.toml` and for the campaign files;
- the vocabularies, the registry of standards and the registry of grain-size limits;
- the derivation rules (reference depth, effective campaign, unit);
- the E/W rules.

The multi-project database is generated from the schema and differs from the package in four points:

| Aspect             | In the package                  | In the database                                                                                                           |
| ------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Keys               | Local identifier (`F1`)         | (`project_key`, `F1`); `project_key` is internal, `project.uuid` is the stable identifier                                 |
| Campaign           | Optional for points and samples | The effective campaign is written explicitly, `NOT NULL`                                                                  |
| Density            | `rho` or `gamma`                | Always `rho`, `rho_s`; `gamma` is converted with g = 9.81 m/s²                                                            |
| Procedural context | TOML files                      | The tables `campaigns` (with the grain-size limits resolved) and `campaign_procedures` (campaign, test, standard, method) |

The unit of samples and of CPT depths is obtained through the views `v_sample_context`, `v_lab` and `v_cpt`, with an interval join. Importing a package deletes in cascade the earlier data of the same `project.uuid` and replaces them.

Verification: two test packages, both with a point `F1`, were loaded into the same SQLite database, and one of them was imported again. There were no collisions and no foreign key violations. Units were derived for all samples and for all 490 CPT depths.

## 13. Design decisions

The decisions below record the reasons behind the format: those already taken, and those still open.

### Taken

| #   | Decision                                                                     | Consequence in the specification                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | CSV is the only form of the tables.                                          | The format is spreadsheet-friendly: the CSV export of a spreadsheet is valid in both dialects (3), but there is no xlsx form. The pitfalls of the export are described in section 8.                                        |
| 2   | Canonical names are in English.                                              | The schema is language-neutral. Labels, synonyms and messages in a given language are in optional locale files, `locales/gdp-0.1.<lang>.json`, separate from the schema and from packages.                                  |
| 3   | The format is called GDP, with the extension `.gdp`.                         | `.geo` is avoided, because Gmsh already uses it.                                                                                                                                                                            |
| 4   | Units are fixed, with no `units` option.                                     | The unit is in the header, and the validator does no conversions (E03). Conversions are done once, in importers.                                                                                                            |
| 5   | The choice between density and unit weight is made by the header.            | The pair `rho`/`rho_s` or `gamma`/`gamma_s` (E12), with g = 9.81 m/s² for the conversion.                                                                                                                                   |
| 6   | The manifest holds only the identity of the package.                         | The procedural context is in `campaigns/<id>.toml`, one file per campaign (section 4).                                                                                                                                      |
| 7   | Each campaign declares its complete procedural context, without inheritance. | The `[standards]`, `[methods]` and `[fractions]` sections of the campaign file. There are no package-level defaults.                                                                                                        |
| 8   | Within a campaign, a test is done with one standard and one method.          | Any other combination means another campaign (E11). There are no standard or method columns in the data tables.                                                                                                             |
| 9   | The campaign is named at the point and can be replaced at the sample.        | `points.campaign` and `samples.campaign`. With a single campaign, both may be absent.                                                                                                                                       |
| 10  | Grain-size limits follow from the declared standard.                         | `[fractions].source`; `upper_mm` only for `"custom"`.                                                                                                                                                                       |
| 11  | The scope is limited to soils.                                               | Rocks (rock mechanics) have no profile in v0.1.                                                                                                                                                                             |
| 12  | Samples tested in parallel or for verification are duplicated.               | Each duplicate is a new sample with a suffix (`F1-P2a`, `F1-P2bis`), possibly with its own campaign. The model keeps one row per sample.                                                                                    |
| 13  | Layers are grouped in geotechnical units.                                    | The optional table `units.csv` and the column `layers.unit`. Lenses and interbeds take the unit that hosts them. Fallback names, if `units` proves ambiguous with units of measurement: `geotechnical_units.csv` / `geotechnical_unit`. |
| 14  | The unit of samples and of CPT series is derived from depth, not written.    | Point + reference depth → layer → unit (5.5). There is no unit key in `samples`.                                                                                                                                            |
| 15  | Units have no declared order.                                                | The order follows from depths at each point and from elevations between points.                                                                                                                                             |
| 16  | Each project has a global identifier, `project.uuid`.                        | Required in the manifest (E01). In a database with several packages, keys become (project, local identifier).                                                                                                               |
| 17  | A package is a complete snapshot of the project.                             | Import replaces the earlier data of the same `project.uuid`; there are no partial packages or differences.                                                                                                                  |
| 18  | A point belongs to one project only.                                         | A borehole reused in a new project is duplicated. The relation "one point in several projects" is postponed until after v1.0.                                                                                               |
| 19  | The vocabulary of tests and methods is closed and confirmed.                 | The keys, method codes and reserved keys in 4.4. Methods stay in the vocabulary even if they are not used in a given country (for example `fluid_displacement` in Romania).                                                 |
| 20  | Provenance fields are postponed until after v1.0.                            | There is no `producer.method`, `reviewed_by` or `reviewed_at` in the manifest. A package produced with the help of an AI assistant mixes data entered by hand, extracted by AI and converted, so a package-level flag would be false. Until then, the producing software is written in `producer.software`. |
| 21  | Unit symbols follow UCUM, case-sensitive variant.                            | Units stay fixed per field; UCUM fixes only the spelling of the symbol (`unit_system` in the schema).                                                                                                                       |
| 22  | Linear works have a chainage and an offset from the alignment.               | `points.station[m]`, `points.offset[m]` (positive to the right), `points.alignment`. Coordinates remain required.                                                                                                           |
| 23  | Rows can name their source document.                                         | The column `source_file` (5.6), with an optional page `#page=N`; the file must exist in `attachments/` (E06).                                                                                                               |
| 24  | A test key has one standard and one method per campaign.                     | For strength tests the drainage condition is part of the key: the reserved keys `triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`, `direct_shear_cu`, `direct_shear_cd` (4.4). A profile can group several keys in one table, with a column that names the key. |
| 25  | The CSV dialect is detected from the header of each file.                    | Two dialects, `,` with `.` and `;` with `,`, with the decimal mark tied to the separator (3). Dates in ISO form only, encoding UTF-8 only. The dialect is not declared in the manifest, because it would repeat the header. |

### Open

1. **The registries of the vocabulary in 4.4.** The registry of known standards must be published, including the table standard → grain-size limits, and the standards for `swelling` and `collapse` must be set.
2. **Inclined points and inclination correction for CPT.** It is to be decided whether `depth` stays the penetration length or becomes the true depth. Candidate for a later version: the optional columns `points.plunge[deg]` and `points.bearing[deg]`, with depths measured along the hole; their absence means a vertical point.
3. **Code lists.** SR EN ISO 14688 symbols or the traditional STAS names (the former Romanian standards), and who maintains the lists.
4. **Interpretation.** Either an `interpretation` profile (characteristic values according to NP 122, the Romanian code for geotechnical parameters, keyed by `unit_id`), or left entirely to AGSi.
5. **Governance.** The specification is published as an open project (GitHub, CC BY 4.0). It remains to decide who maintains the format and how decisions are made: the author, a dedicated GitHub organisation or a professional body. Each option changes the perception of neutrality.
6. **After v1.0: points shared by several projects.** For example a column `points.origin` (`<project_uuid>/F3`), which would let a database recognise duplicates. To be introduced only if it proves useful.
7. **Separately versioned vocabulary.** For a later version: the vocabularies (tests, methods, codes, registries) in a file of their own, with its own version, so that codes and profiles can be added without a new version of the format. It needs a rule for packages that use codes newer than the validator.
8. **After v1.0: data provenance.** For example the production method (`manual`, `converted`, `ai_extracted`) and the review (`reviewed_by`, `reviewed_at`), so that a database can filter AI-extracted data that has not been reviewed. The level (package, table or row) is to be decided from real use.
9. **Methods that vary within one campaign.** For example permeability with constant head for sands and with falling head for clays, or standard and modified Proctor, in the same laboratory programme. The rule in 4.3 would split them into different campaigns. To be decided when the mechanical profiles are designed.
