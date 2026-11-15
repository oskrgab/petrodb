# Volve logs: one table per Log type, each with a measured physical layout

**Status:** accepted

## Context

The Volve log release groups its files by **Log type** (petrophysical interpretation, composite, formation pressure and others) for each **Wellbore**. The published tables are read by DuckDB and DuckDB-WASM over `httpfs`, and the consumer that must feel fast is a log viewer in a browser. It asks two things: a few **Curves** for one Wellbore, and a few Curves for every Wellbore at once. Building a machine-learning dataset is a full scan and can afford to be slower.

Over HTTP the cost of a query is mostly its number of requests. DuckDB fetches the footer, then one range per column chunk (a column in a row group), merging neighbours that are close together. DuckDB-WASM runs on one thread and sends its requests one after another, so each request adds a full round trip.

FORCE 2020 publishes one file per well. The natural choices for Volve were to copy that, or to write one row group per Wellbore so that statistics prune the others.

## Decision

Each Log type is published as one table covering every Wellbore. Each table declares its own key and its own physical layout, chosen by measuring the two viewer queries before the table ships.

The petrophysical interpretation table is one wide Parquet file with a single row group: one row per depth sample, one column per Curve, sorted by Wellbore then depth, with the key columns first and the Curves ordered by how many Wellbores carry them. Samples keep their source depths; nothing is resampled.

A **Curve catalog** table lists which Curves each recording carries and over what depth range, because the Parquet footer cannot answer that.

## Measurements

The table measured had 18 Wellbores, 502,973 rows and 39 Curve columns. The client was limited to one thread with 80 ms added to every request, to stand in for a browser.

| Layout | Three Curves, one Wellbore | Three Curves, every Wellbore |
|---|---|---|
| One file, one row group (chosen) | 9 requests, 5.1 MB, 0.9 s | 5 requests, 3.6 MB, 0.7 s |
| One file, one row group per Wellbore | 9 requests, 0.7 MB, 0.9 s | 58 requests, 6.9 MB, 5.1 s |
| One file, five row groups | 18 requests, 2.0 MB, 1.7 s | 21 requests, 3.0 MB, 2.2 s |
| Long table (one row per sample and Curve), sorted by Curve | 11 requests, 8.3 MB, 1.2 s | 5 requests, 6.0 MB, 0.8 s |
| One file per Wellbore | 26 requests, 0.9 MB, 3.7 s | 75 requests, 7.1 MB, 7.8 s |

With the chosen layout, switching to another Wellbore after the first query costs no further requests, because the columns are already in memory. A depth filter saves almost nothing in any layout. Ordering the columns with the common Curves first cuts the single-Wellbore query from 9 requests to 5 on DuckDB 1.5.2, and changes nothing on the DuckDB 1.4.3 inside DuckDB-WASM 1.32.0. Storing Curves as 32-bit floats saves about 8% of the bytes and no requests.

## Considered alternatives

- **One file per Wellbore**, as FORCE 2020 does. Rejected: the slowest layout for both queries, since every file costs its own footer round trips.
- **One row group per Wellbore.** Rejected: it downloads the fewest bytes for one Wellbore but needs 58 requests for the multi-Wellbore query, and requests cost more than bytes at this size.
- **A long table.** Rejected: comparable request counts, but more bytes, and every consumer has to pivot before plotting.
- **One table for all Log types.** Rejected: Log types differ in key and in shape. Interpretation Curves share one depth grid per Wellbore; pressure tests are points; composite logs span several runs.

## Consequences

- The single-row-group layout suits a table of this size (about 15 MB). A much larger Log type must be measured again and may choose differently; that is why the layout belongs to the table and not to the Dataset.
- A reader pays about 5 MB on the first query whichever Wellbore it asks for. That is the price of the low request count.
- Each new Log type table repeats the measurement of the two viewer queries before it ships.
- FORCE 2020's one-file-per-well layout is the slowest pattern measured here, and is worth revisiting.
