"""Compute the Landing's Glances, Dataset facts and file listings (ADR-0010).

A Glance is a small finding about one Dataset, shown on the Landing as a chart
next to the query that produces it. This command runs each Glance's query with
DuckDB and writes the result as JSON under ``site/data/<dataset>/``; the site
build reads those files and never touches parquet. Next to the Glances it
writes ``facts.json`` (the catalogue's "Covers" text and byte size, both
computed from the data) and, for a Dataset on disk, ``files.json``.

The SQL a visitor sees is the SQL that ran here, with one substitution: the
data host. Queries are written against ``{base}``; they execute against the
local ``parquet/`` tree when the Dataset is on disk there, and against the
public host otherwise. They are published with the Hugging Face resolve base.

Each export pipeline runs this for its Dataset as its last step. By hand, from
the repo root::

    uv run -m scripts.site.glances [dataset ...]          # regenerate
    uv run -m scripts.site.glances --check [dataset ...]  # fail if stale
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.request
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
# The same files, listed with their sizes by the Hugging Face Hub API.
PUBLIC_TREE = "https://huggingface.co/api/datasets/oskrgab/petrodb/tree/main"

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


@dataclass(frozen=True)
class Facts:
    """How a Dataset's catalogue "Covers" text is computed: one query, one row."""

    dataset: str
    sql: str
    covers: Callable[[tuple[Any, ...]], str]


def on_disk(dataset: str) -> bool:
    return (PARQUET_ROOT / dataset).is_dir()


def _base(dataset: str) -> str:
    """Query the local tree when the Dataset is on disk, the public host otherwise."""
    return str(PARQUET_ROOT) if on_disk(dataset) else PUBLIC_BASE


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
       sum(gas_volume)   AS gas_sm3,
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
        pl.col("gas_volume").sum().alias("gas_sm3"),
        pl.col("water_volume").sum().alias("water_sm3"),
    )
    .sort("month")
    .collect()
)"""


def _volve_field(rows: Rows) -> dict[str, Any]:
    rows = [r for r in rows if r[1] is not None]
    months = [r[0].strftime("%Y-%m") for r in rows]
    oil = [r[1] / 1e3 for r in rows]
    gas = [(r[2] or 0.0) / 1e6 for r in rows]
    water = [(r[3] or 0.0) / 1e3 for r in rows]
    peak = max(range(len(oil)), key=oil.__getitem__)
    # First month after which water exceeds oil in every remaining month.
    crossover = next(
        i for i in range(peak, len(oil))
        if all(w > o for w, o in zip(water[i:], oil[i:]))
    )
    # Gas and oil are both in Sm³; the ratio is the field's producing GOR.
    gas_per_oil = sum(gas) * 1e6 / (sum(oil) * 1e3)
    top = _nice_max(max(max(oil), max(water)))
    return {
        "takeaway": (
            f"Oil peaked at {oil[peak]:.0f} thousand Sm³ a month in "
            f"{rows[peak][0]:%B %Y}. Gas came with it, about "
            f"{gas_per_oil:.0f} Sm³ of gas for every Sm³ of oil. From "
            f"{rows[crossover][0]:%B %Y} the field produced more water than "
            f"oil every month until production stopped in {rows[-1][0]:%Y}."
        ),
        "chart": {
            "kind": "lines",
            "x": {"type": "month", "values": months},
            "series": [
                {"name": "Oil", "unit": "thousand Sm³ / month", "tone": "oil",
                 "min": 0, "max": top, "values": [_r(v, 2) for v in oil]},
                {"name": "Gas", "unit": "million Sm³ / month", "tone": "gas",
                 "min": 0, "max": _nice_max(max(gas)), "values": [_r(v, 2) for v in gas]},
                {"name": "Water", "unit": "thousand Sm³ / month", "tone": "water",
                 "min": 0, "max": top, "values": [_r(v, 2) for v in water]},
            ],
        },
    }


VOLVE_WELLS_SQL = """\
SELECT w.wellbore_name AS well,
       coalesce(sum(d.oil_volume), 0) / 1e6             AS oil_million_sm3,
       coalesce(sum(d.water_injection_volume), 0) / 1e6 AS water_injected_million_sm3
