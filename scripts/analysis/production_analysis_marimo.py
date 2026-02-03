import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    from scripts.analysis.utils import (
        query_daily_field_totals,
        query_cumulative_oil_by_well,
        query_field_cumulative_totals,
        create_production_visualizations
    )
    return (
        create_production_visualizations,
        duckdb,
        mo,
        query_cumulative_oil_by_well,
        query_daily_field_totals,
        query_field_cumulative_totals,
    )


@app.cell
def _():
    DATABASE_PATH = "database/volve.db"
    DAILY_PRODUCTION_TABLE = "daily_production"
    WELLS_TABLE = "wells"
    OUTPUT_PATH = "scripts/analysis/output/production_analysis_local.png"
    return DAILY_PRODUCTION_TABLE, DATABASE_PATH, OUTPUT_PATH, WELLS_TABLE


@app.cell
def _(mo):
    mo.md(r"""
    # Volve Production Data Analysis
    """)
    return


@app.cell
def _(DATABASE_PATH, duckdb):
    conn = duckdb.connect(DATABASE_PATH, read_only=True)
    return (conn,)


@app.cell
def _(
    DAILY_PRODUCTION_TABLE,
    WELLS_TABLE,
    conn,
    query_cumulative_oil_by_well,
    query_daily_field_totals,
    query_field_cumulative_totals,
):
    # Query data
    daily_totals = query_daily_field_totals(conn, DAILY_PRODUCTION_TABLE)
    well_cumulatives = query_cumulative_oil_by_well(
        conn, DAILY_PRODUCTION_TABLE, WELLS_TABLE
    )
    field_totals = query_field_cumulative_totals(conn, DAILY_PRODUCTION_TABLE)
    return daily_totals, field_totals, well_cumulatives


@app.cell
def _(daily_totals, field_totals, mo, well_cumulatives):
    mo.md(f"""
    ## Data Summary

    - **Daily Records:** {len(daily_totals)} days of production data
    - **Wells:** {len(well_cumulatives)} wells
    - **Field Cumulative Oil:** {field_totals['oil']:,.0f} sm3
    - **Field Cumulative Gas:** {field_totals['gas']:,.0f} sm3
    - **Field Cumulative Water:** {field_totals['water']:,.0f} sm3
    """)
    return


@app.cell
def _(
    OUTPUT_PATH,
    create_production_visualizations,
    daily_totals,
    field_totals,
    well_cumulatives,
):
    # Create visualizations
    create_production_visualizations(
        daily_totals=daily_totals,
        well_cumulatives=well_cumulatives,
        field_totals=field_totals,
        output_path=OUTPUT_PATH,
        title_suffix="Marimo"
    )
    return


@app.cell
def _():
    # Note: In a reactive notebook, closing the connection might be tricky if you 
    # want to re-run queries without re-opening. 
    # For this demonstration, we'll keep it open or let it close when the process ends.
    # conn.close()
    return


if __name__ == "__main__":
    app.run()
