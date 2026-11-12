"""Compute the Landing's Glances and file listings (ADR-0010).

A Glance is a small finding about one Dataset, shown on the Landing as a chart
next to the query that produces it. This command runs each Glance's query with
DuckDB and writes the result as JSON under ``site/data/<dataset>/``; the site
build reads those files and never touches parquet.

The SQL a visitor sees is the SQL that ran here, with one substitution: the
data host. Queries are written against ``{base}``; they execute against the
local ``parquet/`` tree when the Dataset is committed there, and are published
with the Hugging Face resolve base in its place.

Run from the repo root after re-exporting a Dataset::

    uv run -m scripts.site.glances
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
PARQUET_ROOT = REPO_ROOT / "parquet"
OUT_ROOT = REPO_ROOT / "site" / "data"

# The host visitors query. Must equal `CANONICAL_HF_BASE` in
# `scripts/deploy/retarget_data_urls.py`.
PUBLIC_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main"

Rows = list[tuple[Any, ...]]


@dataclass(frozen=True)
class Glance:
    dataset: str
    id: str
    title: str
    sql: str
    # Turns the query's rows into {"takeaway": str, "chart": {...}}.
    build: Callable[[Rows], dict[str, Any]]
    # Optional hand-written equivalent for Polars users.
    polars: str | None = None
    # Datasets rebuilt in CI are not on disk; query the public host instead.
    remote: bool = False


def _nice_max(value: float) -> float:
    """Round up to the next clean scale end (3, 40, 500, ...)."""
    if value <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 1.5, 2, 3, 4, 5, 6, 8, 10):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


def _r(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)


# --------------------------------------------------------------------------
# Volve
# --------------------------------------------------------------------------

VOLVE_FIELD_SQL = """\
SELECT date_trunc('month', date) AS month,
       sum(oil_volume)   AS oil_sm3,
       sum(water_volume) AS water_sm3
FROM '{base}/volve/daily_production.parquet'
GROUP BY month
ORDER BY month;"""

VOLVE_FIELD_POLARS = """\
import polars as pl

url = "{base}/volve/daily_production.parquet"

monthly = (
    pl.scan_parquet(url)
    .group_by(pl.col("date").dt.truncate("1mo").alias("month"))
    .agg(
        pl.col("oil_volume").sum().alias("oil_sm3"),
        pl.col("water_volume").sum().alias("water_sm3"),
    )
    .sort("month")
    .collect()
)"""


def _volve_field(rows: Rows) -> dict[str, Any]:
    rows = [r for r in rows if r[1] is not None]
    months = [r[0].strftime("%Y-%m") for r in rows]
    oil = [r[1] / 1e3 for r in rows]
    water = [r[2] / 1e3 for r in rows]
    peak = max(range(len(oil)), key=oil.__getitem__)
    # First month after which water exceeds oil in every remaining month.
    crossover = next(
        i for i in range(peak, len(oil))
        if all(w > o for w, o in zip(water[i:], oil[i:]))
    )
    top = _nice_max(max(max(oil), max(water)))
    return {
        "takeaway": (
            f"Oil peaked at {oil[peak]:.0f} thousand Sm³ a month in "
            f"{rows[peak][0]:%B %Y}. From {rows[crossover][0]:%B %Y} the field "
            "produced more water than oil every month until production "
            f"stopped in {rows[-1][0]:%Y}."
        ),
        "chart": {
            "kind": "lines",
            "x": {"type": "month", "values": months},
            "series": [
                {"name": "Oil", "unit": "thousand Sm³ / month", "tone": "oil",
                 "min": 0, "max": top, "values": [_r(v, 2) for v in oil]},
                {"name": "Water", "unit": "thousand Sm³ / month", "tone": "water",
                 "min": 0, "max": top, "values": [_r(v, 2) for v in water]},
            ],
        },
    }


# --------------------------------------------------------------------------
# Argentina
# --------------------------------------------------------------------------

# Every Argentina query over `monthly_production` starts by resolving the
# Manifest into a URL list (ADR-0004): a static host cannot be globbed.
ARGENTINA_MANIFEST_SQL = """\
SET VARIABLE monthly_production = (
    SELECT list('{base}/argentina/monthly_production/' || path)
    FROM read_json('{base}/argentina/monthly_production/_files.json') AS manifest(path)
);
"""

ARGENTINA_RESOURCE_SQL = ARGENTINA_MANIFEST_SQL + """
SELECT p.anio AS year,
       CASE w.tipo_recurso
           WHEN 'NO CONVENCIONAL' THEN 'Unconventional'
           WHEN 'CONVENCIONAL'    THEN 'Conventional'
           ELSE 'Not reported'
       END AS resource,
       sum(p.prod_pet) / 1e6 AS oil_million_m3