FROM '{base}/volve/daily_production.parquet' AS d
JOIN '{base}/volve/wells.parquet' AS w USING (npd_wellbore_code)
GROUP BY well
ORDER BY oil_million_sm3 DESC;"""

VOLVE_WELLS_POLARS = """\
import polars as pl

daily = pl.scan_parquet("{base}/volve/daily_production.parquet")
wells = pl.scan_parquet("{base}/volve/wells.parquet")

by_well = (
    daily.join(wells, on="npd_wellbore_code")
    .group_by(pl.col("wellbore_name").alias("well"))
    .agg(
        (pl.col("oil_volume").sum() / 1e6).alias("oil_million_sm3"),
        (pl.col("water_injection_volume").sum() / 1e6).alias("water_injected_million_sm3"),
    )
    .sort("oil_million_sm3", descending=True)
    .collect()
)"""


def _volve_wells(rows: Rows) -> dict[str, Any]:
    wells = [str(r[0]) for r in rows]
    oil = [float(r[1] or 0.0) for r in rows]
    injected = [float(r[2] or 0.0) for r in rows]
    total = sum(oil)
    top_two_share = (oil[0] + oil[1]) / total
    no_oil = [i for i, v in enumerate(oil) if v == 0]
    takeaway = (
        f"{wells[0]} and {wells[1]} produced {top_two_share:.0%} of the field's "
        f"{total:.1f} million Sm³ of oil."
    )
    if no_oil:
        takeaway += (
            f" {' and '.join(wells[i] for i in no_oil)} produced none and injected "
            f"{sum(injected[i] for i in no_oil):.1f} million Sm³ of water to "
            "hold up reservoir pressure."
        )
    return {
        "takeaway": takeaway,
        "chart": {
            "kind": "bars",
            "x": {"type": "category", "values": wells},
            "series": [
                {"name": "Oil produced", "unit": "million Sm³", "tone": "oil",
                 "min": 0, "max": _nice_max(max(oil)), "values": [_r(v, 2) for v in oil]},
                {"name": "Water injected", "unit": "million Sm³", "tone": "water",
                 "min": 0, "max": _nice_max(max(injected)),
                 "values": [_r(v, 2) for v in injected]},
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
            f"Totals across all years. {basins[0]} and {basins[1]} produced "
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


def _w3_hydrate(rows: Rows) -> dict[str, Any]:
    rows = [r for r in rows if r[1] is not None]
    pressure = [r[1] for r in rows]
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
        },
    }


GLANCES: list[Glance] = [
    Glance("volve", "field-rates", "A field's whole life in one query",
           VOLVE_FIELD_SQL, _volve_field, polars=VOLVE_FIELD_POLARS),
    Glance("volve", "cumulative-oil", "Most of the oil came from two wells",
           VOLVE_WELLS_SQL, _volve_wells, polars=VOLVE_WELLS_POLARS),
    Glance("argentina", "oil-by-resource", "Shale took over Argentina's oil",
           ARGENTINA_RESOURCE_SQL, _argentina_resource),
    Glance("argentina", "basins", "Two basins for oil, a third for gas",
           ARGENTINA_BASIN_SQL, _argentina_basin),
    Glance("argentina", "producing-wells", "More oil from fewer wells",
           ARGENTINA_ACTIVE_SQL, _argentina_active),
    Glance("force_2020", "gamma-ray", "A well log, top to bottom",
           FORCE_GR_SQL, _force_gr),
    Glance("petrobras_3w", "hydrate-pressure", "An anomaly as the sensors saw it",
           W3_HYDRATE_SQL, _w3_hydrate),
]


# --------------------------------------------------------------------------
# Dataset facts: the catalogue's "Covers" column
# --------------------------------------------------------------------------

VOLVE_FACTS_SQL = """\
SELECT (SELECT count(*) FROM '{base}/volve/wells.parquet'),
       year(min(date)), year(max(date))
FROM '{base}/volve/daily_production.parquet';"""

ARGENTINA_FACTS_SQL = ARGENTINA_MANIFEST_SQL + """
SELECT (SELECT count(*) FROM '{base}/argentina/wells.parquet'),
       min(anio), max(anio)
