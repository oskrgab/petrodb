"""What each table and column of the published Volve Dataset holds.

SQLite keeps no table or column comments, so ``export_schema`` cannot reflect
them. They live here, the single source of truth for the descriptions written
into ``parquet/volve/schema.json`` and ``schema.md``; the export fails if a
reflected column has no description or a description names a column that
does not exist.
"""

TABLE_DESCRIPTIONS = {
    "wells": (
        "One row per wellbore the public wellbore register of the Norwegian "
        "Offshore Directorate assigns to the Volve field, drilled or not: its "
        "identifiers, the register's classification and the wellbore it was "
        "drilled from. The production columns come from Equinor's production "
        "report and are empty for a wellbore without production; "
        "`has_production` marks the wellbores that have production rows."
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
    "petrophysical_interpretation": (
        "Well-log Curves of Equinor's petrophysical interpretation, one row "
        "per depth sample of each logged wellbore: the Input curves the "
        "interpretation took (gamma ray, density, neutron, sonic, "
        "resistivity) and the Interpreted curves it computed (porosity, water "
        "saturation, shale volume, permeability, lithology flags) side by "
        "side. One row per `(source_wellbore, depth_md)`. Each Curve column "
        "is named with the source mnemonic and is empty where the wellbore "
        "has no sample. Samples are at the source depths; nothing is "
        "resampled. The file is a single row group, sorted by "
        "`npd_wellbore_code`, `source_wellbore` and `depth_md`; the key "
        "columns come first, then the Curves in descending order of how many "
        "wellbores carry them, ties by mnemonic, so the most common Curves "
        "come first. Built from the raw log files; the Parquet is not in git."
    ),
}

# Plain-English descriptions for every published column. The source column in
# Equinor's "Volve production data.xlsx" or in the register snapshot is named
# where the mapping helps.
COLUMN_DESCRIPTIONS = {
    "wells": {
        "npd_wellbore_code": (
            "Wellbore identifier assigned by the Norwegian Offshore Directorate "
            "(formerly the Norwegian Petroleum Directorate, NPD). The key "
            "every production row joins on."
        ),
        "wellbore_code": (
            "Equinor's wellbore code, prefixed with the country (e.g. "
            "`NO 15/9-F-12 H`), from the production report. Empty for a "
            "wellbore without production."
        ),
        "wellbore_name": (
            "NPD wellbore name (e.g. `15/9-F-12`, a well in block 15/9). "
            "Use this to label wells."
        ),
        "npd_field_code": "NPD field identifier. The same value on every row: Volve.",
        "npd_field_name": "Field name: `VOLVE` on every row.",
        "npd_facility_code": (
            "NPD identifier of the facility the wellbore produced through. "
            "Empty for a wellbore without production."
        ),
        "npd_facility_name": (
            "Facility the wellbore produced through: the `MÆRSK INSPIRER` "
            "jack-up production unit. Empty for a wellbore without production."
        ),
        "wellbore_type": (
            "Register well type: `DEVELOPMENT` for the wellbores drilled to "
            "develop the field, `EXPLORATION` for those drilled to find and "
            "appraise it (source `wlbWellType`)."
        ),
        "purpose": (
            "What the register says the wellbore was drilled for: "
            "`PRODUCTION`, `INJECTION` or `OBSERVATION` for a development "
            "wellbore, `WILDCAT` or `APPRAISAL` for an exploration one "
            "(source `wlbPurpose`)."
        ),
        "content": (
            "What the register says the wellbore found or carries, such as "
            "`OIL`, `WATER`, `SHOWS`, `DRY` or `NOT APPLICABLE` (source "
            "`wlbContent`). Empty for a wellbore that was never drilled."
        ),
        "completion_year": (
            "Year the wellbore was completed, from the register (source "
            "`wlbCompletionYear`). Empty for a wellbore that was never drilled."
        ),
        "parent_npd_wellbore_code": (
            "`npd_wellbore_code` of the wellbore this one was sidetracked or "
            "re-entered from, itself a row of this table (source "
            "`wlbDiskosWellboreParent`). Empty for a wellbore drilled from "
            "the surface."
        ),
        "has_production": (
            "True when the wellbore has rows in the production tables, "
            "`daily_production` and `monthly_production`; false otherwise."
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
    "petrophysical_interpretation": {
        # Key columns first; then one column per Curve, in the order the
        # pipeline writes them from the real raw files: by how many Wellbores
        # carry the Curve, most first, ties by mnemonic. The pre-publish
        # schema check fails if the written file differs from schema.json,
        # which takes this order. A Curve not listed here fails the build, so
        # every published column is described.
        "npd_wellbore_code": "Wellbore the row belongs to. Joins to `wells`.",
        "source_wellbore": (
            "The operator's name for the logged wellbore, such as "
            "`15/9-F-1 A`, taken from the folder the source files sit in."
        ),
        "depth_md": (
            "Measured depth along the wellbore, in metres, rounded to four "
            "decimals so that equality joins are stable. The depth reference "
            "is the one the source file uses; it is not normalised."
        ),
        "BVW": "Bulk volume of water: porosity times water saturation, as a fraction of rock volume (v/v).",
        "COAL_FLAG": "Lithology flag: 1 where the interpretation marks coal, 0 elsewhere.",
        "GR": "Natural gamma ray, in API units.",
        "KLOGH": "Horizontal permeability computed from the logs, in millidarcy (mD).",
        "NPHI": "Neutron porosity, as a fraction (v/v).",
        "PHIF": "Final effective porosity from the interpretation, as a fraction (v/v).",
        "RHOB": "Bulk density, in g/cm³.",
        "RT": "True formation resistivity, as the interpreter selected it, in ohm·m.",
        "SAND_FLAG": "Lithology flag: 1 where the interpretation marks sand, 0 elsewhere.",
        "SW": "Water saturation from the interpretation, as a fraction of pore volume (v/v).",
        "VSH": "Shale volume, as a fraction (v/v).",
        "ABDCQF01": "Bulk density from quadrant 1 of an azimuthal density measurement while drilling, in g/cm³.",
        "ABDCQF02": "Bulk density from quadrant 2 of an azimuthal density measurement while drilling, in g/cm³.",
        "ABDCQF03": "Bulk density from quadrant 3 of an azimuthal density measurement while drilling, in g/cm³.",
        "ABDCQF04": "Bulk density from quadrant 4 of an azimuthal density measurement while drilling, in g/cm³.",
        "BS": "Bit size: nominal diameter of the drilled hole, in inches.",
        "CALI": "Caliper: measured borehole diameter, in inches.",
        "DRHO": "Density correction applied to the bulk density, in g/cm³.",
        "PEF": "Photoelectric factor, in barns per electron.",
        "RACEHM": (
            "Propagation resistivity while drilling, from the attenuation of "
            "the high-frequency signal, in ohm·m."
        ),
        "RACELM": (
            "Propagation resistivity while drilling, from the attenuation of "
            "the low-frequency signal, in ohm·m."
        ),
        "RD": "Deep resistivity, in ohm·m.",
        "ROP": "Rate of penetration while drilling, in m/h.",
        "RPCEHM": (
            "Propagation resistivity while drilling, from the phase shift of "
            "the high-frequency signal, in ohm·m."
        ),
        "RPCELM": (
            "Propagation resistivity while drilling, from the phase shift of "
            "the low-frequency signal, in ohm·m."
        ),
        "RM": "Medium resistivity, in ohm·m.",
        "DT": "Compressional sonic slowness, in µs/ft.",
        "VCARB": "Volume of carbonate minerals (calcite, dolomite, siderite), as a fraction (v/v).",
        "CARB_FLAG": "Lithology flag: 1 where the interpretation marks carbonate, 0 elsewhere.",
        "DTS": "Shear sonic slowness, in µs/ft.",
        "NBGRCFM": "Natural gamma ray measured near the bit while drilling, in API units.",
        "BADDATA_FLAG": "Interpreted flag: 1 where the interpreter judged the log data unreliable, 0 elsewhere.",
        "ROP5_RM": "Rate of penetration while drilling, a second recording; the source gives no unit.",
        "RS": "Shallow resistivity, in ohm·m.",
    },
}