FROM read_parquet(getvariable('monthly_production'), hive_partitioning = true) AS p
JOIN '{base}/argentina/wells.parquet' AS w USING (idpozo)
GROUP BY ALL
ORDER BY year, resource;"""


def _argentina_resource(rows: Rows) -> dict[str, Any]:
    years = sorted({r[0] for r in rows})
    by = {(r[0], r[1]): r[2] or 0.0 for r in rows}
    order = [("Unconventional", "oil"), ("Conventional", "oil-2"), ("Not reported", "neutral")]
    series = [
        {"name": name, "tone": tone,
         "values": [_r(by.get((y, name), 0.0)) for y in years]}
        for name, tone in order
    ]
    totals = [sum(s["values"][i] for s in series) for i in range(len(years))]
    unconventional = series[0]["values"]
    conventional = series[1]["values"]
    overtook = next(
        y for y, u, c in zip(years, unconventional, conventional) if u > c
    )
    low = min(range(len(totals)), key=totals.__getitem__)
    return {
        "takeaway": (
            f"Unconventional wells produced {unconventional[0] * 1e3:.0f} "
            f"thousand m³ of oil in {years[0]} and {unconventional[-1]:.1f} "
            f"million in {years[-1]}. They overtook conventional output in {overtook} and "
            f"lifted the national total from its {years[low]} low of "
            f"{totals[low]:.0f} million m³ to {totals[-1]:.0f} million."
        ),
        "chart": {
            "kind": "stacked",
            "unit": "million m³ of oil / year",
            "min": 0,
            "max": _nice_max(max(totals)),
            "x": {"type": "year", "values": years},
            "series": series,
        },
    }


ARGENTINA_BASIN_SQL = ARGENTINA_MANIFEST_SQL + """
SELECT w.cuenca AS basin,
       sum(p.prod_pet) / 1e6 AS oil_million_m3,
       sum(p.prod_gas) / 1e6 AS gas_billion_m3   -- prod_gas is in thousand m³
FROM read_parquet(getvariable('monthly_production'), hive_partitioning = true) AS p
JOIN '{base}/argentina/wells.parquet' AS w USING (idpozo)
GROUP BY basin
HAVING oil_million_m3 >= 1 OR gas_billion_m3 >= 1
ORDER BY oil_million_m3 DESC;"""


def _argentina_basin(rows: Rows) -> dict[str, Any]:
    basins = [str(r[0]).title() for r in rows]
    oil = [r[1] for r in rows]
    gas = [r[2] for r in rows]
    top_two = (oil[0] + oil[1]) / sum(oil)
    by_gas = sorted(range(len(gas)), key=gas.__getitem__, reverse=True)
    gas_leader, gas_second = by_gas[0], by_gas[1]
    oil_share_of_second = oil[gas_second] / sum(oil)
    return {
        "takeaway": (
            f"Totals for 2006 to 2025. {basins[0]} and {basins[1]} produced "
            f"{top_two:.0%} of the oil. Gas is a different map: {basins[gas_leader]} "
            f"leads, and {basins[gas_second]} ranks second with only "
            f"{oil_share_of_second:.0%} of the oil."
        ),
        "chart": {
            "kind": "bars",
            "x": {"type": "category", "values": basins},
            "series": [
                {"name": "Oil", "unit": "million m³", "tone": "oil",
                 "min": 0, "max": _nice_max(max(oil)), "values": [_r(v, 1) for v in oil]},
                {"name": "Gas", "unit": "billion m³", "tone": "gas",
                 "min": 0, "max": _nice_max(max(gas)), "values": [_r(v, 1) for v in gas]},
            ],
        },
    }


ARGENTINA_ACTIVE_SQL = ARGENTINA_MANIFEST_SQL + """
SELECT anio AS year,
       count(DISTINCT idpozo) AS producing_wells
FROM read_parquet(getvariable('monthly_production'), hive_partitioning = true)
WHERE prod_pet > 0 OR prod_gas > 0
GROUP BY year
ORDER BY year;"""


def _argentina_active(rows: Rows) -> dict[str, Any]:
    years = [r[0] for r in rows]
    wells = [r[1] / 1e3 for r in rows]
    peak = max(range(len(wells)), key=wells.__getitem__)
    return {
        "takeaway": (
            f"The number of wells that produced in a year peaked at "
            f"{rows[peak][1]:,} in {years[peak]} and has drifted down since, "
            "while oil output rose: fewer wells, each producing more."
        ),
        "chart": {
            "kind": "lines",
            "x": {"type": "year", "values": years},
            "series": [
                {"name": "Wells with production", "unit": "thousand wells / year",
                 "tone": "ink", "min": 0, "max": _nice_max(max(wells)),
                 "values": [_r(v, 2) for v in wells]},
            ],
        },
    }


# --------------------------------------------------------------------------
# FORCE 2020
# --------------------------------------------------------------------------

FORCE_GR_SQL = """\
SELECT floor(DEPTH_MD / 5) * 5 AS depth_m,
       avg(GR) AS gamma_ray_api
