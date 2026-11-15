# Volve Database Schema

This document describes the structure of the Volve production database.

## Tables

### `daily_production`

Daily measurements per wellbore, from Equinor's daily production report: hours on stream, pressures, temperatures, choke opening and the volumes produced or injected. One row per `(date, npd_wellbore_code)`. Volumes are in standard cubic metres (Sm³).

**Columns:**

| Column | Type | Nullable | Primary Key | Description |
|--------|------|----------|-------------|-------------|
| `date` | DATE | No | ✓ | Production day (source `DATEPRD`). Stored in the Parquet file as a timestamp at midnight. |
| `npd_wellbore_code` | INTEGER | No | ✓ | Wellbore the row belongs to. Joins to `wells`. |
| `on_stream_hours` | FLOAT | Yes |  | Hours the wellbore was producing or injecting that day (`ON_STREAM_HRS`). Up to 25 on the day the clocks go back. |
| `avg_downhole_pressure` | FLOAT | Yes |  | Average pressure at the downhole gauge over the day, in bar (`AVG_DOWNHOLE_PRESSURE`). |
| `avg_dp_tubing` | FLOAT | Yes |  | Average pressure drop along the production tubing, from the downhole gauge to the wellhead, in bar (`AVG_DP_TUBING`). |
| `avg_annulus_pressure` | FLOAT | Yes |  | Average pressure in the annulus between tubing and casing, in bar (`AVG_ANNULUS_PRESS`). |
| `avg_wellhead_pressure` | FLOAT | Yes |  | Average pressure at the wellhead, in bar (`AVG_WHP_P`). |
| `avg_downhole_temperature` | FLOAT | Yes |  | Average temperature at the downhole gauge, in °C (`AVG_DOWNHOLE_TEMPERATURE`). |
| `avg_wellhead_temperature` | FLOAT | Yes |  | Average temperature at the wellhead, in °C (`AVG_WHT_P`). |
| `avg_choke_size_percent` | FLOAT | Yes |  | Average production choke opening, as a percentage of fully open (`AVG_CHOKE_SIZE_P`). |
| `avg_choke_unit` | TEXT | Yes |  | Unit of `avg_choke_size_percent`: `%`, or NULL on injection rows (`AVG_CHOKE_UOM`). |
| `dp_choke_size` | FLOAT | Yes |  | Pressure drop across the production choke, in bar (`DP_CHOKE_SIZE`). |
| `oil_volume` | FLOAT | Yes |  | Oil produced from the wellbore that day, in Sm³ (`BORE_OIL_VOL`). |
| `gas_volume` | FLOAT | Yes |  | Gas produced from the wellbore that day, in Sm³ (`BORE_GAS_VOL`). |
| `water_volume` | FLOAT | Yes |  | Water produced from the wellbore that day, in Sm³ (`BORE_WAT_VOL`). A few rows are negative, kept as the source reports them. |
| `water_injection_volume` | FLOAT | Yes |  | Water injected into the wellbore that day, in Sm³ (`BORE_WI_VOL`). Filled on injection rows and on a handful of production rows. |
| `flow_kind` | TEXT | Yes |  | Direction of flow that day: `production` or `injection` (`FLOW_KIND`). |
| `well_type` | TEXT | Yes |  | Role of the wellbore that day: `OP` oil producer, `WI` water injector (`WELL_TYPE`). Can change over a wellbore's life. |

**Foreign Keys:**

- `npd_wellbore_code` → `wells.npd_wellbore_code`

**Indexes:**

- `ix_daily_date`: date
- `ix_daily_wellbore`: npd_wellbore_code

---

### `monthly_production`

Monthly volumes per wellbore, from Equinor's monthly production report. One row per `(date, npd_wellbore_code)`, where `date` is the first day of the month. Volumes are in standard cubic metres (Sm³).

**Columns:**

