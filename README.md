# PetroData Repository

Open petroleum datasets in Parquet format for data science and machine learning applications.

## Datasets

### Volve Production Data
Production metrics from the Equinor Volve oil field (2007-2016):
- **7 wells** with daily and monthly production records
- **15,634 daily measurements** - pressure, temperature, oil/gas/water volumes
- **526 monthly aggregates** - production volumes in Sm3

### FORCE 2020 Well Logs
Well log data from 108 wells in the Norwegian Continental Shelf:
- **29 columns** of petrophysical measurements per well
- **Log curves**: Gamma Ray (GR), Density (RHOB), Porosity (NPHI), Resistivity, Sonic
- **Lithofacies classifications** for machine learning applications

## Access Data

Browse and download files at: **https://dev-petrodb.ocortez.com**

## Quick Start

Query directly with DuckDB (no download required):

```python
import duckdb

conn = duckdb.connect()

# Query Volve production data
volve = conn.execute("""
    SELECT
        w.wellbore_name,
        SUM(d.oil_volume) as total_oil,
        SUM(d.gas_volume) as total_gas
    FROM 'https://dev-petrodb.ocortez.com/volve/daily_production.parquet' d
    JOIN 'https://dev-petrodb.ocortez.com/volve/wells.parquet' w
        ON d.npd_wellbore_code = w.npd_wellbore_code
    GROUP BY w.wellbore_name
    ORDER BY total_oil DESC
""").fetchdf()

# Query Force 2020 well logs
force = conn.execute("""
    SELECT
        WELL,
        AVG(GR) as avg_gamma_ray,
        AVG(RHOB) as avg_density,
        COUNT(*) as samples
    FROM 'https://dev-petrodb.ocortez.com/force_2020/wells/15-9-13.parquet'
    GROUP BY WELL
""").fetchdf()

# Query all 108 wells at once with wildcard
all_wells = conn.execute("""
    SELECT WELL, FORMATION, COUNT(*) as samples
    FROM 'https://dev-petrodb.ocortez.com/force_2020/wells/*.parquet'
    WHERE FORMATION IS NOT NULL
    GROUP BY WELL, FORMATION
    ORDER BY WELL, samples DESC
""").fetchdf()
```

Or download files locally and query:

```python
import duckdb

conn = duckdb.connect()

# Query local Volve files
result = conn.execute("""
    SELECT * FROM 'parquet/volve/daily_production.parquet'
    WHERE date BETWEEN '2008-01-01' AND '2008-12-31'
""").fetchdf()

# Query local Force 2020 files
well_data = conn.execute("""
    SELECT * FROM 'parquet/force_2020/wells/15-9-13.parquet'
    WHERE DEPTH_MD > 3000
""").fetchdf()
```

## Project Structure

```
parquet/
├── volve/                    # Volve production data
│   ├── daily_production.parquet
│   ├── monthly_production.parquet
│   ├── wells.parquet
│   └── schema.json
└── force_2020/               # FORCE 2020 well logs
    └── wells/                # 108 well files
        ├── 15-9-13.parquet
        ├── 34-10-16_R.parquet
        └── ... (106 more)
```

## Acknowledgments

- **Equinor** - Volve field dataset
- **FORCE (Norwegian Oil and Gas Association)** and **Xeek** - FORCE 2020 ML Competition dataset

Both datasets are provided for research and educational purposes.

## License

See original license terms:
- Volve: https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf
- FORCE 2020: https://xeek.ai/challenges/force-well-logs
