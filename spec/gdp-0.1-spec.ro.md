> Aceasta e traducerea în română a specificației [`gdp-0.1-spec.md`](gdp-0.1-spec.md) și poate rămâne în urma ei. Textul englez prevalează; schema [`gdp-0.1.schema.json`](../gdp-0.1.schema.json) e normativă pentru amândouă.

# Format de date geotehnice — nucleu v0.1 (draft)

Versiunea 0.1 (draft), 2026-11-28 · Bogdan Teodoru

## 1. Scop și principii

GDP (Geotechnical Data Package) este un format pentru datele factuale ale unui program de investigare geotehnică. Poate fi citit și scris manual, cu instrumente uzuale (un editor de text sau un program de calcul tabelar), iar programele, inclusiv asistenții AI, îl pot valida automat și pot ajuta la generarea lui. Pentru datele geotehnice există deja două formate consacrate. AGS 4 e larg folosit, dar sintaxa lui și dependența de un dicționar de date îl fac greu de scris sau de verificat manual. DIGGS e cuprinzător, dar reprezentarea lui XML/GML e prolixă și greu de scris, citit sau verificat manual. GDP își propune să fie mai simplu decât amândouă: un pachet e un folder cu tabele CSV simple, distribuit ca fișier zip și descris de un manifest TOML mic și de câte un fișier pentru fiecare campanie de investigare.

Nucleul v0.1 acoperă datele factuale ale unei investigații: puncte de investigare, stratificație, apă subterană, probe, indici de laborator și CPT/CPTu. Interpretarea (valori caracteristice, model de teren) rămâne în afara nucleului; nucleul conține doar o grupare simplă a straturilor în unități geotehnice (`units.csv`, 5.5). Formatul se limitează la pământuri; rocile țin de mecanica rocilor și nu intră deocamdată în domeniu. Extensia pachetului e `.gdp`.

- **CSV, prietenos cu programele de calcul tabelar.** Tabelele sunt CSV-uri simple, în unul dintre cele două dialecte pe care le scriu programele de calcul tabelar după setările regionale: `,` cu punct zecimal sau `;` cu virgulă zecimală. Un tabel pregătit cu coloanele din specificație, cu datele calendaristice în forma ISO și salvat ca „CSV UTF-8”, e valid fără setări regionale și fără convertor (secțiunea 8). Formatul nu are o formă xlsx.
- **Un tabel = un fișier.** Fără rânduri GROUP/UNIT/TYPE și fără ghilimele inutile.
- **Nume citibile, cu unitatea în antet:** `depth_top[m]`, nu `GEOL_TOP`. Simbolurile unităților se scriu după UCUM, varianta sensibilă la majuscule (`Mg/m3`, `kN/m3`, `cm2`, `deg`).
- **Chei simple.** Fiecare entitate are un singur identificator, unic în proiect. Excepție fac straturile, identificate prin punct și adâncimea superioară (`point_id`, `depth_top`).
- **Se stochează doar mărimi măsurate.** Mărimile derivate (IP, IC, qt, Rf, Bq, Ic) se recalculează, deci nu pot fi inconsecvente.
- **Nucleu mic + profile versionate separat** (`cpt`, `lab_index`). Pachetul declară ce profile folosește.
- **Extensibil fără negociere.** Coloanele proprii poartă prefixul `x_` și sunt ignorate de cititorii care nu le cunosc.

## 2. Structura pachetului

Un pachet `.gdp` e un zip cu căi fixe. Sunt obligatorii `manifest.toml`, `points.csv` și cel puțin un fișier în `campaigns/`. Restul fișierelor apar numai dacă există date pentru ele. Dacă zip-ul nu are `manifest.toml` în rădăcină, dar conține un singur folder care îl are, cum produc „Compress” din Finder și „Send to → Compressed folder” din Windows, acel folder e rădăcina pachetului; metadatele arhivatorului (`__MACOSX/`, `.DS_Store`, `._*`) se ignoră, iar căile din mesaje sunt relative la rădăcina pachetului. Regula e doar pentru zip-uri, unde nivelul suplimentar vine de la arhivator: un folder dat validatorului sau importatorului trebuie să fie chiar rădăcina pachetului. Când `manifest.toml` lipsește din rădăcină dar există în altă parte a pachetului, validatorul indică unde (E01) și nu mai face celelalte verificări.

```
proiect.gdp
├── manifest.toml          identitate: format, proiect, producător, profile
├── campaigns/
│   ├── C2016.toml         context procedural: standarde, metode, fracții
│   └── C2026.toml
├── points.csv             puncte de investigare (foraje, CPT, gropi…)
├── units.csv              unități geotehnice (orizonturi)
├── layers.csv             stratificație descrisă
├── water.csv              observații apă subterană
├── samples.csv            probe
├── lab/
│   └── index.csv          profil lab_index: umiditate, limite, densități, fracții
├── cpt/
│   ├── tests.csv          profil cpt: un rând per test
│   └── data/
│       ├── CPT1.csv       seria densă a testului CPT1
│       └── CPT2.csv
└── attachments/           opțional: PDF, fotografii, fișe originale, indicate prin source_file
```

Relațiile dintre fișiere trec prin aceste chei:

```
points.point_id ─┬─ layers, water, samples, cpt/tests
                 │
units.unit_id    ── layers.unit
samples.sample_id ── lab/index
cpt/tests.test_id ── cpt/data/<test_id>.csv        (cheia e numele fișierului)
points.campaign  ─┬─ campaigns/<campaign>.toml     (cheia e numele fișierului)
samples.campaign ─┘
```

Unitatea unei probe sau a unei adâncimi dintr-o serie CPT nu se scrie nicăieri. Se deduce: punct + adâncime → strat → unitate (secțiunea 5.5).

Un cititor ignoră fișierele pe care nu le cunoaște. Astfel, un pachet v0.2 cu un profil nou rămâne lizibil pentru un cititor v0.1. Validatorul raportează fișierele necunoscute ca avertismente (W02), ca un fișier cu nume greșit să fie observat; fișierele din `attachments/` și metadatele arhivatorului nu se raportează.

## 3. Convenții generale

Regulile de mai jos se aplică tuturor tabelelor.