| Column | Type | Nullable | Primary Key | Description |
|--------|------|----------|-------------|-------------|
| `date` | DATE | No | ✓ | First day of the month the volumes cover, built from the source `Year` and `Month`. Stored in the Parquet file as a timestamp. |
| `npd_wellbore_code` | INTEGER | No | ✓ | Wellbore the row belongs to. Joins to `wells`. |
| `on_stream_hours` | FLOAT | Yes |  | Hours the wellbore was on stream in the month (`On Stream`). |
| `oil_volume_sm3` | FLOAT | Yes |  | Oil produced in the month, in Sm³ (`Oil`). |
| `gas_volume_sm3` | FLOAT | Yes |  | Gas produced in the month, in Sm³ (`Gas`). |
| `water_volume_sm3` | FLOAT | Yes |  | Water produced in the month, in Sm³ (`Water`). |
| `gas_injection_sm3` | FLOAT | Yes |  | Gas injected in the month, in Sm³ (`GI`). Empty in every row of the source. |
| `water_injection_sm3` | FLOAT | Yes |  | Water injected in the month, in Sm³ (`WI`). |

**Foreign Keys:**

- `npd_wellbore_code` → `wells.npd_wellbore_code`

**Indexes:**

- `ix_monthly_date`: date
- `ix_monthly_wellbore`: npd_wellbore_code

---

### `petrophysical_interpretation`

Well-log Curves of Equinor's petrophysical interpretation, one row per depth sample of each logged wellbore: the Input curves the interpretation took (gamma ray, density, neutron, sonic, resistivity) and the Interpreted curves it computed (porosity, water saturation, shale volume, permeability, lithology flags) side by side. One row per `(source_wellbore, depth_md)`. Each Curve column is named with the source mnemonic and is empty where the wellbore has no sample. Each Curve has one documented unit, stated with the column: the source files spell it several ways, and the values are kept as the source gives them, never converted. Samples are at the source depths; nothing is resampled. Built from the raw log files; the Parquet is not in git.

**Columns:**

