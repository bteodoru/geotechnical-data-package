-- GDP v0.1: baza de date multi-proiect (SQLite).
-- Generat din gdp-0.1.schema.json de gdp_db.py. Nu se editează de mână.

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

CREATE TABLE points (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  point_id TEXT NOT NULL,
  type TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  easting REAL NOT NULL, -- [m]
  northing REAL NOT NULL, -- [m]
  elevation REAL, -- [m]
  final_depth REAL NOT NULL, -- [m]
  station REAL, -- [m]
  offset REAL, -- [m]
  alignment TEXT,
  date_start TEXT,
  date_end TEXT,
  method TEXT,
  source_file TEXT,
  remarks TEXT,
  PRIMARY KEY (project_key, point_id),
  FOREIGN KEY (project_key, campaign_id) REFERENCES campaigns(project_key, campaign_id) ON DELETE CASCADE
);

CREATE TABLE units (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  unit_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  remarks TEXT,
  PRIMARY KEY (project_key, unit_id)
);

CREATE TABLE layers (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  point_id TEXT NOT NULL,
  depth_top REAL NOT NULL, -- [m]
  depth_base REAL NOT NULL, -- [m]
  description TEXT NOT NULL,
  soil_symbol TEXT,
  unit_id TEXT,
  source_file TEXT,
  PRIMARY KEY (project_key, point_id, depth_top),
  FOREIGN KEY (project_key, point_id) REFERENCES points(project_key, point_id) ON DELETE CASCADE,
  FOREIGN KEY (project_key, unit_id) REFERENCES units(project_key, unit_id) ON DELETE CASCADE
);

CREATE TABLE water (
  row_id INTEGER PRIMARY KEY,
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  point_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  depth REAL NOT NULL, -- [m]
  datetime TEXT,
  source_file TEXT,
  remarks TEXT,
  FOREIGN KEY (project_key, point_id) REFERENCES points(project_key, point_id) ON DELETE CASCADE
);

CREATE TABLE samples (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  sample_id TEXT NOT NULL,
  point_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  depth_top REAL NOT NULL, -- [m]
  depth_base REAL, -- [m]
  kind TEXT NOT NULL,
  source_file TEXT,
  remarks TEXT,
  PRIMARY KEY (project_key, sample_id),
  FOREIGN KEY (project_key, point_id) REFERENCES points(project_key, point_id) ON DELETE CASCADE,
  FOREIGN KEY (project_key, campaign_id) REFERENCES campaigns(project_key, campaign_id) ON DELETE CASCADE
);

CREATE TABLE lab_index (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  sample_id TEXT NOT NULL,
  w REAL, -- [%]
  wL REAL, -- [%]
  wP REAL, -- [%]
  rho REAL, -- [Mg/m3]
  rho_s REAL, -- [Mg/m3]
  clay REAL, -- [%]
  silt REAL, -- [%]
  sand REAL, -- [%]
  gravel REAL, -- [%]
  source_file TEXT,
  remarks TEXT,
  PRIMARY KEY (project_key, sample_id),
  FOREIGN KEY (project_key, sample_id) REFERENCES samples(project_key, sample_id) ON DELETE CASCADE
);

CREATE TABLE cpt_tests (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  test_id TEXT NOT NULL,
  point_id TEXT NOT NULL,
  date TEXT NOT NULL,
  cone_area REAL NOT NULL, -- [cm2]
  area_ratio REAL,
  filter_position TEXT,
  predrill_depth REAL, -- [m]
  equipment TEXT,
  source_file TEXT,
  remarks TEXT,
  PRIMARY KEY (project_key, test_id),
  FOREIGN KEY (project_key, point_id) REFERENCES points(project_key, point_id) ON DELETE CASCADE
);

CREATE TABLE cpt_data (
  project_key INTEGER NOT NULL REFERENCES projects(project_key) ON DELETE CASCADE,
  test_id TEXT NOT NULL,
  depth REAL NOT NULL, -- [m]
  qc REAL NOT NULL, -- [MPa]
  fs REAL NOT NULL, -- [kPa]
  u REAL, -- [kPa]
  inclination REAL, -- [deg]
  PRIMARY KEY (project_key, test_id, depth),
  FOREIGN KEY (project_key, test_id) REFERENCES cpt_tests(project_key, test_id) ON DELETE CASCADE
);

CREATE INDEX ix_layers_interval ON layers(project_key, point_id, depth_top, depth_base);
CREATE INDEX ix_samples_point ON samples(project_key, point_id);

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
