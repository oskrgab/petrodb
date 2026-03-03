# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb",
#     "polars",
#     "matplotlib",
#     "numpy",
#     "pyarrow",
# ]
# ///
"""
FORCE 2020 Well Log Plot

Fetches well data from petrodb remote parquet files and produces a 3-track
vertical well log plot: GR, Density/Neutron, and Deep Resistivity.

Usage:
    uv run plot_well_logs.py <well_name> [--top TOP] [--base BASE]

Example:
    uv run plot_well_logs.py 15-9-13
    uv run plot_well_logs.py 15-9-13 --top 1000 --base 2000
"""

import argparse
import sys
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import polars as pl

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://dev-petrodb.ocortez.com/force_2020/wells"
COLUMNS = ["DEPTH_MD", "GR", "RHOB", "NPHI", "RDEP"]

# Track scales
GR_MIN, GR_MAX = 0, 150
RHOB_MIN, RHOB_MAX = 1.95, 2.95
NPHI_MIN, NPHI_MAX = 0.45, -0.15  # reversed: high porosity on left
RDEP_MIN, RDEP_MAX = 0.2, 200

OUTPUT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_well_data(
    well_name: str, top: float | None = None, base: float | None = None
) -> pl.DataFrame:
    url = f"{BASE_URL}/{well_name}.parquet"
    cols = ", ".join(COLUMNS)
    where = ""
    if top is not None or base is not None:
        clauses = []
        if top is not None:
            clauses.append(f"DEPTH_MD >= {top}")
        if base is not None:
            clauses.append(f"DEPTH_MD <= {base}")
        where = " WHERE " + " AND ".join(clauses)

    query = f"SELECT {cols} FROM read_parquet('{url}'){where} ORDER BY DEPTH_MD"
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    result = con.execute(query).pl()
    con.close()
    return result


# ---------------------------------------------------------------------------
# Track plotting helpers
# ---------------------------------------------------------------------------
def plot_gr_track(ax, depth, gr):
    """GR track with segment-by-segment yellow-to-green fill."""
    ax.set_xlim(GR_MIN, GR_MAX)
    ax.set_xlabel("GR (API)", fontsize=9)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.grid(True, alpha=0.3)
    ax.set_ylabel("Depth (m MD)")

    # Segment fill coloured by GR value
    cmap = mcolors.LinearSegmentedColormap.from_list("gr", ["#FFD700", "#228B22"])
    gr_clipped = np.clip(gr, GR_MIN, GR_MAX)

    for i in range(len(depth) - 1):
        avg_gr = (gr_clipped[i] + gr_clipped[i + 1]) / 2
        colour = cmap(avg_gr / GR_MAX)
        ax.fill_betweenx(
            depth[i : i + 2],
            0,
            gr_clipped[i : i + 2],
            color=colour,
            linewidth=0,
        )

    ax.plot(gr, depth, color="black", linewidth=0.5)


def plot_density_neutron_track(ax, depth, rhob, nphi):
    """Density + Neutron with crossover fill."""
    ax.set_xlim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()

    # Normalize both curves to 0-1 on their respective scales
    rhob_norm = (rhob - RHOB_MIN) / (RHOB_MAX - RHOB_MIN)
    nphi_norm = (nphi - NPHI_MIN) / (NPHI_MAX - NPHI_MIN)

    # Custom tick labels showing both scales
    ticks = np.linspace(0, 1, 5)
    rhob_labels = np.linspace(RHOB_MIN, RHOB_MAX, 5)
    nphi_labels = np.linspace(NPHI_MIN, NPHI_MAX, 5)

    ax2 = ax.twiny()
    ax.set_xlim(0, 1)
    ax2.set_xlim(0, 1)

    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{v:.2f}" for v in rhob_labels], fontsize=7, color="red")
    ax.set_xlabel("RHOB (g/cc)", fontsize=9, color="red")
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()

    ax2.set_xticks(ticks)
    ax2.set_xticklabels([f"{v:.2f}" for v in nphi_labels], fontsize=7, color="blue")
    ax2.set_xlabel("NPHI (v/v)", fontsize=9, color="blue")

    # Crossover fill
    ax.fill_betweenx(
        depth,
        rhob_norm,
        nphi_norm,
        where=nphi_norm > rhob_norm,
        color="#FFD700",
        alpha=0.5,
        label="Sand crossover",
    )
    ax.fill_betweenx(
        depth,
        rhob_norm,
        nphi_norm,
        where=rhob_norm >= nphi_norm,
        color="#8B4513",
        alpha=0.5,
        label="Shale",
    )

    ax.plot(rhob_norm, depth, color="red", linewidth=0.8, label="RHOB")
    ax.plot(nphi_norm, depth, color="blue", linewidth=0.8, label="NPHI")
    ax.legend(loc="lower left", fontsize=7)


def plot_resistivity_track(ax, depth, rdep):
    """Deep resistivity on logarithmic scale."""
    ax.set_xscale("log")
    ax.set_xlim(RDEP_MIN, RDEP_MAX)
    ax.set_xlabel("RDEP (ohm.m)", fontsize=9)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.grid(True, which="both", alpha=0.3)
    ax.plot(rdep, depth, color="black", linewidth=0.8)


# ---------------------------------------------------------------------------
# Main plot assembly
# ---------------------------------------------------------------------------
def create_well_log_plot(
    df: pl.DataFrame, well_name: str, top: float | None, base: float | None
) -> Path:
    depth = df["DEPTH_MD"].to_numpy()
    gr = df["GR"].to_numpy()
    rhob = df["RHOB"].to_numpy()
    nphi = df["NPHI"].to_numpy()
    rdep = df["RDEP"].to_numpy()

    fig, axes = plt.subplots(1, 3, figsize=(10, 16), sharey=True)
    fig.suptitle(f"Well: {well_name}", fontsize=14, fontweight="bold", y=0.98)

    # Invert depth axis (shared)
    axes[0].invert_yaxis()

    plot_gr_track(axes[0], depth, gr)
    plot_density_neutron_track(axes[1], depth, rhob, nphi)
    plot_resistivity_track(axes[2], depth, rdep)

    # Remove y-tick labels on tracks 2 and 3
    axes[1].set_yticklabels([])
    axes[2].set_yticklabels([])

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    out_path = OUTPUT_DIR / f"{well_name}_logs.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Plot FORCE 2020 well logs")
    parser.add_argument("well_name", help="Well name, e.g. 15-9-13")
    parser.add_argument("--top", type=float, default=None, help="Top depth (m MD)")
    parser.add_argument("--base", type=float, default=None, help="Base depth (m MD)")
    args = parser.parse_args()

    print(f"Fetching data for well {args.well_name}...")
    df = fetch_well_data(args.well_name, args.top, args.base)
    print(f"  Rows: {len(df)}, Depth range: {df['DEPTH_MD'].min():.1f} - {df['DEPTH_MD'].max():.1f} m")

    # Drop rows where all log columns are null
    log_cols = ["GR", "RHOB", "NPHI", "RDEP"]
    df = df.filter(~pl.all_horizontal(pl.col(c).is_null() for c in log_cols))
    print(f"  Rows after filtering nulls: {len(df)}")

    out = create_well_log_plot(df, args.well_name, args.top, args.base)
    print(f"Plot saved to {out}")


if __name__ == "__main__":
    main()