| Aspect              | Regula                                                                                                                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Codare text         | UTF-8. BOM-ul e acceptat, pentru că Excel îl scrie la „CSV UTF-8”.                                                                                                                                                               |
| Separator, zecimală | Două dialecte: `,` între câmpuri cu `.` zecimal, sau `;` între câmpuri cu `,` zecimal. Dialectul se deduce din primul rând al fiecărui fișier: e cel al cărui separator apare singur în antet (numele coloanelor nu conțin `,` sau `;`), altfel primul. Zecimala e legată de separator, deci `1.234` într-un fișier cu `;` e eroare. Fără separator de mii. Ghilimele doar când valoarea conține separatorul, ghilimele sau rând nou (RFC 4180). Fișierele unui pachet pot avea dialecte diferite; programele care scriu GDP folosesc primul dialect. |
| Antet               | Primul rând. Numele coloanei e exact cel din specificație, cu unitatea între paranteze drepte: `depth_top[m]`. Mărimile adimensionale nu au paranteze.                                                                           |
| Unități             | SI, fixate de specificație pentru fiecare coloană. Unitatea din antet trebuie să coincidă cu cea specificată (v0.1 nu face conversii).                                                                                           |
| Valoare lipsă       | Celulă goală. Nu se folosesc `-999`, `N/A`, `-`.                                                                                                                                                                                 |
| Tipuri              | `id`, `text`, `number`, `integer`, `date` (`YYYY-MM-DD`, doar forma ISO), `datetime` (ISO 8601 cu fus orar, `2026-10-14T09:30+03:00`), `bool` (`true`/`false`), `code` (dintr-o listă de coduri), `file_ref` (cale relativă față de `attachments/`, urmată opțional de `#page=N`, pagina unui PDF numărată de la 1; 5.6).                                                |
| Identificatori      | Caractere `A–Z a–z 0–9 _ - .`, fără spații, maximum 64 de caractere, sensibili la majuscule. Sunt folosiți și ca nume de fișiere. Se recomandă identificatori care încep cu o literă (`F1`, `P1`, `F1-P2bis`), ca programele de calcul tabelar să nu-i transforme în date calendaristice sau numere și să nu piardă zerourile de la început. |
| Adâncimi            | Metri sub nivelul terenului din punctul respectiv, pozitive în jos. Un interval e `[depth_top, depth_base)`, cu `depth_top < depth_base`. Ultimul interval al unui punct include și baza, când aceasta e egală cu `final_depth`. |
| Cote                | Metri față de datumul vertical din manifest (de exemplu Marea Neagră 1975).                                                                                                                                                      |
| Coordonate          | Un singur CRS per proiect, declarat în manifest ca cod EPSG (de exemplu `EPSG:3844`, Stereo 70). Coloanele se numesc `easting` și `northing`, ca să nu existe ambiguitatea X/Y din Stereo 70.                                    |
| Verticalitate       | v0.1 presupune puncte verticale. Forajele înclinate sunt o decizie deschisă.                                                                                                                                                     |
| Coloane proprii     | Prefix `x_` (de exemplu `x_lab_ref`). Nu sunt validate și se păstrează la conversie.                                                                                                                                             |

## 4. Manifestul și campaniile

Contextul pachetului stă în două locuri. `manifest.toml` spune ce e pachetul, iar fiecare fișier `campaigns/<id>.toml` spune cum au fost obținute datele unei campanii. Unitățile și alegerea între ρ și γ nu se declară în niciunul dintre ele: stau în antetul coloanelor.

### 4.1 `manifest.toml`

Manifestul are circa 20 de linii și nu crește odată cu datele. Cheia `project.uuid` identifică proiectul la nivel global. Se generează o singură dată, la crearea proiectului, și nu se schimbă la versiunile ulterioare ale pachetului. Fără instrumentele GDP se obține cu `uuidgen` (macOS, Linux) sau cu `New-Guid` în PowerShell (Windows). `project.id` rămâne codul intern, lizibil, al proiectului.

Un pachet e întotdeauna o **imagine completă** a proiectului, nu o diferență față de o versiune anterioară. O bază de date care importă pachetul înlocuiește tot ce avea pentru acel `project.uuid`. Versiunea se recunoaște după `producer.date`. În baza de date, cheia fiecărei entități devine perechea (proiect, identificator local), de exemplu (`project.uuid`, `point_id`).

```toml
format  = "gdp"          # obligatoriu
version = "0.1"          # versiunea nucleului; obligatoriu

[project]
uuid           = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"  # obligatoriu; generat o singură dată
id             = "IS-2026-014"                         # obligatoriu
name           = "Clădire socială, extindere anexă"    # obligatoriu
location       = "Iași, jud. Iași"
client         = ""
crs            = "EPSG:3844"                           # obligatoriu
vertical_datum = "Marea Neagră 1975"                   # obligatoriu dacă există cote

[producer]
organisation = ""
author       = ""
date         = 2026-11-24       # data generării pachetului
software     = "exemplu 1.4"    # opțional, util la depanare

[profiles]
cpt       = "0.1"
lab_index = "0.1"
```

### 4.2 `campaigns/<id>.toml`