FROM read_parquet(getvariable('monthly_production'), hive_partitioning = true);"""

FORCE_FACTS_SQL = """\
SET VARIABLE wells = (
    SELECT list('{base}/force_2020/wells/' || path)
    FROM read_json('{base}/force_2020/wells/_files.json') AS manifest(path)
);
SELECT count(DISTINCT WELL) FROM read_parquet(getvariable('wells'));"""

W3_FACTS_SQL = """\
SELECT (SELECT count(*) FROM '{base}/petrobras_3w/instances.parquet'),
       count(*), year(min(first_ts)), year(max(last_ts))
FROM '{base}/petrobras_3w/wells.parquet';"""

FACTS: list[Facts] = [
    Facts("volve", VOLVE_FACTS_SQL,
          lambda r: f"{r[0]:,} wells, {r[1]}–{r[2]}"),
    Facts("force_2020", FORCE_FACTS_SQL,
          lambda r: f"{r[0]:,} wells"),
    Facts("argentina", ARGENTINA_FACTS_SQL,
          lambda r: f"{r[0]:,} wells, {r[1]}–{r[2]}"),
    Facts("petrobras_3w", W3_FACTS_SQL,
          lambda r: f"{r[0]:,} Instances, {r[1]:,} real wells, {r[2]}–{r[3]}"),
]

DATASETS = [f.dataset for f in FACTS]


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


def _query(sql: str, dataset: str) -> Rows:
    return duckdb.connect().execute(sql.format(base=_base(dataset))).fetchall()


def published_bytes(dataset: str) -> int:
    """Total size of a Dataset's parquet files as published on Hugging Face.

    For a Dataset whose tree is not on disk (Petrobras 3W is rebuilt in CI).
    The Hub API lists 1,000 entries a page and links the next one.
    """
    total = 0
    url: str | None = f"{PUBLIC_TREE}/{dataset}?recursive=true"
    while url:
        with urllib.request.urlopen(url) as response:
            entries = json.load(response)
            link = response.headers.get("Link") or ""
        total += sum(
            e["size"] for e in entries
            if e["type"] == "file" and e["path"].endswith(".parquet")
        )
        found = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = found.group(1) if found else None
    return total


def run_glance(glance: Glance) -> dict[str, Any]:
    rows = _query(glance.sql, glance.dataset)
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


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1) + "\n"


def build(dataset: str) -> dict[str, str]:
    """Everything the command writes for one Dataset: file name -> JSON text."""
    out: dict[str, str] = {}
    glances = [run_glance(g) for g in GLANCES if g.dataset == dataset]
    if glances:
        out["glances.json"] = _dump(glances)
    files = list_files(dataset)
    if files is not None:
        out["files.json"] = _dump(files)
    facts = next(f for f in FACTS if f.dataset == dataset)
    out["facts.json"] = _dump({
        "covers": facts.covers(_query(facts.sql, dataset)[0]),
        "bytes": (sum(t["bytes"] for t in files) if files is not None
                  else published_bytes(dataset)),
    })
    return out


def write(dataset: str, out_root: Path = OUT_ROOT) -> None:
    """Regenerate one Dataset's committed output. Each export pipeline's last step."""
    for name, text in build(dataset).items():
        path = out_root / dataset / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path}")


def stale(dataset: str, out_root: Path = OUT_ROOT) -> list[str]:
    """Names of the committed files that differ from what the command produces now."""
    return [
        name for name, text in build(dataset).items()
        if not (out_root / dataset / name).is_file()
        or (out_root / dataset / name).read_text() != text
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.site.glances")
    parser.add_argument("datasets", nargs="*", metavar="dataset",
                        help=f"any of {', '.join(DATASETS)}; default all")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 if committed output is stale")
    args = parser.parse_args(argv)
    unknown = sorted(set(args.datasets) - set(DATASETS))
    if unknown:
        parser.error(f"unknown dataset: {', '.join(unknown)}")
    datasets = args.datasets or DATASETS

    if not args.check:
        for dataset in datasets:
            write(dataset)
        return 0

    failed = False
    for dataset in datasets:
        if not on_disk(dataset):
            print(f"skip {dataset}: parquet/{dataset} is not on disk, nothing to compare")
            continue
        names = stale(dataset)
        if names:
            failed = True
            print(f"stale {dataset}: {', '.join(names)}; "
                  f"run `uv run -m scripts.site.glances {dataset}`")
        else:
            print(f"ok {dataset}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