FROM '{base}/force_2020/wells/15-9-13.parquet'
GROUP BY depth_m
ORDER BY depth_m;"""


def _force_gr(rows: Rows) -> dict[str, Any]:
    rows = [r for r in rows if r[1] is not None]
    depth = [r[0] for r in rows]
    gr = [r[1] for r in rows]
    return {
        "takeaway": (
            f"Gamma ray in well 15/9-13 from {depth[0]:,.0f} m to "
            f"{depth[-1]:,.0f} m, averaged every 5 m. High readings mark "
            "shale; low readings mark cleaner sand and carbonate."
        ),
        "chart": {
            "kind": "lines",
            "x": {"type": "depth", "values": depth},
            "series": [
                {"name": "Gamma ray", "unit": "API", "tone": "ink", "min": 0,
                 "max": _nice_max(max(gr)), "values": [_r(v, 1) for v in gr]},
            ],
        },
    }


# --------------------------------------------------------------------------
# Petrobras 3W
# --------------------------------------------------------------------------

W3_HYDRATE_INSTANCE = "WELL-00032_20110830235321"

W3_HYDRATE_SQL = """\
SELECT time_bucket(INTERVAL 10 MINUTE, timestamp) AS t,
       avg("P-TPT") / 1e5 AS p_tpt_bar,   -- sensors report pascals
       max(class) AS label
FROM '{base}/petrobras_3w/observations/event_class=8/%s.parquet'
GROUP BY t
ORDER BY t;""" % W3_HYDRATE_INSTANCE


W3_HYDRATE_CLASS = 8


def _span(name: str, labels: list[Any], code: int) -> dict[str, Any]:
    """The first and last x index whose label is ``code``."""
    hits = [i for i, label in enumerate(labels) if label == code]
    return {"name": name, "from": hits[0], "to": hits[-1]}


def _w3_hydrate(rows: Rows) -> dict[str, Any]:
    rows = [r for r in rows if r[1] is not None]
    pressure = [r[1] for r in rows]
    labels = [r[2] for r in rows]
    labelled = next(i for i, r in enumerate(rows) if r[2])
    before = sum(pressure[:labelled]) / labelled
    hours = (rows[-1][0] - rows[0][0]).total_seconds() / 3600
    return {
        "takeaway": (
            f"One Instance, {hours:.0f} hours at 1 Hz, labelled as hydrate "
            f"forming in the production line. Pressure at the tree held near "
            f"{before:.0f} bar, then rose to {max(pressure):.0f} bar once the "
            f"anomaly label starts at {rows[labelled][0]:%H:%M}."
        ),
        "chart": {
            "kind": "lines",
            "x": {"type": "time", "values": [r[0].isoformat() for r in rows]},
            "series": [
                {"name": "P-TPT, pressure at the tree", "unit": "bar",
                 "tone": "gas", "min": 0, "max": _nice_max(max(pressure)),
                 "values": [_r(v, 2) for v in pressure]},
            ],
            # Each 10-minute bucket carries its highest label, so the
            # transient code (event + 100) wins the bucket it starts in.
            "spans": [
                _span("Transient", labels, W3_HYDRATE_CLASS + 100),
                _span("Steady", labels, W3_HYDRATE_CLASS),
            ],
        },
    }


W3_BY_CLASS_SQL = """\
SELECT e.description AS event_class,
       count(*) FILTER (WHERE i.well_kind = 'real')      AS real_wells,
       count(*) FILTER (WHERE i.well_kind = 'simulated') AS simulated,
       count(*) FILTER (WHERE i.well_kind = 'drawn')     AS drawn
