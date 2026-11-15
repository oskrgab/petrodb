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
        "has no sample. Each Curve has one documented unit, stated with the "
        "column: the source files spell it several ways, and the values are kept as "
        "the source gives them, never converted. Samples are at the source "
        "depths; nothing is resampled. A source depth is kept only where a "
        "Curve other than the lithology and bad-data flags has a value: some "
        "files pad the wellbore with samples whose only value is a flag, and "
        "those are dropped. The file is a single row group, sorted "
        "by `npd_wellbore_code`, `source_wellbore` and `depth_md`; the key "
        "columns come first, then the Curves in descending order of how many "
        "wellbores carry them, ties by mnemonic, so the most common Curves "
        "come first. Built from the raw log files; the Parquet is not in git."
    ),
    "log_curves": (
        "The Curve catalog: one row per log table, Wellbore or Technical "
        "sidetrack, and Curve that has data there. Read it first to learn "
        "which Curves each one has, over which depths, and which raw file each came from, before "
        "reading any samples. One row per `(table_name, source_wellbore, "
        "mnemonic)`; a Curve that is empty for a `source_wellbore` has no row. Its "
        "depth range and sample count are those of the table it describes. "
        "Built with the log tables from the raw log files; the Parquet is not "
        "in git."
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
        # every published column is described. Units are not repeated here:
        # each column's one unit comes from the unit table
        # (scripts/transform/volve_logs/units.py).
        "npd_wellbore_code": (
            "Wellbore the row belongs to. Joins to `wells`. For a Technical "
            "sidetrack, the code of its parent Wellbore."
        ),
        "source_wellbore": (
            "The operator's name for the logged wellbore, such as "
            "`15/9-F-1 A`, taken from the folder the source files sit in. "
            "Usually the name of the Wellbore in `npd_wellbore_code`. A "
            "Technical sidetrack, such as `15/9-F-11 T2`, is a re-drilled "
            "section the register does not count as a Wellbore: its rows "
            "carry the `npd_wellbore_code` of its parent Wellbore "
            "(`15/9-F-11`) and keep the Technical sidetrack's name here. The "
            "15/9-F-11 top-hole section is "
            "`15/9-F-11`: it has Input curves only, and it overlaps the "
            "depths of `15/9-F-11 T2` with different values. Filter on "
            "`npd_wellbore_code` for everything logged under a Wellbore, on "
            "`source_wellbore` for one of its sources."
        ),
        "depth_md": (
            "Measured depth along the wellbore, in metres, rounded to four "
            "decimals so that equality joins are stable. Source files that "
            "index depth in tenths of an inch or in millimetres are converted "
            "to metres before rounding. The depth reference "
            "is the one the source file uses; it is not normalised."
        ),
        "BVW": "Bulk volume of water: porosity times water saturation, as a fraction of rock volume.",
        "COAL_FLAG": "Lithology flag: 1 where the interpretation marks coal, 0 elsewhere.",
        "GR": "Natural gamma ray.",
        "KLOGH": "Horizontal permeability computed from the logs.",
        "NPHI": "Neutron porosity, as a fraction.",
        "RHOB": "Bulk density.",
        "RT": "True formation resistivity, as the interpreter selected it.",
        "SAND_FLAG": "Lithology flag: 1 where the interpretation marks sand, 0 elsewhere.",
        "VSH": "Shale volume, as a fraction.",
        "PHIF": "Final effective porosity from the interpretation, as a fraction.",
        "RD": "Deep resistivity.",
        "SW": "Water saturation from the interpretation, as a fraction of pore volume.",
        "DRHO": "Density correction applied to the bulk density.",
        "CALI": "Caliper: measured borehole diameter.",
        "CARB_FLAG": "Lithology flag: 1 where the interpretation marks carbonate, 0 elsewhere.",
        "DT": "Compressional sonic slowness.",
        "PEF": "Photoelectric factor.",
        "RS": "Shallow resistivity.",
        "ABDCQF01": "Bulk density from quadrant 1 of an azimuthal density measurement while drilling.",
        "ABDCQF02": "Bulk density from quadrant 2 of an azimuthal density measurement while drilling.",
        "ABDCQF03": "Bulk density from quadrant 3 of an azimuthal density measurement while drilling.",
        "ABDCQF04": "Bulk density from quadrant 4 of an azimuthal density measurement while drilling.",
        "BS": "Bit size: nominal diameter of the drilled hole.",
        "RACEHM": (
            "Propagation resistivity while drilling, from the attenuation of "
            "the high-frequency signal."
        ),
        "RACELM": (
            "Propagation resistivity while drilling, from the attenuation of "
            "the low-frequency signal."
        ),
        "ROP": "Rate of penetration while drilling.",
        "RPCEHM": (
            "Propagation resistivity while drilling, from the phase shift of "
            "the high-frequency signal."
        ),
        "RPCELM": (
            "Propagation resistivity while drilling, from the phase shift of "
            "the low-frequency signal."
        ),
        "RM": "Medium resistivity.",
        "DTS": "Shear sonic slowness.",
        "VCARB": "Volume of carbonate minerals (calcite, dolomite, siderite), as a fraction.",
        "DRHU": (
            "Density correction applied to `ROBU`, the bulk density from the "
            "top of the borehole, measured while drilling."
        ),
        "NBGRCFM": "Natural gamma ray measured near the bit while drilling.",
        "ROBU": (
            "Bulk density from the top of the borehole, measured while "
            "drilling by a rotating density tool."
        ),
        "ROBB": (
            "Bulk density from the bottom of the borehole, measured while "
            "drilling by a rotating density tool."
        ),
        "BADDATA_FLAG": "Interpreted flag: 1 where the interpreter judged the log data unreliable, 0 elsewhere.",
        "DRHB": (
            "Density correction applied to `ROBB`, the bulk density from the "
            "bottom of the borehole, measured while drilling."
        ),
        "PHID": "Porosity computed from the bulk density, as a fraction.",
        "ROP5_RM": (
            "Rate of penetration while drilling, a second recording. Its file "
            "leaves the unit unknown; its values lie in the range `ROP` has "
            "in the other wellbores, so it is documented in the same unit."
        ),
    },
    "log_curves": {
        "table_name": (
            "The log table the Curve is a column of, such as "
            "`petrophysical_interpretation`."
        ),
        "npd_wellbore_code": (
            "Wellbore the Curve was logged in. Joins to `wells`. For a "
            "Technical sidetrack, the code of its parent Wellbore."
        ),
        "source_wellbore": (
            "The operator's name for the logged Wellbore or Technical sidetrack, "
            "as in the log table's `source_wellbore`: a Wellbore, a Technical sidetrack "
            "such as `15/9-F-11 T2`, or the 15/9-F-11 top-hole section."
        ),
        "mnemonic": "The Curve's source mnemonic: the name of its column in the log table.",
        "curve_kind": (
            "`input` for an Input curve, a measurement the petrophysical "
            "interpretation took as input; `interpreted` for an Interpreted "
            "curve it computed. A Curve in both the input and the output file "
            "is an Input curve."
        ),
        "unit": "The one unit documented for the Curve's column, as the schema documents write it.",
        "source_unit": (
            "The unit as the source file spells it, such as `V/V` or "
            "`UNKNOWN`. The values are not converted: every spelling the build "
            "accepts means the documented unit."
        ),
        "first_depth_md": "Shallowest measured depth at which the Curve has a sample.",
        "last_depth_md": "Deepest measured depth at which the Curve has a sample.",
        "sample_count": "Number of depth samples at which the Curve has a value.",
        "source_file": (
            "Path of the file the Curve was read from, within the Raw repo "
            "`oskrgab/petrodb-raw-volve`. A Curve in both files of a pair "
            "names the input file."
        ),
    },
}