| Column | Type | Unit | Nullable | Primary Key | Description |
|--------|------|------|----------|-------------|-------------|
| `npd_wellbore_code` | INTEGER | — | No |  | Wellbore the row belongs to. Joins to `wells`. For a Technical sidetrack, the code of its parent Wellbore. |
| `source_wellbore` | TEXT | — | No | ✓ | The operator's name for the logged wellbore, such as `15/9-F-1 A`, taken from the folder the source files sit in. Usually the name of the Wellbore in `npd_wellbore_code`. A Technical sidetrack, such as `15/9-F-11 T2`, is a re-drilled section the register does not count as a Wellbore: its rows carry the `npd_wellbore_code` of its parent Wellbore (`15/9-F-11`) and keep the Technical sidetrack's name here. The 15/9-F-11 top-hole section is `15/9-F-11`: it has Input curves only, and it overlaps the depths of `15/9-F-11 T2` with different values. Filter on `npd_wellbore_code` for everything logged under a Wellbore, on `source_wellbore` for one of its sources. |
| `depth_md` | DOUBLE | m | No | ✓ | Measured depth along the wellbore, in metres, rounded to four decimals so that equality joins are stable. Source files that index depth in tenths of an inch or in millimetres are converted to metres before rounding. The depth reference is the one the source file uses; it is not normalised. |
| `ABDCQF01` | DOUBLE | g/cm³ | Yes |  | Bulk density from quadrant 1 of an azimuthal density measurement while drilling. |
| `ABDCQF02` | DOUBLE | g/cm³ | Yes |  | Bulk density from quadrant 2 of an azimuthal density measurement while drilling. |
| `ABDCQF03` | DOUBLE | g/cm³ | Yes |  | Bulk density from quadrant 3 of an azimuthal density measurement while drilling. |
| `ABDCQF04` | DOUBLE | g/cm³ | Yes |  | Bulk density from quadrant 4 of an azimuthal density measurement while drilling. |
| `BS` | DOUBLE | in | Yes |  | Bit size: nominal diameter of the drilled hole. |
| `CALI` | DOUBLE | in | Yes |  | Caliper: measured borehole diameter. |
| `DRHB` | DOUBLE | g/cm³ | Yes |  | Density correction applied to `ROBB`, the bulk density from the bottom of the borehole, measured while drilling. |
| `DRHO` | DOUBLE | g/cm³ | Yes |  | Density correction applied to the bulk density. |
| `DRHU` | DOUBLE | g/cm³ | Yes |  | Density correction applied to `ROBU`, the bulk density from the top of the borehole, measured while drilling. |
| `DT` | DOUBLE | µs/ft | Yes |  | Compressional sonic slowness. |
| `DTS` | DOUBLE | µs/ft | Yes |  | Shear sonic slowness. |
| `GR` | DOUBLE | gAPI | Yes |  | Natural gamma ray. |
| `NBGRCFM` | DOUBLE | gAPI | Yes |  | Natural gamma ray measured near the bit while drilling. |
| `NPHI` | DOUBLE | v/v | Yes |  | Neutron porosity, as a fraction. |
| `PEF` | DOUBLE | b/e | Yes |  | Photoelectric factor. |
| `RACEHM` | DOUBLE | ohm·m | Yes |  | Propagation resistivity while drilling, from the attenuation of the high-frequency signal. |
| `RACELM` | DOUBLE | ohm·m | Yes |  | Propagation resistivity while drilling, from the attenuation of the low-frequency signal. |
| `RD` | DOUBLE | ohm·m | Yes |  | Deep resistivity. |
| `RHOB` | DOUBLE | g/cm³ | Yes |  | Bulk density. |
| `RM` | DOUBLE | ohm·m | Yes |  | Medium resistivity. |
| `ROBB` | DOUBLE | g/cm³ | Yes |  | Bulk density from the bottom of the borehole, measured while drilling by a rotating density tool. |
| `ROBU` | DOUBLE | g/cm³ | Yes |  | Bulk density from the top of the borehole, measured while drilling by a rotating density tool. |
| `ROP` | DOUBLE | m/h | Yes |  | Rate of penetration while drilling. |
| `ROP5_RM` | DOUBLE | m/h | Yes |  | Rate of penetration while drilling, a second recording. Its file leaves the unit unknown; its values lie in the range `ROP` has in the other wellbores, so it is documented in the same unit. |
| `RPCEHM` | DOUBLE | ohm·m | Yes |  | Propagation resistivity while drilling, from the phase shift of the high-frequency signal. |
| `RPCELM` | DOUBLE | ohm·m | Yes |  | Propagation resistivity while drilling, from the phase shift of the low-frequency signal. |
| `RS` | DOUBLE | ohm·m | Yes |  | Shallow resistivity. |
| `RT` | DOUBLE | ohm·m | Yes |  | True formation resistivity, as the interpreter selected it. |
| `BADDATA_FLAG` | DOUBLE | unitless | Yes |  | Interpreted flag: 1 where the interpreter judged the log data unreliable, 0 elsewhere. |
| `BVW` | DOUBLE | v/v | Yes |  | Bulk volume of water: porosity times water saturation, as a fraction of rock volume. |
| `CARB_FLAG` | DOUBLE | unitless | Yes |  | Lithology flag: 1 where the interpretation marks carbonate, 0 elsewhere. |
| `COAL_FLAG` | DOUBLE | unitless | Yes |  | Lithology flag: 1 where the interpretation marks coal, 0 elsewhere. |
| `KLOGH` | DOUBLE | mD | Yes |  | Horizontal permeability computed from the logs. |
| `PHID` | DOUBLE | v/v | Yes |  | Porosity computed from the bulk density, as a fraction. |
| `PHIF` | DOUBLE | v/v | Yes |  | Final effective porosity from the interpretation, as a fraction. |
| `SAND_FLAG` | DOUBLE | unitless | Yes |  | Lithology flag: 1 where the interpretation marks sand, 0 elsewhere. |
| `SW` | DOUBLE | v/v | Yes |  | Water saturation from the interpretation, as a fraction of pore volume. |
| `VCARB` | DOUBLE | v/v | Yes |  | Volume of carbonate minerals (calcite, dolomite, siderite), as a fraction. |
| `VSH` | DOUBLE | v/v | Yes |  | Shale volume, as a fraction. |

