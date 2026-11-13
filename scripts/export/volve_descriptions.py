"""What each table and column of the published Volve Dataset holds.

SQLite keeps no table or column comments, so ``export_schema`` cannot reflect
them. They live here, the single source of truth for the descriptions written
into ``parquet/volve/schema.json`` and ``schema.md``; the export fails if a
reflected column has no description or a description names a column that
does not exist.
"""

TABLE_DESCRIPTIONS = {
    "wells": (
        "One row per wellbore in the Volve field: its identifiers and the "
        "field and facility it belongs to. Seven wellbores, all produced "
        "through the Mærsk Inspirer production unit."
    ),
    "daily_production": (
        "Daily measurements per wellbore, from Equinor's daily production "
        "report: hours on stream, pressures, temperatures, choke opening and "
        "the volumes produced or injected. One row per `(date, "
        "npd_wellbore_code)`. Volumes are in standard cubic metres (Sm³)."
    ),
    "monthly_production": (
        "Monthly volumes per wellbore, from Equinor's monthly production "
        "report. One row per `(date, npd_wellbore_code)`, where `date` is the "
        "first day of the month. Volumes are in standard cubic metres (Sm³)."
    ),
}

# Plain-English descriptions for every published column. The source column in
# Equinor's "Volve production data.xlsx" is named where the mapping helps.
COLUMN_DESCRIPTIONS = {
    "wells": {
        "npd_wellbore_code": (
            "Wellbore identifier assigned by the Norwegian Offshore Directorate "
            "(formerly the Norwegian Petroleum Directorate, NPD). The key "
            "every production row joins on."
        ),
        "wellbore_code": (
            "Equinor's wellbore code, prefixed with the country (e.g. "
            "`NO 15/9-F-12 H`)."
        ),
        "wellbore_name": (
            "NPD wellbore name (e.g. `15/9-F-12`, a well in block 15/9). "
            "Use this to label wells."
        ),
        "npd_field_code": "NPD field identifier. The same value on every row: Volve.",
        "npd_field_name": "Field name: `VOLVE` on every row.",
        "npd_facility_code": "NPD identifier of the facility the wellbore produced through.",
        "npd_facility_name": (
            "Facility the wellbore produced through: the `MÆRSK INSPIRER` "
            "jack-up production unit on every row."
        ),
    },
    "daily_production": {
        "date": (
            "Production day (source `DATEPRD`). Stored in the Parquet file "
            "as a timestamp at midnight."
        ),
        "npd_wellbore_code": "Wellbore the row belongs to. Joins to `wells`.",
        "on_stream_hours": (
            "Hours the wellbore was producing or injecting that day "
            "(`ON_STREAM_HRS`). Up to 25 on the day the clocks go back."
        ),
        "avg_downhole_pressure": (
            "Average pressure at the downhole gauge over the day, in bar "
            "(`AVG_DOWNHOLE_PRESSURE`)."
        ),
        "avg_dp_tubing": (
            "Average pressure drop along the production tubing, from the "
            "downhole gauge to the wellhead, in bar (`AVG_DP_TUBING`)."
        ),
        "avg_annulus_pressure": (
            "Average pressure in the annulus between tubing and casing, in bar "
            "(`AVG_ANNULUS_PRESS`)."
        ),
        "avg_wellhead_pressure": "Average pressure at the wellhead, in bar (`AVG_WHP_P`).",
        "avg_downhole_temperature": (
            "Average temperature at the downhole gauge, in °C "
            "(`AVG_DOWNHOLE_TEMPERATURE`)."
        ),
        "avg_wellhead_temperature": "Average temperature at the wellhead, in °C (`AVG_WHT_P`).",
        "avg_choke_size_percent": (
            "Average production choke opening, as a percentage of fully open "
            "(`AVG_CHOKE_SIZE_P`)."
        ),
        "avg_choke_unit": (
            "Unit of `avg_choke_size_percent`: `%`, or NULL on injection rows "
            "(`AVG_CHOKE_UOM`)."
        ),
        "dp_choke_size": (
            "Pressure drop across the production choke, in bar "
            "(`DP_CHOKE_SIZE`)."
        ),
        "oil_volume": "Oil produced from the wellbore that day, in Sm³ (`BORE_OIL_VOL`).",
        "gas_volume": "Gas produced from the wellbore that day, in Sm³ (`BORE_GAS_VOL`).",
        "water_volume": (
            "Water produced from the wellbore that day, in Sm³ "
            "(`BORE_WAT_VOL`). A few rows are negative, kept as the source "
            "reports them."
        ),
        "water_injection_volume": (
            "Water injected into the wellbore that day, in Sm³ "
            "(`BORE_WI_VOL`). Filled on injection rows and on a handful of "
            "production rows."
        ),
        "flow_kind": "Direction of flow that day: `production` or `injection` (`FLOW_KIND`).",
        "well_type": (
            "Role of the wellbore that day: `OP` oil producer, `WI` water "
            "injector (`WELL_TYPE`). Can change over a wellbore's life."
        ),
    },
    "monthly_production": {
        "date": (
            "First day of the month the volumes cover, built from the source "
            "`Year` and `Month`. Stored in the Parquet file as a timestamp."
        ),
        "npd_wellbore_code": "Wellbore the row belongs to. Joins to `wells`.",
        "on_stream_hours": "Hours the wellbore was on stream in the month (`On Stream`).",
        "oil_volume_sm3": "Oil produced in the month, in Sm³ (`Oil`).",
        "gas_volume_sm3": "Gas produced in the month, in Sm³ (`Gas`).",
        "water_volume_sm3": "Water produced in the month, in Sm³ (`Water`).",
        "gas_injection_sm3": (
            "Gas injected in the month, in Sm³ (`GI`). Empty in every row of "
            "the source."
        ),
        "water_injection_sm3": "Water injected in the month, in Sm³ (`WI`).",
    },
}
