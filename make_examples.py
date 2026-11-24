"""Construiește două pachete de test, ambele cu un punct F1, pentru a verifica încărcarea multi-proiect.

A: exemplul din specificație (o campanie, rho, CPTu).
B: alt proiect, două campanii (C2016 cu limite custom), gamma în loc de rho, fără CPT.
"""
import math
import zipfile
from pathlib import Path

OUT = Path(__file__).with_name("examples")


def cpt_series() -> str:
    rows = ["depth[m],qc[MPa],fs[kPa],u[kPa],inclination[deg]"]
    n = round((10.20 - 0.42) / 0.02) + 1
    for i in range(n):
        z = 0.42 + i * 0.02
        wiggle = 0.08 * math.sin(z * 7.0)
        if z < 0.60:
            qc, fs, u = 1.80 + wiggle, 60.0, 2.0
        elif z < 3.90:   # loess
            qc, fs, u = 2.10 + 0.10 * z + wiggle, 62.0 + 4.0 * z, 2.0 + 0.5 * z
        else:            # argilă marnoasă, sub nivelul apei
            qc, fs = 1.40 + 0.06 * z + wiggle, 70.0 + 3.0 * z
            u = max(0.0, (z - 4.95) * 9.81) + 25.0 * (z - 3.9)
        incl = 0.4 + 0.07 * z
        rows.append(f"{z:.2f},{qc:.2f},{fs:.1f},{u:.1f},{incl:.1f}")
    return "\n".join(rows) + "\n"


A = {
    "manifest.toml": '''format  = "gdp"
version = "0.1"

[project]
uuid           = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"
id             = "IS-2026-014"
name           = "Clădire socială, extindere anexă"
location       = "Iași, jud. Iași"
crs            = "EPSG:3844"
vertical_datum = "Marea Neagră 1975"

[producer]
organisation = "Firma A"
date         = 2026-11-24
software     = "make_examples.py"

[profiles]
cpt       = "0.1"
lab_index = "0.1"
''',
    "campaigns/C2026.toml": '''description  = "Studiu geotehnic pentru autorizare"
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
''',
    "points.csv": '''point_id,type,easting[m],northing[m],elevation[m],final_depth[m],date_start,date_end,method,remarks
F1,borehole,697412.35,634988.10,52.40,8.00,2026-10-14,2026-10-14,"rotativ uscat, Ø 146 mm",
CPT1,cpt,697414.80,634986.55,52.38,10.20,2026-10-15,2026-10-15,,refuz la 10.20 m
''',
    "units.csv": '''unit_id,name,description,remarks
U0,Sol vegetal,,
U1,Argile prăfoase și prafuri argiloase loessoide,"Gălbui, plastic vârtoase, sensibile la umezire",
U2,Argile marnoase,"Vânăt-cenușii, plastic consistente spre vârtoase",
''',
    "layers.csv": '''point_id,depth_top[m],depth_base[m],description,soil_symbol,unit
F1,0.00,0.60,"Sol vegetal, cafeniu-negricios",,U0
F1,0.60,3.80,"Argilă prăfoasă loessoidă, gălbuie, plastic vârtoasă, cu concrețiuni calcaroase",siCl,U1
F1,3.80,8.00,"Argilă marnoasă vânătă, plastic consistentă spre vârtoasă",Cl,U2
CPT1,0.00,0.60,Interpretat din CPTu: sol vegetal,,U0
CPT1,0.60,3.90,Interpretat din CPTu: argilă prăfoasă,,U1
CPT1,3.90,10.20,Interpretat din CPTu: argilă,,U2
''',
    "water.csv": '''point_id,kind,depth[m],datetime,remarks
F1,struck,5.40,2026-10-14T13:10+03:00,
F1,stable,4.95,2026-10-15T09:00+03:00,citire după 20 h
''',
    "samples.csv": '''sample_id,point_id,depth_top[m],depth_base[m],kind,remarks
F1-P1,F1,1.50,1.80,undisturbed,
F1-P2,F1,3.00,3.30,undisturbed,
F1-P3,F1,6.00,6.30,undisturbed,
''',
    "lab/index.csv": '''sample_id,w[%],wL[%],wP[%],rho[Mg/m3],rho_s[Mg/m3],clay[%],silt[%],sand[%],gravel[%],remarks
F1-P1,19.8,38,21,1.86,2.69,28,58,14,0,
F1-P2,22.4,41,22,1.90,2.70,31,56,13,0,
F1-P3,27.1,58,26,1.94,2.73,48,44,8,0,
''',
    "cpt/tests.csv": '''test_id,point_id,date,cone_area[cm2],area_ratio,filter_position,predrill_depth[m],equipment,remarks
CPT1,CPT1,2026-10-15,10,0.80,u2,0.40,Pagani TG 63-150,
''',
    "cpt/data/CPT1.csv": cpt_series(),
}