O campanie e o etapă de investigare: altă perioadă, alt scop sau alt executant. Fiecare fișier declară complet contextul procedural al campaniei, fără valori implicite și fără moștenire din alte fișiere. Numele fișierului e identificatorul campaniei.

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
# campaigns/C2016.toml — date vechi, informație parțială
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
upper_mm = { clay = 0.005, silt = 0.05, sand = 2.0, gravel = 70.0 }   # valori ilustrative
```

| Secțiune      | Conținut                                                                                                                                                                                                                                                   |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| chei de bază  | `description`, `organisation`, `year`, toate opționale.                                                                                                                                                                                                    |
| `[standards]` | Standardul fiecărei încercări care are date în campanie, ca text. Pentru date vechi fără această informație se scrie explicit `"unknown"`. O încercare cu date dar fără standard e eroare (E11).                                                           |
| `[methods]`   | Metoda de determinare, acolo unde standardul admite mai multe. Opțională; lipsă = nespecificată.                                                                                                                                                           |
| `[fractions]` | Standardul care definește limitele fracțiunilor granulometrice. Pentru un standard cunoscut, `source` e suficient, iar limitele se iau din tabelul de referință al implementării. Cu `source = "custom"`, limitele superioare se dau în `upper_mm`, în mm. |

### 4.3 Legarea datelor de campanii

- Un punct indică o campanie prin `points.campaign`. Straturile, apa, probele și testele CPT ale punctului aparțin aceleiași campanii.
- O probă poate avea propria campanie, în `samples.campaign`. Dacă e completată, aceasta înlocuiește campania punctului pentru proba respectivă și pentru încercările ei de laborator. E cazul dublurilor de verificare: `F1-P2bis` din campania de verificare V2026, de exemplu.
- Când pachetul are o singură campanie, coloanele `campaign` pot rămâne goale. Când are mai multe, fiecare punct trebuie să indice una (E06).

Regula care rezultă: **într-o campanie, o încercare se face cu un singur standard și o singură metodă.** Orice altă combinație înseamnă altă campanie.

### 4.4 Vocabular: chei de încercare și coduri de metodă

Vocabularul e închis. Un fișier de campanie folosește doar cheile și codurile de mai jos, plus extensii cu prefixul `x_`. Un cod de metodă există numai acolo unde standardul descrie metode distincte.

**O cheie de încercare e unitatea pentru care campania declară un standard și o metodă.** Ce poate varia de la o încercare la alta în aceeași campanie nu se declară în campanie. Dacă definește tipul încercării, face parte din cheie; dacă e o condiție a încercării (de exemplu presiunea de consolidare), e o coloană în datele profilului. La încercările de rezistență, condiția de drenaj face parte din cheie (`triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`…): UU și CU au standarde diferite (SR EN ISO 17892-8 și 17892-9) și apar frecvent în aceeași campanie. Cheile separate nu înseamnă tabele separate: un profil poate ține mai multe chei într-un singur tabel, cu o coloană care indică cheia fiecărui rând.

| Cheie              | Mărimi                           | Standard de referință | Coduri `method`                                                                                  |
| ------------------ | -------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------ |
| `water_content`    | `w`                              | SR EN ISO 17892-1     | — (o singură metodă)                                                                             |
| `bulk_density`     | `rho` / `gamma`                  | SR EN ISO 17892-2     | `linear_measurement`, `immersion`, `fluid_displacement`                                          |
| `particle_density` | `rho_s` / `gamma_s`              | SR EN ISO 17892-3     | `fluid_pycnometer`, `gas_pycnometer`                                                             |
| `grain_size`       | `clay`, `silt`, `sand`, `gravel` | SR EN ISO 17892-4     | `sieving`, `sieving_hydrometer`, `sieving_pipette`, `hydrometer`, `pipette`, `laser_diffraction` |
| `atterberg`        | `wL`, `wP`                       | SR EN ISO 17892-12    | `fall_cone`, `casagrande` (metoda se referă la wL)                                               |
| `cpt`              | profilul `cpt`                   | SR EN ISO 22476-1     | —                                                                                                |

Metodele corespund celor descrise în fiecare standard: trei pentru densitate ([ISO 17892-2](https://www.iso.org/standard/55244.html)), doi picnometri ([ISO 17892-3](https://www.iso.org/standard/55245.html)), cernere și două metode de sedimentare ([ISO 17892-4](https://www.iso.org/standard/55246.html)), con și cupa Casagrande ([ISO 17892-12](https://www.iso.org/standard/72017.html)). Alte trei reguli:

- **`fall_cone` nu distinge între conul de 80 g/30° și cel de 60 g/60°.** Versiunea din 2004 a standardului le-a adoptat pe amândouă pentru că dau practic aceeași valoare a lui wL ([ISO/TS 17892-12:2004](https://www.iso.org/standard/38525.html)), deci diferența nu justifică un cod separat.
- **Codurile de granulometrie descriu combinația completă** (`sieving_hydrometer`), nu o listă, ca valoarea să rămână text simplu. `laser_diffraction` nu face parte din SR EN ISO 17892-4 și se declară cu standardul său propriu.
- **O metodă nedeclarată e nespecificată.** Nu există cod `unknown` pentru metode.

**Chei rezervate** pentru profile viitoare, fără coduri de metodă deocamdată: `oedometer`, `unconfined_compression`, `triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`, `direct_shear_cu`, `direct_shear_cd`, `permeability`, `compaction`, `organic_content`, `carbonate_content`, `swelling`, `collapse`. Ultimele două acoperă pământurile cu umflări și contracții mari și pământurile sensibile la umezire, specifice practicii românești. Standardele lor rămân de stabilit.

**Standardele sunt text.** Se scriu ca pe copertă, fără an (`SR EN ISO 17892-12`); anul se poate adăuga după două puncte (`SR EN ISO 17892-12:2018`). Implementarea de referință ține un registru de standarde cunoscute. Un standard nerecunoscut produce un avertisment (W05), nu o eroare, ca standardele noi sau vechi să nu blocheze pachetul.

TOML a fost ales în locul YAML pentru că nu are capcane de indentare și nu transformă tacit `no` în boolean.

## 5. Tabelele nucleului

Nucleul are cinci tabele, cu 40 de coloane în total, dintre care 18 sunt obligatorii. Toate, cu excepția `units`, se leagă de `points` prin `point_id`; `units` e referit de `layers.unit`.

### 5.1 `points.csv`: puncte de investigare

Un rând per punct: foraj, sondaj CPT, penetrare dinamică, groapă sau puț.

| Coloană          | Tip      | Oblig.     | Descriere                                                                                                                                                                                             |
| ---------------- | -------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `point_id`       | id       | da         | Identificator unic în proiect (`F1`, `CPT1`).                                                                                                                                                         |
| `type`           | code     | da         | `borehole`, `cpt`, `dp`, `trial_pit`, `well`.                                                                                                                                                         |
| `campaign`       | id       | nu         | Campania din care face parte punctul, cu fișierul `campaigns/<id>.toml`. Poate rămâne goală doar când pachetul are o singură campanie.                                                                |
| `easting[m]`     | number   | da         | Coordonată est în CRS-ul din manifest.                                                                                                                                                                |
| `northing[m]`    | number   | da         | Coordonată nord în CRS-ul din manifest.                                                                                                                                                               |
| `elevation[m]`   | number   | recomandat | Cota terenului în punct.                                                                                                                                                                              |
| `final_depth[m]` | number   | da         | Adâncimea finală atinsă.                                                                                                                                                                              |
| `station[m]`     | number   | nu         | Poziția kilometrică pe axa unei lucrări liniare (dig, drum, canal), în metri: km 12+345,60 se scrie `12345.60`. Obligatorie dacă există `offset`.                                                     |
| `offset[m]`      | number   | nu         | Distanța față de ax, pozitivă la dreapta privind în sensul în care crește poziția kilometrică, negativă la stânga.                                                                                    |
| `alignment`      | text     | nu         | Numele axei la care se raportează `station`, când proiectul are mai multe (`dig`, `canal`). Axa nu e descrisă în pachet, deci poziția kilometrică e informativă, iar coordonatele rămân de referință. |
| `date_start`     | date     | nu         | Data începerii.                                                                                                                                                                                       |
| `date_end`       | date     | nu         | Data terminării.                                                                                                                                                                                      |
| `method`         | text     | nu         | Metodă și echipament, liber („rotativ uscat, Ø 146 mm”).                                                                                                                                              |
| `source_file`    | file_ref | nu         | Documentul sursă din `attachments/` (5.6).                                                                                                                                                            |
| `remarks`        | text     | nu         | Observații.                                                                                                                                                                                           |

### 5.2 `layers.csv`: stratificație

Un rând per strat descris într-un punct. Straturile unui punct nu se suprapun. Lentilele și intercalațiile se descriu ca straturi separate, dar primesc unitatea care le găzduiește.

| Coloană         | Tip      | Oblig. | Descriere                                                     |
| --------------- | -------- | ------ | ------------------------------------------------------------- |
| `point_id`      | id       | da     | Referință la `points`.                                        |
| `depth_top[m]`  | number   | da     | Partea superioară a stratului.                                |
| `depth_base[m]` | number   | da     | Baza stratului.                                               |
| `description`   | text     | da     | Descrierea completă, așa cum apare în fișa de foraj.          |
| `soil_symbol`   | code     | nu     | Simbol SR EN ISO 14688-2 (`clSi`, `saGr`, `Mg`).              |
| `unit`          | id       | nu     | Unitatea geotehnică din care face parte stratul, din `units`. |
| `source_file`   | file_ref | nu     | Documentul sursă din `attachments/` (5.6).                    |

### 5.3 `water.csv`: apă subterană

Un rând per observație. Așa, aceeași structură acoperă și nivelul întâlnit la foraj, și citirile repetate dintr-un piezometru.

| Coloană       | Tip      | Oblig. | Descriere                                                                       |
| ------------- | -------- | ------ | ------------------------------------------------------------------------------- |
| `point_id`    | id       | da     | Referință la `points`.                                                          |
| `kind`        | code     | da     | `struck` (întâlnit), `stable` (stabilizat), `reading` (citire de monitorizare). |
| `depth[m]`    | number   | da     | Adâncimea nivelului apei.                                                       |
| `datetime`    | datetime | nu     | Momentul observației.                                                           |
| `source_file` | file_ref | nu     | Documentul sursă din `attachments/` (5.6).                                      |
| `remarks`     | text     | nu     | Observații („aparție lentă, 20 min”).                                           |

### 5.4 `samples.csv`: probe

Un rând per probă. `sample_id` e unic în tot proiectul, nu doar în foraj. Aceasta e diferența principală față de cheia compusă din AGS (LOCA_ID + SAMP_TOP + SAMP_REF + SAMP_TYPE + SAMP_ID). O probă testată în paralel sau pentru verificare se înregistrează ca probă separată, cu sufix (F1-P2a, F1-P2bis).

| Coloană         | Tip      | Oblig. | Descriere                                                                                                             |
| --------------- | -------- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| `sample_id`     | id       | da     | Identificator unic în proiect (`F1-P1`).                                                                              |
| `point_id`      | id       | da     | Referință la `points`.                                                                                                |
| `campaign`      | id       | nu     | Înlocuiește campania punctului pentru această probă (de exemplu o dublură de verificare). Goală = campania punctului. |
| `depth_top[m]`  | number   | da     | Adâncimea de prelevare, sau partea superioară a intervalului.                                                         |
| `depth_base[m]` | number   | nu     | Baza intervalului. Goală = probă punctuală.                                                                           |
| `kind`          | code     | da     | `undisturbed`, `disturbed`, `core`, `water`.                                                                          |
| `source_file`   | file_ref | nu     | Documentul sursă din `attachments/` (5.6).                                                                            |
| `remarks`       | text     | nu     | Observații.                                                                                                           |

### 5.5 `units.csv`: unități geotehnice

O unitate grupează straturi cu proprietăți similare, care sunt tratate împreună în descrierea de ansamblu, în modelul terenului (NP 074) și la stabilirea valorilor caracteristice. Termenul neutru `unit` evită disputa unitate / orizont / strat și corespunde unităților geotehnice din modelul de teren al noului Eurocod 7. Tabelul e opțional: un pachet fără `units.csv` conține doar stratificația descrisă.

| Coloană       | Tip  | Oblig. | Descriere                                                              |
| ------------- | ---- | ------ | ---------------------------------------------------------------------- |
| `unit_id`     | id   | da     | Identificator unic în proiect (`U1`, `U2`).                            |
| `name`        | text | da     | Denumirea unității („Argile prăfoase și prafuri argiloase loessoide”). |
| `description` | text | nu     | Descrierea de ansamblu.                                                |
| `remarks`     | text | nu     | Observații.                                                            |

Unitatea nu are o coloană de ordine. Ordinea într-un punct de investigare rezultă din adâncimile straturilor, iar ordinea între puncte rezultă din cote (`elevation` minus adâncime). O unitate poate lipsi dintr-un punct de investigare sau poate fi prima într-un alt punct și a treia într-altul.

Unitatea se deduce, nu se scrie la probe sau în seriile CPT:

1. Adâncimea de referință a unei probe e mijlocul intervalului `[depth_top, depth_base]`, sau `depth_top` pentru o probă punctuală.
2. Proba aparține stratului punctului în care cade această adâncime. Intervalele straturilor sunt `[sus, jos)`, deci o limită între straturi aparține stratului de dedesubt. Excepție: baza ultimului strat, egală cu final_depth, aparține ultimului strat.
3. Proba primește unitatea stratului.

Pentru seriile CPT, fiecare adâncime cade într-un strat al punctului CPT. Stratificația unui punct CPT este cea interpretată din sondaj și se trece în `layers` ca pentru orice alt punct. Excluderea unei probe din calculul valorilor caracteristice e o decizie de proiectare și aparține profilului de interpretare, nu tabelului de probe.

### 5.6 Documente sursă: `source_file`

Tabelele `points`, `layers`, `water`, `samples`, `lab_index` și `cpt_tests` au coloana opțională `source_file`, care indică documentul din care provine rândul: fișa de foraj, buletinul de laborator, fișierul GEF original. Valoarea e calea relativă față de `attachments/` (`buletin_lab_2026.pdf`, `fise/F1.pdf`). Pentru un PDF se poate indica și pagina, după `#page=` (`buletin_lab_2026.pdf#page=3`, cu prima pagină 1). Fișierul trebuie să existe în pachet (E06). Astfel, fiecare valoare se poate verifica pe documentul din care a fost preluată, inclusiv când a fost extrasă automat.