**Foreign Keys:**

- `npd_wellbore_code` → `wells.npd_wellbore_code`

---

### `wells`

One row per wellbore the public wellbore register of the Norwegian Offshore Directorate assigns to the Volve field, drilled or not: its identifiers, the register's classification and the wellbore it was drilled from. The production columns come from Equinor's production report and are empty for a wellbore without production; `has_production` marks the wellbores that have production rows.

**Columns:**

| Column | Type | Nullable | Primary Key | Description |
|--------|------|----------|-------------|-------------|
| `npd_wellbore_code` | INTEGER | No | ✓ | Wellbore identifier assigned by the Norwegian Offshore Directorate (formerly the Norwegian Petroleum Directorate, NPD). The key every production row joins on. |
| `wellbore_code` | TEXT | Yes |  | Equinor's wellbore code, prefixed with the country (e.g. `NO 15/9-F-12 H`), from the production report. Empty for a wellbore without production. |
| `wellbore_name` | TEXT | No |  | NPD wellbore name (e.g. `15/9-F-12`, a well in block 15/9). Use this to label wells. |
| `npd_field_code` | INTEGER | No |  | NPD field identifier. The same value on every row: Volve. |
| `npd_field_name` | TEXT | No |  | Field name: `VOLVE` on every row. |
| `npd_facility_code` | INTEGER | Yes |  | NPD identifier of the facility the wellbore produced through. Empty for a wellbore without production. |
| `npd_facility_name` | TEXT | Yes |  | Facility the wellbore produced through: the `MÆRSK INSPIRER` jack-up production unit. Empty for a wellbore without production. |
| `wellbore_type` | TEXT | No |  | Register well type: `DEVELOPMENT` for the wellbores drilled to develop the field, `EXPLORATION` for those drilled to find and appraise it (source `wlbWellType`). |
| `purpose` | TEXT | No |  | What the register says the wellbore was drilled for: `PRODUCTION`, `INJECTION` or `OBSERVATION` for a development wellbore, `WILDCAT` or `APPRAISAL` for an exploration one (source `wlbPurpose`). |
| `content` | TEXT | Yes |  | What the register says the wellbore found or carries, such as `OIL`, `WATER`, `SHOWS`, `DRY` or `NOT APPLICABLE` (source `wlbContent`). Empty for a wellbore that was never drilled. |
| `completion_year` | INTEGER | Yes |  | Year the wellbore was completed, from the register (source `wlbCompletionYear`). Empty for a wellbore that was never drilled. |
| `parent_npd_wellbore_code` | INTEGER | Yes |  | `npd_wellbore_code` of the wellbore this one was sidetracked or re-entered from, itself a row of this table (source `wlbDiskosWellboreParent`). Empty for a wellbore drilled from the surface. |
| `has_production` | BOOLEAN | No |  | True when the wellbore has rows in the production tables, `daily_production` and `monthly_production`; false otherwise. |

**Foreign Keys:**

- `parent_npd_wellbore_code` → `wells.npd_wellbore_code`

---

## Relationships

```
daily_production.npd_wellbore_code → wells.npd_wellbore_code
monthly_production.npd_wellbore_code → wells.npd_wellbore_code
petrophysical_interpretation.npd_wellbore_code → wells.npd_wellbore_code
wells.parent_npd_wellbore_code → wells.npd_wellbore_code
```