B = {
    "manifest.toml": '''format  = "gdp"
version = "0.1"

[project]
uuid = "9b1d6f40-2c8e-4a7b-b3e5-0f6a1c2d3e4f"
id   = "2026-07"
name = "Bloc de locuințe P+4"
crs  = "EPSG:3844"
vertical_datum = "Marea Neagră 1975"

[producer]
organisation = "Firma B"
date         = 2026-11-20

[profiles]
lab_index = "0.1"
''',
    "campaigns/C2016.toml": '''description  = "Studiu preliminar"
organisation = "Laborator X"
year         = 2016

[standards]
water_content = "unknown"
bulk_density  = "unknown"
atterberg     = "unknown"
grain_size    = "unknown"

[methods]
atterberg = "casagrande"

[fractions]
source   = "custom"
upper_mm = { clay = 0.005, silt = 0.05, sand = 2.0, gravel = 70.0 }
''',
    "campaigns/C2026.toml": '''description = "Studiu geotehnic"
year        = 2026

[standards]
water_content = "SR EN ISO 17892-1"
bulk_density  = "SR EN ISO 17892-2"
atterberg     = "SR EN ISO 17892-12"
grain_size    = "SR EN ISO 17892-4"

[methods]
atterberg  = "fall_cone"
grain_size = "sieving_pipette"

[fractions]
source = "SR EN ISO 14688-1"
''',
    "points.csv": '''point_id,type,campaign,easting[m],northing[m],elevation[m],final_depth[m]
F1,borehole,C2016,698120.00,636410.00,61.20,10.00
F2,borehole,C2026,698145.00,636402.00,60.70,12.00
''',
    "units.csv": '''unit_id,name
U1,Prafuri argiloase loessoide
U2,Argile marnoase
''',
    "layers.csv": '''point_id,depth_top[m],depth_base[m],description,unit
F1,0.00,5.20,Praf argilos loessoid,U1
F1,5.20,10.00,Argilă marnoasă,U2
F2,0.00,4.80,Praf argilos loessoid,U1
F2,4.80,12.00,Argilă marnoasă,U2
''',
    "samples.csv": '''sample_id,point_id,depth_top[m],depth_base[m],kind
F1-P1,F1,2.00,2.30,undisturbed
F2-P1,F2,2.50,2.80,undisturbed
F2-P2,F2,6.00,6.30,undisturbed
''',
    "lab/index.csv": '''sample_id,w[%],wL[%],wP[%],gamma[kN/m3],clay[%],silt[%],sand[%],gravel[%]
F1-P1,18.5,35,20,18.4,22,63,15,0
F2-P1,19.1,36,20,18.6,25,61,14,0
F2-P2,26.4,55,25,19.2,46,46,8,0
''',
}


def build(name: str, files: dict) -> Path:
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.gdp"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, content in files.items():
            z.writestr(fname, content)
    return path


if __name__ == "__main__":
    for p in (build("proiect_A", A), build("proiect_B", B)):
        print(p, p.stat().st_size, "B")