## 6. Profilul `cpt` (v0.1)

Profilul separă metadatele testului de seria densă. Metadatele stau într-un tabel mic; fiecare serie are un fișier propriu, fără cheie repetată pe rânduri. Un CPTu de 30 m înregistrat la 2 cm are \~1 500 de rânduri, adică \~50 KB în CSV și mai puțin de 20 KB în zip.

### 6.1 `cpt/tests.csv`

| Coloană             | Tip      | Oblig.         | Descriere                                                                             |
| ------------------- | -------- | -------------- | ------------------------------------------------------------------------------------- |
| `test_id`           | id       | da             | Identificatorul testului. Dă și numele fișierului de date.                            |
| `point_id`          | id       | da             | Referință la `points` (de regulă de tip `cpt`). Testul moștenește campania punctului. |
| `date`              | date     | da             | Data execuției.                                                                       |
| `cone_area[cm2]`    | number   | da             | Aria vârfului: 10 sau 15.                                                             |
| `area_ratio`        | number   | da pentru CPTu | Raportul de arii _a_, necesar pentru qt = qc + u2(1 − a).                             |
| `filter_position`   | code     | da pentru CPTu | `u1`, `u2`, `u3`.                                                                     |
| `predrill_depth[m]` | number   | nu             | Adâncimea pre-forată, fără date.                                                      |
| `equipment`         | text     | nu             | Penetrometru și con („Geomil 200 kN, con S15CFIIP”).                                  |
| `source_file`       | file_ref | nu             | Documentul sursă din `attachments/`, de exemplu fișierul GEF original (5.6).          |
| `remarks`           | text     | nu             | Observații (refuz, abatere de la verticală).                                          |

### 6.2 `cpt/data/<test_id>.csv`

Un rând per adâncime. Fișierul are numai date; toate metadatele sunt în `tests.csv`.

| Coloană            | Tip    | Oblig. | Descriere                                                |
| ------------------ | ------ | ------ | -------------------------------------------------------- |
| `depth[m]`         | number | da     | Lungimea de penetrare, strict crescătoare.               |
| `qc[MPa]`          | number | da     | Rezistența pe vârf măsurată (necorectată).               |
| `fs[kPa]`          | number | da     | Frecarea pe manșon.                                      |
| `u[kPa]`           | number | nu     | Presiunea apei în pori la poziția din `filter_position`. |
| `inclination[deg]` | number | nu     | Înclinarea față de verticală.                            |

Nu se stochează qt, Rf, Bq, Qt, Fr sau Ic. Se obțin din coloanele de mai sus și din `area_ratio`.

Seriile intră în pachet prin importatoare de la formatele aparatelor, nu prin tastare. Primul importator propus e GEF (formatul text olandez pentru CPT).

Testele de disipare și SCPT seismic nu intră în v0.1.

## 7. Profilul `lab_index` (v0.1)

Un rând per probă, cu o coloană pentru fiecare mărime măsurată. E forma în care laboratoarele lucrează deja în Excel. Profilul acoperă indicii folosiți în aproape orice studiu; încercările mecanice (edometru, forfecare, triaxial) vor fi profile separate.

