---
license: cc-by-4.0
pretty_name: PetroDB
tags:
  - petroleum
  - reservoir-engineering
  - parquet
  - duckdb
---

# PetroDB

Public petroleum datasets served as a partitioned **parquet** tree, designed for
remote columnar queries with DuckDB `httpfs` (HTTP Range pushdown).

This Hugging Face dataset repo hosts the **parquet bytes only**. It mirrors the
`parquet/` root and is queried directly via `resolve` URLs, which honour HTTP
Range requests so consumers fetch only the row groups a predicate needs.

```sql
INSTALL httpfs; LOAD httpfs;
SELECT *
FROM 'https://huggingface.co/datasets/oskrgab/petrodb/resolve/main/<dataset>/...';
```

The human-facing landing page, per-dataset schema docs, and discovery manifests
live at **https://petrodb.ocortez.com/**.

- `main` — public production deployment
- `stage` — pre-production validation branch

See ADR-0005 in the project repository for the hosting rationale.

## Licences

Each Dataset keeps the licence of its source:

- `volve/`: **Equinor Open Data Licence**
  (<https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf>).
  It is based on CC BY 4.0: you may use the data for commercial and
  non-commercial purposes, share it and adapt it, but the data itself may not
  be sold. Credit Equinor and the former Volve licence partners (ExxonMobil
  Exploration & Production Norway AS and Bayerngas Norge AS), and link to the
  licence.
- `force_2020/`, `argentina/`, `petrobras_3w/`: CC BY 4.0, with the attribution
  each Dataset's page on the landing gives.
