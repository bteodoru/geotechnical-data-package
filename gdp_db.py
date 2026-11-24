"""GDP v0.1 -> SQLite: generează schema bazei de date multi-proiect din gdp-0.1.schema.json
și importă pachete .gdp (zip sau folder).

    python gdp_db.py ddl                    > gdp-0.1.db.sql
    python gdp_db.py load [--accept-newer] baza.sqlite a.gdp b.gdp ...

Fiecare pachet e validat (gdp_validator) înainte de import; un pachet cu erori e refuzat.

Baza de date conține mai multe proiecte. Cheia fiecărei entități e (project_key, id local).
Importul unui pachet înlocuiește complet datele anterioare cu același project.uuid.

Normalizări la import:
  - gamma, gamma_s -> rho, rho_s (g din schemă);
  - campania efectivă a punctelor și probelor e scrisă explicit (NOT NULL);
  - limitele fracțiunilor se rezolvă din registru sau din upper_mm (custom).
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import sys
import tomllib
from pathlib import Path

from gdp_validator import validate
from gdp_validator.package import Package

SCHEMA_PATH = Path(__file__).with_name("gdp-0.1.schema.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
G = SCHEMA["constants"]["g"]["value"]

SQL_TYPE = {"id": "TEXT", "text": "TEXT", "code": "TEXT", "date": "TEXT",
            "datetime": "TEXT", "file_ref": "TEXT", "number": "REAL", "integer": "INTEGER", "bool": "INTEGER"}

# Diferențe dintre pachet și baza de date (normalizare), aplicate peste schema pachetului.
DB_DROP = {"lab_index": {"gamma", "gamma_s"}}          # convertite în rho, rho_s
DB_NOT_NULL = {"points": {"campaign"}, "samples": {"campaign"}}  # campania efectivă
TABLE_ORDER = ["points", "units", "layers", "water", "samples", "lab_index", "cpt_tests", "cpt_data"]

FIXED_DDL = """\
PRAGMA foreign_keys = ON;