| Coloană                             | Tip      | Descriere                                                           |
| ----------------------------------- | -------- | ------------------------------------------------------------------- |
| `sample_id`                         | id       | Referință la `samples`. Obligatorie.                                |
| `w[%]`                              | number   | Umiditate naturală.                                                 |
| `wL[%]`                             | number   | Limita de curgere.                                                  |
| `wP[%]`                             | number   | Limita de frământare.                                               |
| `rho[Mg/m3]` sau `gamma[kN/m3]`     | number   | Densitatea, respectiv greutatea volumică, în stare naturală.        |
| `rho_s[Mg/m3]` sau `gamma_s[kN/m3]` | number   | Densitatea, respectiv greutatea volumică, a particulelor solide.    |
| `clay[%]`                           | number   | Fracțiunea sub limita `clay` din `[fractions]` al campaniei probei. |
| `silt[%]`                           | number   | Între limitele `clay` și `silt`.                                    |
| `sand[%]`                           | number   | Între limitele `silt` și `sand`.                                    |
| `gravel[%]`                         | number   | Între limitele `sand` și `gravel`.                                  |
| `source_file`                       | file_ref | Buletinul de laborator din `attachments/` (5.6).                    |
| `remarks`                           | text     | Observații.                                                         |

Antetul decide între densitate și greutate volumică. Un fișier `lab_index` conține fie perechea `rho`/`rho_s`, fie perechea `gamma`/`gamma_s`, niciodată amândouă (E12). Pentru conversia între ele, specificația fixează g = 9,81 m/s², astfel încât toate implementările să dea același rezultat. Standardul și metoda nu apar în tabel: ele țin de campania probei (secțiunea 4.2).

Au fost lăsate deliberat în afară IP, IC, e, n, Sr și ρd (sau γd), pentru că se calculează din coloanele de mai sus. Curba granulometrică completă va fi un profil separat, cu o serie per probă, construit după același model ca seriile CPT.

## 8. Programe de calcul tabelar (informativ)

Secțiunea nu adaugă reguli. Descrie capcanele întâlnite când un tabel se pregătește într-un program de calcul tabelar (Excel, LibreOffice, Numbers) și se exportă ca CSV.

- **Tabelul.** Antetul din specificație pe primul rând și datele de la rândul 2, fără celule îmbinate, fără rânduri de total și fără unitatea pe un rând separat. Fiecare tabel se exportă separat, cu numele de fișier din specificație.
- **Separatorul și zecimala nu cer setări.** Exportul folosește setările regionale ale sistemului, deci `,` cu `.` sau `;` cu `,`. Ambele dialecte sunt valide (3).
- **Datele calendaristice** se exportă în formatul afișat, de exemplu `14.10.2026`, care nu e valid. Coloanele de dată se formatează `yyyy-mm-dd` înainte de export.
- **Codarea.** Se alege „CSV UTF-8”. Varianta „CSV” simplă scrie în codarea locală a sistemului (MacRoman, Windows-1250, Windows-1252), iar diacriticele se pierd.
- **Valorile se exportă așa cum sunt afișate.** O coloană formatată cu o zecimală pierde restul, iar un număr afișat `1,23E+05` iese 123000. Zerourile de la final dispar (`52.40` devine `52.4`), ceea ce e valid.
- **Un CSV existent nu se corectează în Excel.** La deschidere, Excel interpretează datele calendaristice și le scrie la salvare în formatul local. Un fișier fără BOM poate fi citit într-o codare greșită, iar textul se corupe fără ca validatorul să poată observa (`Ø` devine `√ò`). Un CSV existent se corectează într-un editor de text. Pentru vizualizare în Excel se folosește importul (Data → From Text/CSV), cu codarea UTF-8.
- **Identificatorii** care încep cu o cifră (`1-2`, `3.10`, `007`) pot deveni date calendaristice sau numere, iar zerourile de la început se pierd. Se recomandă identificatori care încep cu o literă (3).
- **Separatorii nu se înlocuiesc prin căutare și înlocuire.** Virgulele din text, de exemplu `rotativ uscat, Ø 146 mm`, s-ar schimba fără urmă. Nu e nevoie, pentru că ambele dialecte sunt valide.

## 9. Reguli de validare

Validarea are 19 reguli: 12 erori, care fac pachetul invalid, și 7 avertismente. Toate se pot verifica mecanic. Nu există reguli care să ceară citirea unui document separat.

| Cod | Nivel       | Regula                                                                                                                                                                                                                                                                                                                                        |
| --- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E01 | eroare      | `manifest.toml` există și are `format`, `version`, `project.uuid` (UUID valid), `project.id`, `project.name`, `project.crs`. Manifestul și fișierele de campanie sunt TOML valid și respectă schema lor; cheile de încercare și metodele țin de E10, fracțiunile de E11.                                                                      |
| E02 | eroare      | `points` are cel puțin un rând, iar `campaigns/` are cel puțin un fișier.                                                                                                                                                                                                                                                                     |
| E03 | eroare      | Fiecare tabel prezent e CSV în UTF-8, într-unul dintre cele două dialecte (3), și are toate coloanele obligatorii, cu nume și unitate exacte.                                                                                                                                                                                                 |
| E04 | eroare      | Valorile se pot citi în tipul coloanei (numerele cu zecimala dialectului fișierului, datele în forma ISO), câmpurile obligatorii nu sunt goale, iar valorile respectă limitele coloanei (`out_of_bounds`): `final_depth`, precum și `depth_top` din straturi și probe, ≥ 0; `area_ratio` în [0, 1].                                           |
| E05 | eroare      | Cheile primare sunt unice: `point_id` în `points`, `unit_id` în `units`, (`point_id`, `depth_top`) în `layers`, `sample_id` în `samples` și în `lab_index`, `test_id` în `cpt/tests`. În fișierele de date CPT, `depth` e unică pentru că e strict crescătoare (E09).                                                                         |
| E06 | eroare      | Toate referințele se rezolvă: fiecare `point_id` din `layers` există în `points`, fiecare `layers.unit` există în `units`, fiecare `campaign` din `points` și `samples` are fișierul `campaigns/<campaign>.toml` ș.a.m.d. Cu mai multe campanii, fiecare punct indică una. Fiecare `source_file` indică un fișier existent în `attachments/`. |
| E07 | eroare      | `depth_top < depth_base`, iar toate adâncimile sunt în \[0, `final_depth`\] ale punctului.                                                                                                                                                                                                                                                    |
| E08 | eroare      | Straturile aceluiași punct nu se suprapun.                                                                                                                                                                                                                                                                                                    |
| E09 | eroare      | Fiecare `test_id` are fișierul de date, și fiecare fișier de date are un `test_id`. În fiecare fișier, `depth` e strict crescătoare.                                                                                                                                                                                                          |
| E10 | eroare      | Valorile din coloanele `code` apar în lista de coduri, iar `wL ≥ wP`. Cheile din `[standards]` și `[methods]` și codurile de metodă provin din vocabularul din 4.4 sau au prefixul `x_`.                                                                                                                                                      |
| E11 | eroare      | Pentru fiecare încercare cu date, campania rândului declară standardul în `[standards]` (un standard sau `"unknown"`). Dacă există fracțiuni granulometrice, `[fractions].source` e un standard cunoscut sau `"custom"` cu `upper_mm` complet.                                                                                                |
| E12 | eroare      | `lab_index` conține fie `rho`/`rho_s`, fie `gamma`/`gamma_s`, nu amândouă perechile.                                                                                                                                                                                                                                                          |
| W01 | avertisment | Există goluri între straturile unui punct, sau stratificația nu începe la 0 ori nu ajunge la `final_depth`.                                                                                                                                                                                                                                   |
| W02 | avertisment | O coloană necunoscută fără prefixul `x_`: nu se citește și probabil e o greșeală de tastare. Un fișier necunoscut în afara `attachments/`.                                                                                                                                                                                                    |
| W03 | avertisment | Valori în afara intervalelor plauzibile: `w > 150 %`, `qc > 100 MPa`, `rho` în afara \[1,2; 2,6\] Mg/m³ (echivalent în kN/m³ pentru `gamma`).                                                                                                                                                                                                 |
| W04 | avertisment | Suma fracțiunilor granulometrice diferă de 100 % cu mai mult de ±1 %.                                                                                                                                                                                                                                                                         |
| W05 | avertisment | Un standard din `[standards]` nu apare în registrul implementării. Poate fi un standard nou, unul vechi sau o greșeală de scriere.                                                                                                                                                                                                            |
| W06 | avertisment | Adâncimea de referință a unei probe nu cade în niciun strat al punctului, deci unitatea ei nu se poate deduce.                                                                                                                                                                                                                                |
| W07 | avertisment | Pachetul are `units.csv`, dar un strat nu are `unit`.                                                                                                                                                                                                                                                                                         |

