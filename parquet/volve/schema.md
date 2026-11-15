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
wells.parent_npd_wellbore_code → wells.npd_wellbore_code
```