FROM '{base}/petrobras_3w/instances.parquet' AS i
JOIN '{base}/petrobras_3w/event_types.parquet' AS e USING (event_class)
GROUP BY e.event_class, e.description
ORDER BY e.event_class;"""


def _w3_by_class(rows: Rows) -> dict[str, Any]:
    classes = [r[0] for r in rows]
    real, simulated, drawn = ([r[k] for r in rows] for k in (1, 2, 3))
    total = sum(real) + sum(simulated) + sum(drawn)
    top = _nice_max(max(real + simulated + drawn))
    # Row 0 is Normal Operation; the anomalies follow.
    only_real = [c for c, s, d in zip(classes[1:], simulated[1:], drawn[1:]) if s + d == 0]
    mostly_sim = max(range(len(rows)), key=simulated.__getitem__)
    return {
        "takeaway": (
            f"{total:,} Instances. Real wells supply {sum(real):,}, "
            f"{real[0]} of them {classes[0]}. Among the anomalies, "
            f"{' and '.join(only_real)} {'comes' if len(only_real) == 1 else 'come'} "
            "only from real wells; "
            f"{classes[mostly_sim]} is mostly simulated "
            f"({simulated[mostly_sim]} of {real[mostly_sim] + simulated[mostly_sim] + drawn[mostly_sim]})."
        ),
        "chart": {
            "kind": "bars",
            "x": {"type": "category", "values": classes},
            "series": [
                {"name": name, "unit": "Instances", "tone": tone,
                 "min": 0, "max": top, "values": values}
                for name, tone, values in (
                    ("Real", "oil", real),
                    ("Simulated", "water", simulated),
                    ("Drawn", "gas", drawn),
                )
            ],
        },
    }


GLANCES: list[Glance] = [
    Glance("volve", "field-rates", "A field's whole life in one query",
           VOLVE_FIELD_SQL, _volve_field, polars=VOLVE_FIELD_POLARS),
    Glance("argentina", "oil-by-resource", "Shale took over Argentina's oil",
           ARGENTINA_RESOURCE_SQL, _argentina_resource),
    Glance("argentina", "basins", "Two basins for oil, a third for gas",
           ARGENTINA_BASIN_SQL, _argentina_basin),
    Glance("argentina", "producing-wells", "More oil from fewer wells",
           ARGENTINA_ACTIVE_SQL, _argentina_active),
    Glance("force_2020", "gamma-ray", "A well log, top to bottom",
           FORCE_GR_SQL, _force_gr),
    Glance("petrobras_3w", "hydrate-pressure", "An anomaly as the sensors saw it",
           W3_HYDRATE_SQL, _w3_hydrate, remote=True),
    Glance("petrobras_3w", "instances-by-class", "Real, simulated and hand-drawn",
           W3_BY_CLASS_SQL, _w3_by_class, remote=True),
]


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------

# The Petrobras 3W page groups its Observation files by Event class. The page
# is built only where the 3W tree exists, but the names are committed so the
# build never needs to read parquet.
W3_EVENT_CLASSES_SQL = """\
SELECT event_class, description
FROM '{base}/petrobras_3w/event_types.parquet'
ORDER BY event_class;"""


def w3_event_classes() -> list[dict[str, Any]]:
    rows = duckdb.sql(W3_EVENT_CLASSES_SQL.format(base=PUBLIC_BASE)).fetchall()
    return [{"event_class": c, "description": d} for c, d in rows]


# --------------------------------------------------------------------------
# File listings
# --------------------------------------------------------------------------


def _parquet_rows(path: Path) -> int:
    return duckdb.sql(
        f"SELECT sum(num_rows) FROM parquet_file_metadata('{path}')"
    ).fetchone()[0]


def list_files(dataset: str) -> list[dict[str, Any]] | None:
    """Describe a committed Dataset's tables: sizes, row counts, member files.

    A directory holding a Manifest is one Multi-parquet table; any other
    ``*.parquet`` at the Dataset root is a single-file table.
    """
    root = PARQUET_ROOT / dataset
    if not root.is_dir():
        return None
    tables: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.parquet")):
        tables.append({
            "name": path.stem, "kind": "single", "path": path.name,
            "bytes": path.stat().st_size, "rows": _parquet_rows(path),
        })
    for manifest in sorted(root.glob("*/_files.json")):
        members = []
        for rel in json.loads(manifest.read_text()):
            member = manifest.parent / rel
            members.append({
                "path": f"{manifest.parent.name}/{rel}",
                "bytes": member.stat().st_size, "rows": _parquet_rows(member),
            })
        tables.append({
            "name": manifest.parent.name, "kind": "multi",
            "manifest": f"{manifest.parent.name}/_files.json",
            "bytes": sum(m["bytes"] for m in members),
            "rows": sum(m["rows"] for m in members),
            "files": members,
        })
    return tables


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def run_glance(glance: Glance) -> dict[str, Any]:
    base = PUBLIC_BASE if glance.remote else str(PARQUET_ROOT)
    con = duckdb.connect()
    rows = con.execute(glance.sql.format(base=base)).fetchall()
    built = glance.build(rows)
    out = {
        "id": glance.id,
        "title": glance.title,
        "takeaway": built["takeaway"],
        "sql": glance.sql.format(base=PUBLIC_BASE),
        "chart": built["chart"],
    }
    if glance.polars:
        out["polars"] = glance.polars.format(base=PUBLIC_BASE)
    return out


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for glance in GLANCES:
        by_dataset.setdefault(glance.dataset, []).append(run_glance(glance))
    for dataset, glances in by_dataset.items():
        _write(OUT_ROOT / dataset / "glances.json", glances)
        files = list_files(dataset)
        if files is not None:
            _write(OUT_ROOT / dataset / "files.json", files)
    _write(OUT_ROOT / "petrobras_3w" / "event_classes.json", w3_event_classes())


if __name__ == "__main__":
    main()