Validatorul de referință raportează fiecare problemă cu fișierul, rândul și coloana. Exemplu: `layers.csv:14:depth_base[m] E07 depth_base (3.20) ≤ depth_top (3.40)`.

**Sub-verificări și mesaje.** Fiecare regulă are în schemă (`rules[*].checks`) una sau mai multe sub-verificări, fiecare cu un identificator stabil și un șablon de mesaj în engleză, cu parametri între acolade: E07 are `top_not_above_base` și `beyond_final_depth`, de exemplu. Fișierul de localizare traduce șablonul sub cheia `rules.<cod>.checks.<id>`; fără traducere se folosește șablonul englezesc. Astfel, o altă implementare produce aceleași mesaje citind doar schema.

**Locații.** Rândul e linia fizică din fișier, cu antetul pe linia 1. Problemele din antet au rândul 1, cele care privesc un fișier întreg sau un fișier TOML nu au rând. Coloana e celula de antet așa cum e scrisă (`depth_base[m]`), numele canonic când coloana lipsește, iar în TOML cheia cu puncte (`fractions.upper_mm`).

**Modul draft.** Validatorul deosebește _lipsurile_ de _contradicții_. O lipsă se rezolvă adăugând informație: manifest, cheie obligatorie, campanie, coloană sau valoare obligatorie, campania unui punct când pachetul are mai multe, standardul unei încercări cu date, secțiunea `[fractions]`, `upper_mm` pentru `custom`. Sub-verificările de acest fel au în schemă `"missing": true`. O contradicție înseamnă că ceva deja scris e greșit: unitate, tip, cheie duplicată, referință spre ceva inexistent, `wL < wP`, straturi suprapuse. În modul normal, lipsurile sunt erori. În modul draft ele devin un raport de completitudine și nu fac pachetul invalid, iar contradicțiile rămân erori. Fiecare lipsă indică fișierul, rândul și câmpul, iar acolo unde valoarea vine dintr-o listă închisă, și valorile permise (`allowed`), de exemplu standardul de referință sau `"unknown"` pentru o încercare. Un program care construiește pachete poate pune întrebarea direct pe baza ei.

**Formate de ieșire.** În text, câte o linie per problemă, întâi erorile, apoi avertismentele, apoi, în modul draft, lipsurile după o linie `missing:`; ultima linie e un rezumat (`2 errors, 1 warnings, 3 missing`). În JSON, un obiect cu `package`, `draft`, `ok` și lista `issues`; fiecare problemă are `level` (`error`, `warning`, `missing`), `code`, `check`, `path`, `row`, `column`, `params` (valorile exact cum sunt scrise în fișier), `message` și, unde e cazul, `allowed`.

**Coduri de ieșire.** Linia de comandă (`gdp_validate.py [--draft] [--format text|json] [--lang ro] PACHET`) întoarce 0 fără erori, 1 cu erori și 2 când pachetul nu se poate deschide. Avertismentele și lipsurile nu schimbă codul.

**Versiuni.** Validatorul verifică doar versiunea lui. Orice altă versiune din manifest dă E01 `version_unsupported`, iar celelalte verificări nu se mai fac, pentru că validatorul nu poate judeca reguli pe care nu le cunoaște. Importatorul poate încărca totuși un pachet cu aceeași versiune majoră și o versiune minoră mai nouă (`--accept-newer`): îl verifică după regulile pe care le cunoaște, raportează fișierele necunoscute ca avertismente (W02) și îl importă dacă nu are erori.

## 10. Exemplu complet: un foraj și un CPTu

Exemplul e fictiv, dar are valori plauzibile pentru Iași: loess peste argilă marnoasă. Pachetul are 10 fișiere: manifest.toml și campaigns/C2026.toml din secțiunea 4, plus cele de mai jos. Există o singură campanie, deci coloanele opționale campaign lipsesc.

`points.csv`. Metoda forajului e între ghilimele pentru că conține o virgulă.

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

`cpt/data/CPT1.csv`, primele rânduri. Fișierul complet are 490 de rânduri, de la 0.42 m la 10.20 m, cu pas de 2 cm.

```csv
depth[m],qc[MPa],fs[kPa],u[kPa],inclination[deg]
0.42,1.84,62.1,2.3,0.4
0.44,1.91,64.8,2.1,0.4
0.46,1.97,66.0,2.2,0.4
0.48,2.05,67.9,2.0,0.5
```

Același proiect în AGS 4 ar avea grupurile PROJ, TRAN, UNIT, TYPE, ABBR, LOCA, GEOL, WSTK, SAMP, LNMC, LLPL, LDEN, LPDN, GRAG, SCPG și SCPT. Fiecare valoare ar fi între ghilimele, iar fiecare rând SCPT ar repeta `LOCA_ID` și `SCPG_TESN`.

## 11. Mapare către AGS 4

Nucleul are un corespondent AGS 4 pentru fiecare tabel. Deci un convertor bidirecțional e fezabil de la început, cu pierderi doar acolo unde AGS are câmpuri pe care nucleul nu le prevede: acestea ajung în coloane `x_`. Maparea e preliminară, făcută fără dicționar, și trebuie verificată câmp cu câmp față de dicționarul AGS 4.1.

