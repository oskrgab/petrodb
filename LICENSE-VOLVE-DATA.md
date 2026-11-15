# Volve Dataset Licence

This project republishes data from the **Volve field dataset** (the Volve data
village), which Equinor and the former Volve licence partners released for
research, study and development.

## Licence

The Volve data is licensed under the **Equinor Open Data Licence**, published as
the Volve *Terms and Conditions for Use of License to Data*:

**[Equinor Open Data Licence: terms and conditions for the Volve data](https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf)**

Equinor's [Volve data sharing page](https://www.equinor.com/energy/volve-data-sharing)
grants the dataset under this licence. It replaced the earlier Creative Commons
non-commercial terms and applies to all the Volve data, including the copies in
this repository.

The licence is based on CC BY 4.0, with two changes that it states itself:

- The licensed material may not be sold.
- The licence covers all data in the dataset, whether or not it is by law
  covered by copyright.

It is not a Creative Commons licence, so do not describe the Volve data or
anything built from it as CC BY.

### Summary, in the licence's own words

The licence opens with a human-readable summary, which is not a substitute for
the licence itself:

You are free to:

- Download and use the Licensed Material for non-commercial and commercial purposes
- Create, produce and reproduce Adapted Material
- Share the Licensed Material and/or the Adapted Material

Under the following terms:

- You may not sell the Licensed Material.
- You must give Equinor and the Volve license partners credit, and provide a
  link to these terms and conditions, as well as a copyright notice if applicable
- You may not share Adapted Material under a license that prevents recipients
  from complying with these terms and conditions
- You shall not use the Licensed Material in a manner that appears misleading
  nor present the Licensed Material in a distorted or incorrect manner.

The licence also forbids using the names or trademarks of Equinor and the former
Volve licence partners to support, recommend or market your use of the data.

## Attribution

The licence asks you to credit Equinor **and** the former Volve licence
partners, which it names as:

- ExxonMobil Exploration & Production Norway AS
- Bayerngas Norge AS

(or their successors or permitted assignees), and to link to the licence text.
When you use or share this project's Volve data, include a notice such as:

> Contains data from the Volve field dataset, made available by Equinor and the
> former Volve licence partners (ExxonMobil Exploration & Production Norway AS
> and Bayerngas Norge AS) under the Equinor Open Data Licence:
> https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf

For academic citations:

```
Equinor and the former Volve licence partners (2018). Volve field dataset.
Available at: https://www.equinor.com/energy/volve-data-sharing
Licence: Equinor Open Data Licence,
https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf
```

## The wellbore register (NLOD)

The `wells` table also lists the Volve wellbores that never produced, and
gives every wellbore its type, purpose, content, completion year and parent
wellbore. Those come from the public wellbore register of the Norwegian
Offshore Directorate (formerly the Norwegian Petroleum Directorate), not from
the Volve dataset, and carry the register's own licence, the
**Norwegian Licence for Open Government Data (NLOD)**:
<https://data.norge.no/nlod/en>. When you use or share them, include:

> Contains data under the Norwegian Licence for Open Government Data (NLOD)
> distributed by the Norwegian Offshore Directorate.

The register snapshot the table is built from is published in the Volve Raw
repo, [`oskrgab/petrodb-raw-volve`](https://huggingface.co/datasets/oskrgab/petrodb-raw-volve),
under `register/`.

## Data processing

The original Volve dataset provides production data in Excel format. This
project transforms it into a structured SQLite database and exports it as
Parquet files:

- **Star schema design** with dimension and fact tables
- **Referential integrity** with proper foreign key relationships
- **Data validation** and quality checks
- **Parquet exports** for high-performance analytics

## Scope

### What the licence covers

- **Source data files** in `data/production/`
- **Generated database** in `database/volve.db`
- **Parquet exports** in `parquet/volve/`
- **Any other data** derived from the Volve dataset

### What it does not cover

- **Software code** in this repository
- **Documentation files** written for this project
- **ETL scripts and transformation logic**

The Volve licence applies to the **data content**, not to the software. You
may use this codebase with your own datasets.

## References

- **Licence text**: https://cdn.equinor.com/files/h61q9gi9/global/de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf
- **Volve data sharing page**: https://www.equinor.com/energy/volve-data-sharing

---

**Last Updated**: November 2026

**Disclaimer**: This document summarises the Volve licence for convenience. The
official terms and conditions linked above take precedence in case of any
discrepancy.
