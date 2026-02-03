# Volve Database Schema

This document describes the structure of the Volve production database.

## Tables

### daily_production

**Columns:**

| Column | Type | Nullable | Primary Key | Comment |
|--------|------|----------|-------------|----------|
| date | DATE | No | ✓ |  |
| npd_wellbore_code | INTEGER | No | ✓ |  |
| on_stream_hours | FLOAT | Yes |  |  |
| avg_downhole_pressure | FLOAT | Yes |  |  |
| avg_dp_tubing | FLOAT | Yes |  |  |
| avg_annulus_pressure | FLOAT | Yes |  |  |
| avg_wellhead_pressure | FLOAT | Yes |  |  |
| avg_downhole_temperature | FLOAT | Yes |  |  |
| avg_wellhead_temperature | FLOAT | Yes |  |  |
| avg_choke_size_percent | FLOAT | Yes |  |  |
| avg_choke_unit | TEXT | Yes |  |  |
| dp_choke_size | FLOAT | Yes |  |  |
| oil_volume | FLOAT | Yes |  |  |
| gas_volume | FLOAT | Yes |  |  |
| water_volume | FLOAT | Yes |  |  |
| water_injection_volume | FLOAT | Yes |  |  |
| flow_kind | TEXT | Yes |  |  |
| well_type | TEXT | Yes |  |  |

**Foreign Keys:**

- `npd_wellbore_code` → `wells.npd_wellbore_code`

**Indexes:**

- `ix_daily_date`: date
- `ix_daily_wellbore`: npd_wellbore_code

---

### monthly_production

**Columns:**

| Column | Type | Nullable | Primary Key | Comment |
|--------|------|----------|-------------|----------|
| date | DATE | No | ✓ |  |
| npd_wellbore_code | INTEGER | No | ✓ |  |
| on_stream_hours | FLOAT | Yes |  |  |
| oil_volume_sm3 | FLOAT | Yes |  |  |
| gas_volume_sm3 | FLOAT | Yes |  |  |
| water_volume_sm3 | FLOAT | Yes |  |  |
| gas_injection_sm3 | FLOAT | Yes |  |  |
| water_injection_sm3 | FLOAT | Yes |  |  |

**Foreign Keys:**

- `npd_wellbore_code` → `wells.npd_wellbore_code`

**Indexes:**

- `ix_monthly_wellbore`: npd_wellbore_code
- `ix_monthly_date`: date

---

### wells

**Columns:**

| Column | Type | Nullable | Primary Key | Comment |
|--------|------|----------|-------------|----------|
| npd_wellbore_code | INTEGER | No | ✓ |  |
| wellbore_code | TEXT | No |  |  |
| wellbore_name | TEXT | No |  |  |
| npd_field_code | INTEGER | No |  |  |
| npd_field_name | TEXT | No |  |  |
| npd_facility_code | INTEGER | No |  |  |
| npd_facility_name | TEXT | No |  |  |

---

## Relationships

```
daily_production.npd_wellbore_code → wells.npd_wellbore_code
monthly_production.npd_wellbore_code → wells.npd_wellbore_code
```