| GDP                     | AGS 4                        | Note                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest`, `campaigns` | PROJ, TRAN, UNIT, TYPE, ABBR | Metadatele și dicționarele AGS se reduc la câteva chei. Cel mai apropiat echivalent al campaniilor e `LOCA_CLST`, o grupare a punctelor pe faze de investigare, fără standarde și metode: `points.campaign` ↔ `LOCA_CLST`.                                                                                                                                                       |
| `points`                | LOCA                         | `easting`/`northing` → LOCA_NATE/LOCA_NATN, `elevation` → LOCA_GL, `final_depth` → LOCA_FDEP. `station` → LOCA_CNGE (text în AGS, de forma `500+123.23`, fără unitate declarată; convertorul îl transformă în metri), `offset` → LOCA_OFFS (AGS nu fixează unitatea și convenția de semn), `alignment` → LOCA_ALID. Verificate în dicționarele standard AGS 4.0.4, 4.1 și 4.1.1. |
| `layers`                | GEOL                         | `depth_top`/`depth_base` → GEOL_TOP/GEOL_BASE, `description` → GEOL_DESC, `unit` → GEOL_GEOL (cel mai apropiat echivalent).                                                                                                                                                                                                                                                      |
| `units`                 | —                            | AGS 4 nu are tabel de unități. Unitățile corespund elementelor modelului de teren din AGSi.                                                                                                                                                                                                                                                                                      |
| `water`                 | WSTK, WSTD, MOND             | `struck`/`stable` → WSTK/WSTD, `reading` → MOND.                                                                                                                                                                                                                                                                                                                                 |
| `samples`               | SAMP                         | Cheia compusă AGS se reduce la `sample_id`. La import se generează `F1-P1`.                                                                                                                                                                                                                                                                                                      |
| `lab_index`             | LNMC, LLPL, LDEN, LPDN, GRAG | Cinci grupuri AGS se adună într-un rând per probă.                                                                                                                                                                                                                                                                                                                               |
| `cpt_tests`             | SCPG                         | `area_ratio` → raportul de arii al conului din SCPG.                                                                                                                                                                                                                                                                                                                             |
| `cpt/data/*`            | SCPT                         | SCPT_DPTH, SCPT_RES, SCPT_FRES, SCPT_PWP2. Un grup unic devine câte un fișier per test.                                                                                                                                                                                                                                                                                          |

## 12. Schema citibilă de mașină și baza de date

Specificația are o sursă unică, `gdp-0.1.schema.json`. Din ea se obțin validatorul, documentația tabelelor și schema bazei de date. Schema e neutră lingvistic: numele, descrierile și regulile sunt în engleză. Etichetele, sinonimele și mesajele de eroare într-o anumită limbă stau în fișiere de localizare opționale, `locales/gdp-0.1.<lang>.json`. Cheile lor sunt căi în schemă, de exemplu `tables.lab_index.fields.w`. Un element fără intrare de localizare își păstrează numele canonic. Sinonimele (`W`, `Wn`, `umiditate`) servesc mai ales unui AI care mapează documente sursă pe câmpurile canonice. Fișierul conține:

- tabelele, cu câmpuri, tipuri, unități, chei primare și străine;
- schemele JSON pentru `manifest.toml` și fișierele de campanie;
- vocabularele, registrul de standarde și registrul limitelor granulometrice;
- regulile de deducere (adâncime de referință, campanie efectivă, unitate);
- regulile E/W.

Baza de date multi-proiect se generează din schemă și se deosebește de pachet în patru puncte:

| Aspect             | În pachet                    | În baza de date                                                                                                              |
| ------------------ | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Chei               | Identificator local (`F1`)   | (`project_key`, `F1`); `project_key` e intern, `project.uuid` e identificatorul stabil                                       |
| Campanie           | Opțională la puncte și probe | Campania efectivă e scrisă explicit, `NOT NULL`                                                                              |
| Densitate          | `rho` sau `gamma`            | Mereu `rho`, `rho_s`; `gamma` se convertește cu g = 9,81 m/s²                                                                |
| Context procedural | Fișiere TOML                 | Tabelele `campaigns` (cu limitele granulometrice rezolvate) și `campaign_procedures` (campanie, încercare, standard, metodă) |

Unitatea probelor și a adâncimilor CPT se obține prin vederile `v_sample_context`, `v_lab` și `v_cpt`, cu un join pe interval. Importul unui pachet șterge în cascadă datele anterioare ale aceluiași `project.uuid` și le înlocuiește.

Verificare: două pachete de test, ambele cu un punct `F1`, au fost încărcate în aceeași bază SQLite, iar unul dintre ele a fost reimportat. Nu au apărut coliziuni sau încălcări de chei străine. Unitățile au fost deduse pentru toate probele și toate cele 490 de adâncimi CPT.

## 13. Decizii de proiectare

Deciziile de mai jos arată motivele formatului: cele deja luate și cele încă deschise.

### Luate

| #   | Decizie                                                                         | Consecință în specificație                                                                                                                                                                                                                                                                               |
| --- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | CSV e singura formă a tabelelor.                                                | Formatul e prietenos cu programele de calcul tabelar: exportul lor CSV e valid în ambele dialecte (3), dar nu există o formă xlsx. Capcanele exportului sunt descrise în secțiunea 8.                                                                                                                    |
| 2   | Numele canonice sunt în engleză.                                                | Schema e neutră lingvistic. Etichetele, sinonimele și mesajele într-o anumită limbă stau în fișiere de localizare opționale, `locales/gdp-0.1.<lang>.json`, separate de schemă și de pachete.                                                                                                            |
| 3   | Formatul se numește GDP, cu extensia `.gdp`.                                    | `.geo` e evitată, pentru că e deja folosită de Gmsh.                                                                                                                                                                                                                                                     |
| 4   | Unitățile sunt fixe, fără opțiune `units`.                                      | Unitatea stă în antet, iar validatorul nu face conversii (E03). Conversiile se fac o singură dată, în importatoare.                                                                                                                                                                                      |
| 5   | Alegerea între densitate și greutate volumică se face prin antet.               | Perechea `rho`/`rho_s` sau `gamma`/`gamma_s` (E12), cu g = 9,81 m/s² pentru conversie.                                                                                                                                                                                                                   |
| 6   | Manifestul conține doar identitatea pachetului.                                 | Contextul procedural stă în `campaigns/<id>.toml`, câte un fișier per campanie (secțiunea 4).                                                                                                                                                                                                            |
| 7   | Fiecare campanie își declară complet contextul procedural, fără moștenire.      | Secțiunile `[standards]`, `[methods]` și `[fractions]` din fișierul campaniei. Nu există valori implicite la nivel de pachet.                                                                                                                                                                            |
| 8   | Într-o campanie, o încercare se face cu un singur standard și o singură metodă. | Orice altă combinație înseamnă altă campanie (E11). Nu există coloane de standard sau metodă în tabelele de date.                                                                                                                                                                                        |
| 9   | Campania se indică la punct și poate fi înlocuită la probă.                     | `points.campaign` și `samples.campaign`. Cu o singură campanie, ambele pot lipsi.                                                                                                                                                                                                                        |
| 10  | Limitele granulometrice decurg din standardul declarat.                         | `[fractions].source`; `upper_mm` doar pentru `"custom"`.                                                                                                                                                                                                                                                 |
| 11  | Domeniul e limitat la pământuri.                                                | Rocile (mecanica rocilor) nu au profil în v0.1.                                                                                                                                                                                                                                                          |
| 12  | Probele testate în paralel sau pentru verificare se dublează.                   | Fiecare dublură e o probă nouă cu sufix (`F1-P2a`, `F1-P2bis`), eventual cu propria campanie. Modelul păstrează un rând per probă.                                                                                                                                                                       |
| 13  | Straturile se grupează în unități geotehnice.                                   | Tabelul opțional `units.csv` și coloana `layers.unit`. Lentilele și intercalațiile primesc unitatea care le găzduiește. Numele de rezervă, dacă `units` se dovedește ambiguu față de unitățile de măsură: `geotechnical_units.csv` / `geotechnical_unit`.                                                |
| 14  | Unitatea probelor și a seriilor CPT se deduce din adâncime, nu se scrie.        | Punct + adâncime de referință → strat → unitate (5.5). Nu există cheie de unitate în `samples`.                                                                                                                                                                                                          |
| 15  | Unitățile nu au ordine declarată.                                               | Ordinea rezultă din adâncimi în fiecare punct și din cote între puncte.                                                                                                                                                                                                                                  |
| 16  | Fiecare proiect are un identificator global, `project.uuid`.                    | Obligatoriu în manifest (E01). Într-o bază de date cu mai multe pachete, cheile devin (proiect, identificator local).                                                                                                                                                                                    |
| 17  | Un pachet e o imagine completă a proiectului.                                   | Importul înlocuiește datele anterioare ale aceluiași `project.uuid`; nu există pachete parțiale sau diferențe.                                                                                                                                                                                           |
| 18  | Un punct aparține unui singur proiect.                                          | Un foraj preluat într-un proiect nou se dublează. Relația „un punct în mai multe proiecte” e amânată după v1.0.                                                                                                                                                                                          |
| 19  | Vocabularul de încercări și metode e închis și confirmat.                       | Cheile, codurile de metodă și cheile rezervate din 4.4. Metodele rămân în vocabular chiar dacă nu se folosesc într-o anumită țară (de exemplu `fluid_displacement` în România).                                                                                                                          |
| 20  | Câmpurile de proveniență se amână după v1.0.                                    | Nu există `producer.method`, `reviewed_by` sau `reviewed_at` în manifest. Un pachet produs cu ajutorul unui asistent AI amestecă date introduse manual, extrase de AI și convertite, deci un indicator la nivel de pachet ar fi fals. Până atunci, programul producător se trece în `producer.software`. |
| 21  | Simbolurile unităților urmează UCUM, varianta sensibilă la majuscule.           | Unitățile rămân fixe per câmp; UCUM fixează doar scrierea simbolului (`unit_system` în schemă).                                                                                                                                                                                                          |
| 22  | Lucrările liniare au poziție kilometrică și distanță față de ax.                | `points.station[m]`, `points.offset[m]` (pozitiv la dreapta), `points.alignment`. Coordonatele rămân obligatorii.                                                                                                                                                                                        |
| 23  | Rândurile pot indica documentul sursă.                                          | Coloana `source_file` (5.6), cu pagină opțională `#page=N`; fișierul trebuie să existe în `attachments/` (E06).                                                                                                                                                                                          |
| 24  | O cheie de încercare are un singur standard și o singură metodă pe campanie.    | Condiția de drenaj face parte din cheie la încercările de rezistență: cheile rezervate `triaxial_uu`, `triaxial_cu`, `triaxial_cd`, `direct_shear_uu`, `direct_shear_cu`, `direct_shear_cd` (4.4). Un profil poate grupa mai multe chei într-un tabel, cu o coloană care indică cheia.                   |
| 25  | Dialectul CSV se deduce din antetul fiecărui fișier.                            | Două dialecte, `,` cu `.` și `;` cu `,`, cu zecimala legată de separator (3). Datele calendaristice doar ISO, codarea doar UTF-8. Dialectul nu se declară în manifest, pentru că ar repeta antetul.                                                                                                      |
| 26  | Un zip fără `manifest.toml` în rădăcină, al cărui singur folder de nivel superior îl conține, are acel folder drept rădăcină a pachetului. | „Compress” din Finder și „Send to → Compressed folder” din Windows adaugă acest nivel. Metadatele arhivatorului (`__MACOSX/`, `.DS_Store`, `._*`) se ignoră, iar căile din mesaje sunt relative la rădăcină. Regula e doar pentru zip-uri: un folder dat instrumentelor trebuie să fie chiar rădăcina pachetului (2). |
| 27  | Coloanele necunoscute se raportează (W02) și nu se citesc.                      | Nu există o listă de mărimi derivate de ignorat: utilizatorii își refac tabelele cu coloanele GDP, iar o mărime derivată se poate scrie `IP`, `I_p` sau `ind_pl`, deci o astfel de listă n-ar fi niciodată completă (9).                                                                                 |
| 28  | Un `manifest.toml` pus greșit e o singură eroare fatală.                        | Când `manifest.toml` nu e în rădăcina pachetului, dar există în altă parte a lui, singura problemă e E01 `manifest_elsewhere`, care arată unde se află, și nu se mai face nicio altă verificare: pachetul nu poate fi interpretat, iar celelalte erori ar fi doar consecințe. Rămâne eroare și în modul draft (2, 9). |
| 29  | Identificatorii au cel mult 64 de caractere.                                    | `types.id` în schemă. Limita anterioară, de 24 de caractere, venea de la numele foilor xlsx, care nu mai contează, pentru că formatul nu are o formă xlsx (3).                                                                                                                                           |

### Deschise

1. **Registrele vocabularului din 4.4.** Trebuie publicat registrul de standarde cunoscute, inclusiv tabelul standard → limite granulometrice, și stabilite standardele pentru `swelling` și `collapse`.
2. **Puncte înclinate și corecția de înclinare la CPT.** E de stabilit dacă `depth` rămâne lungime de penetrare sau devine adâncime adevărată. Varianta candidată pentru o versiune ulterioară: coloanele opționale `points.plunge[deg]` și `points.bearing[deg]`, cu adâncimile măsurate de-a lungul găurii; lipsa lor înseamnă punct vertical.
3. **Liste de coduri.** Simbolurile SR EN ISO 14688 sau denumirile tradiționale STAS, și cine întreține listele.
4. **Interpretarea.** Ori un profil `interpretation` (valori caracteristice NP 122 raportate la `unit_id`), ori lăsată integral în seama AGSi.
5. **Guvernanța.** Specificația este publicată ca proiect deschis (GitHub, CC BY 4.0). Rămâne de stabilit cine întreține formatul și cum se iau deciziile: autorul, o organizație GitHub dedicată sau un organism profesional. Fiecare variantă schimbă percepția de neutralitate.
6. **După v1.0: puncte comune mai multor proiecte.** De exemplu o coloană `points.origin` (`<project_uuid>/F3`), care ar permite unei baze de date să recunoască dublurile. Se introduce doar dacă se dovedește utilă.
7. **Vocabular versionat separat.** Pentru o versiune ulterioară: vocabularele (încercări, metode, coduri, registre) într-un fișier propriu, cu versiune proprie, ca să se poată adăuga coduri și profile fără o versiune nouă a formatului. Necesită o regulă pentru pachetele care folosesc coduri mai noi decât validatorul.
8. **După v1.0: proveniența datelor.** De exemplu metoda de producere (`manual`, `converted`, `ai_extracted`) și verificarea (`reviewed_by`, `reviewed_at`), ca o bază de date să poată filtra datele extrase de AI neverificate. Nivelul (pachet, tabel sau rând) se stabilește din utilizarea reală.
9. **Metode care variază în aceeași campanie.** De exemplu permeabilitatea cu nivel constant la nisipuri și cu nivel variabil la argile, sau Proctor normal și modificat, în același program de laborator. Regula din 4.3 le-ar separa în campanii diferite. Se decide la proiectarea profilelor mecanice.