CREATE TABLE projects (
  project_key     INTEGER PRIMARY KEY,
  uuid            TEXT NOT NULL UNIQUE,
  id              TEXT NOT NULL,
  name            TEXT NOT NULL,
  location        TEXT,
  client          TEXT,
  crs             TEXT NOT NULL,
  vertical_datum  TEXT,
  producer_org    TEXT,
  producer_author TEXT,
  package_date    TEXT,
  software        TEXT,
  format_version  TEXT NOT NULL,
  imported_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE campaigns (
  project_key   INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  campaign_id   TEXT NOT NULL,
  description   TEXT,
  organisation  TEXT,
  year          INTEGER,
  fractions_source TEXT,
  clay_upper_mm    REAL,   -- limitele rezolvate (registru sau custom)
  silt_upper_mm    REAL,
  sand_upper_mm    REAL,
  gravel_upper_mm  REAL,
  PRIMARY KEY (project_key, campaign_id)
);

CREATE TABLE campaign_procedures (
  project_key  INTEGER NOT NULL,
  campaign_id  TEXT NOT NULL,
  test         TEXT NOT NULL,
  standard     TEXT NOT NULL,
  method       TEXT,
  PRIMARY KEY (project_key, campaign_id, test),
  FOREIGN KEY (project_key, campaign_id) REFERENCES campaigns(project_key, campaign_id) ON DELETE CASCADE
);
"""

VIEWS_DDL = """\
-- Probă + punct + campanie efectivă + unitate dedusă din adâncime (join pe interval).
CREATE VIEW v_sample_context AS
SELECT s.project_key, pr.id AS project_id, s.sample_id, s.point_id, s.campaign_id,
       s.depth_top, s.depth_base,
       CASE WHEN s.depth_base IS NULL THEN s.depth_top
            ELSE (s.depth_top + s.depth_base) / 2.0 END AS depth_ref,
       p.elevation - CASE WHEN s.depth_base IS NULL THEN s.depth_top
            ELSE (s.depth_top + s.depth_base) / 2.0 END AS elevation_ref,
       l.unit_id
FROM samples s
JOIN projects pr ON pr.project_key = s.project_key
JOIN points p    ON p.project_key = s.project_key AND p.point_id = s.point_id
LEFT JOIN layers l
       ON l.project_key = s.project_key AND l.point_id = s.point_id
      AND l.depth_top <= (CASE WHEN s.depth_base IS NULL THEN s.depth_top
                               ELSE (s.depth_top + s.depth_base) / 2.0 END)
      AND ((CASE WHEN s.depth_base IS NULL THEN s.depth_top
                 ELSE (s.depth_top + s.depth_base) / 2.0 END) < l.depth_base
           OR l.depth_base = p.final_depth);  -- ultimul strat include baza

-- Rezultate de laborator cu contextul complet: unitate, campanie, limite granulometrice.
CREATE VIEW v_lab AS
SELECT c.project_id, c.sample_id, c.point_id, c.depth_ref, c.unit_id, c.campaign_id,
       li.w, li.wL, li.wP, li.rho, li.rho_s, li.clay, li.silt, li.sand, li.gravel,
       cp.fractions_source, cp.clay_upper_mm,
       (SELECT method FROM campaign_procedures q
         WHERE q.project_key = c.project_key AND q.campaign_id = c.campaign_id
           AND q.test = 'atterberg') AS wL_method
FROM v_sample_context c
JOIN lab_index li ON li.project_key = c.project_key AND li.sample_id = c.sample_id
JOIN campaigns cp ON cp.project_key = c.project_key AND cp.campaign_id = c.campaign_id;

-- Fiecare adâncime CPT cu unitatea stratului punctului testului.
CREATE VIEW v_cpt AS
SELECT d.project_key, t.point_id, d.test_id, d.depth, d.qc, d.fs, d.u, l.unit_id
FROM cpt_data d
JOIN cpt_tests t ON t.project_key = d.project_key AND t.test_id = d.test_id
JOIN points p    ON p.project_key = d.project_key AND p.point_id = t.point_id
LEFT JOIN layers l ON l.project_key = d.project_key AND l.point_id = t.point_id
                  AND l.depth_top <= d.depth
                  AND (d.depth < l.depth_base OR l.depth_base = p.final_depth);  -- ultimul strat include baza
"""


def _fields(table: str) -> list[dict]:
    return [f for f in SCHEMA["tables"][table]["fields"] if f["name"] not in DB_DROP.get(table, set())]


def _col_name(table: str, field: str) -> str:
    # în baza de date, referințele poartă numele cheii țintă
    if field == "campaign":
        return "campaign_id"
    if table == "layers" and field == "unit":
        return "unit_id"
    return field


def table_ddl(table: str) -> str:
    spec = SCHEMA["tables"][table]
    cols = ["  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE"]
    if table == "cpt_data":
        cols.append("  test_id TEXT NOT NULL")
    for f in _fields(table):
        unit = f" -- [{f['unit']}]" if "unit" in f else ""
        nn = " NOT NULL" if f.get("required") or f["name"] in DB_NOT_NULL.get(table, set()) else ""
        cols.append(f"  {_col_name(table, f['name'])} {SQL_TYPE[f['type']]}{nn},{unit}")
    pk = spec.get("primary_key")
    if table == "cpt_data":
        pk = ["test_id"] + pk
    constraints = []
    if pk:
        constraints.append(f"  PRIMARY KEY (project_key, {', '.join(pk)})")
    else:
        cols.insert(0, "  row_id INTEGER PRIMARY KEY")
    for fk in spec.get("foreign_keys", []):
        src = ", ".join(_col_name(table, c) for c in fk["fields"])
        ref = fk["reference"]
        constraints.append(f"  FOREIGN KEY (project_key, {src}) REFERENCES {ref['table']}"
                           f"(project_key, {', '.join(ref['fields'])}) ON DELETE CASCADE")
    for f in _fields(table):
        if f.get("references") == "campaign":
            constraints.append("  FOREIGN KEY (project_key, campaign_id) REFERENCES campaigns"
                               "(project_key, campaign_id) ON DELETE CASCADE")
    if table == "cpt_data":
        constraints.append("  FOREIGN KEY (project_key, test_id) REFERENCES cpt_tests"
                           "(project_key, test_id) ON DELETE CASCADE")
    body = cols + constraints
    # virgulă după fiecare linie, cu excepția ultimei (comentariile de unitate rămân la final)
    lines = []
    for i, line in enumerate(body):
        last = i == len(body) - 1
        if " -- [" in line:
            code, comment = line.split(" -- ", 1)
            code = code.rstrip(",") + ("" if last else ",")
            lines.append(f"{code} -- {comment}")
        else:
            lines.append(line.rstrip(",") + ("" if last else ","))
    return f"CREATE TABLE {table} (\n" + "\n".join(lines) + "\n);\n"


def ddl() -> str:
    header = (f"-- GDP v{SCHEMA['version']}: baza de date multi-proiect (SQLite).\n"
              f"-- Generat din {SCHEMA_PATH.name} de gdp_db.py. Nu se editează de mână.\n\n")
    tables = "\n".join(table_ddl(t) for t in TABLE_ORDER)
    index = ("CREATE INDEX ix_layers_interval ON layers(project_key, point_id, depth_top, depth_base);\n"
             "CREATE INDEX ix_samples_point ON samples(project_key, point_id);\n")
    return header + FIXED_DDL + "\n" + tables + "\n" + index + "\n" + VIEWS_DDL


# ---------------------------------------------------------------- import

HEADER_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(\[(?P<unit>[^\]]+)\])?$")


def read_table(pkg: Package, path: str, table: str) -> list[dict]:
    text = pkg.read_text(path)
    if text is None:
        return []
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    spec = {f["name"]: f for f in SCHEMA["tables"][table]["fields"]}
    names = []
    for h in header:
        m = HEADER_RE.match(h.strip())
        names.append(m["name"] if m else h.strip())   # antetul a fost validat
    rows = []
    for raw in reader:
        if not any(v.strip() for v in raw):
            continue
        row = {}
        for name, value in zip(names, raw):
            value = value.strip()
            f = spec.get(name)
            if f is None:            # x_ sau necunoscută: ignorată în baza de date
                continue
            if value == "":
                row[name] = None
            elif f["type"] == "number":
                row[name] = float(value)
            elif f["type"] == "integer":
                row[name] = int(value)
            else:
                row[name] = value
        rows.append(row)
    return rows


def load(db: sqlite3.Connection, pkg_path: Path, accept_newer: bool = False) -> str:
    report = validate(pkg_path, accept_newer=accept_newer)
    if not report.ok:
        raise ValueError(f"{pkg_path}: pachet invalid\n{report.to_text()}")
    pkg = Package(pkg_path)
    manifest = tomllib.loads(pkg.read_text("manifest.toml"))
    proj, prod = manifest["project"], manifest.get("producer", {})
    uuid = proj["uuid"]

    cur = db.cursor()
    cur.execute("DELETE FROM projects WHERE uuid = ?", (uuid,))   # imagine completă: înlocuire
    cur.execute("""INSERT INTO projects (uuid, id, name, location, client, crs, vertical_datum,
                   producer_org, producer_author, package_date, software, format_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uuid, proj["id"], proj["name"], proj.get("location"), proj.get("client"), proj["crs"],
                 proj.get("vertical_datum"), prod.get("organisation"), prod.get("author"),
                 str(prod.get("date")) if prod.get("date") else None, prod.get("software"),
                 manifest["version"]))
    pk = cur.lastrowid

    # campanii
    registry = SCHEMA["vocabularies"]["fractions_registry"]
    campaign_files = sorted(n for n in pkg.names() if re.fullmatch(r"campaigns/[^/]+\.toml", n))
    campaign_ids = []
    for name in campaign_files:
        cid = Path(name).stem
        campaign_ids.append(cid)
        c = tomllib.loads(pkg.read_text(name))
        fr = c.get("fractions", {})
        src = fr.get("source")
        limits = fr.get("upper_mm") if src == "custom" else registry.get(src, {})
        cur.execute("""INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (pk, cid, c.get("description"), c.get("organisation"), c.get("year"), src,
                     limits.get("clay"), limits.get("silt"), limits.get("sand"), limits.get("gravel")))
        methods = c.get("methods", {})
        for test, standard in c.get("standards", {}).items():
            cur.execute("INSERT INTO campaign_procedures VALUES (?,?,?,?,?)",
                        (pk, cid, test, standard, methods.get(test)))
    single = campaign_ids[0] if len(campaign_ids) == 1 else None

    def insert(table: str, rows: list[dict], extra: dict | None = None):
        cols = [_col_name(table, f["name"]) for f in _fields(table)]
        names = [f["name"] for f in _fields(table)]
        if extra:
            cols = list(extra) + cols
        sql = f"INSERT INTO {table} (project_key, {', '.join(cols)}) VALUES ({', '.join('?' * (len(cols) + 1))})"
        for r in rows:
            vals = ([extra[k] for k in extra] if extra else []) + [r.get(n) for n in names]
            cur.execute(sql, [pk] + vals)

    points = read_table(pkg, "points.csv", "points")
    point_campaign = {}
    for p in points:
        p["campaign"] = p.get("campaign") or single
        point_campaign[p["point_id"]] = p["campaign"]

    insert("points", points)
    insert("units", read_table(pkg, "units.csv", "units"))
    insert("layers", read_table(pkg, "layers.csv", "layers"))
    insert("water", read_table(pkg, "water.csv", "water"))

    samples = read_table(pkg, "samples.csv", "samples")
    for s in samples:
        s["campaign"] = s.get("campaign") or point_campaign[s["point_id"]]
    insert("samples", samples)

    lab = read_table(pkg, "lab/index.csv", "lab_index")
    for r in lab:
        has_gamma = r.get("gamma") is not None or r.get("gamma_s") is not None
        if has_gamma:
            r["rho"] = r["gamma"] / G if r.get("gamma") is not None else None
            r["rho_s"] = r["gamma_s"] / G if r.get("gamma_s") is not None else None
    insert("lab_index", lab)

    tests = read_table(pkg, "cpt/tests.csv", "cpt_tests")
    insert("cpt_tests", tests)
    for t in tests:
        data = read_table(pkg, f"cpt/data/{t['test_id']}.csv", "cpt_data")
        insert("cpt_data", data, extra={"test_id": t["test_id"]})

    db.commit()
    return f"{proj['id']} ({uuid}): {len(points)} puncte, {len(samples)} probe, {len(tests)} teste CPT"


def main(argv: list[str]) -> None:
    if argv[:1] == ["ddl"]:
        sys.stdout.write(ddl())
    elif argv[:1] == ["load"]:
        args = argv[1:]
        accept_newer = "--accept-newer" in args
        args = [a for a in args if a != "--accept-newer"]
        if len(args) < 2:
            print(__doc__)
            return
        db_path = Path(args[0])
        new = not db_path.exists()
        db = sqlite3.connect(db_path)
        db.execute("PRAGMA foreign_keys = ON")
        if new:
            db.executescript(ddl())
        for p in args[1:]:
            print("încărcat:", load(db, Path(p), accept_newer=accept_newer))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
