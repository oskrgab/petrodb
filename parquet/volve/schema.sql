-- Volve Database Schema
-- Auto-generated schema export using SQLAlchemy
-- This file contains DDL statements to recreate the database structure


CREATE TABLE daily_production (
	date DATE NOT NULL, 
	npd_wellbore_code INTEGER NOT NULL, 
	on_stream_hours FLOAT, 
	avg_downhole_pressure FLOAT, 
	avg_dp_tubing FLOAT, 
	avg_annulus_pressure FLOAT, 
	avg_wellhead_pressure FLOAT, 
	avg_downhole_temperature FLOAT, 
	avg_wellhead_temperature FLOAT, 
	avg_choke_size_percent FLOAT, 
	avg_choke_unit TEXT, 
	dp_choke_size FLOAT, 
	oil_volume FLOAT, 
	gas_volume FLOAT, 
	water_volume FLOAT, 
	water_injection_volume FLOAT, 
	flow_kind TEXT, 
	well_type TEXT, 
	PRIMARY KEY (date, npd_wellbore_code), 
	FOREIGN KEY(npd_wellbore_code) REFERENCES wells (npd_wellbore_code)
)

;


CREATE TABLE monthly_production (
	date DATE NOT NULL, 
	npd_wellbore_code INTEGER NOT NULL, 
	on_stream_hours FLOAT, 
	oil_volume_sm3 FLOAT, 
	gas_volume_sm3 FLOAT, 
	water_volume_sm3 FLOAT, 
	gas_injection_sm3 FLOAT, 
	water_injection_sm3 FLOAT, 
	PRIMARY KEY (date, npd_wellbore_code), 
	FOREIGN KEY(npd_wellbore_code) REFERENCES wells (npd_wellbore_code)
)

;


CREATE TABLE petrophysical_interpretation (
	npd_wellbore_code INTEGER NOT NULL, 
	source_wellbore TEXT NOT NULL, 
	depth_md DOUBLE NOT NULL, 
	"BVW" DOUBLE, 
	"COAL_FLAG" DOUBLE, 
	"GR" DOUBLE, 
	"KLOGH" DOUBLE, 
	"NPHI" DOUBLE, 
	"PHIF" DOUBLE, 
	"RHOB" DOUBLE, 
	"RT" DOUBLE, 
	"SAND_FLAG" DOUBLE, 
	"SW" DOUBLE, 
	"VSH" DOUBLE, 
	"ABDCQF01" DOUBLE, 
	"ABDCQF02" DOUBLE, 
	"ABDCQF03" DOUBLE, 
	"ABDCQF04" DOUBLE, 
	"BS" DOUBLE, 
	"CALI" DOUBLE, 
	"DRHO" DOUBLE, 
	"PEF" DOUBLE, 
	"RACEHM" DOUBLE, 
	"RACELM" DOUBLE, 
	"RD" DOUBLE, 
	"ROP" DOUBLE, 
	"RPCEHM" DOUBLE, 
	"RPCELM" DOUBLE, 
	"RM" DOUBLE, 
	"DT" DOUBLE, 
	"CARB_FLAG" DOUBLE, 
	"VCARB" DOUBLE, 
	"DTS" DOUBLE, 
	"NBGRCFM" DOUBLE, 
	"BADDATA_FLAG" DOUBLE, 
	"ROP5_RM" DOUBLE, 
	"RS" DOUBLE, 
	PRIMARY KEY (source_wellbore, depth_md), 
	FOREIGN KEY(npd_wellbore_code) REFERENCES wells (npd_wellbore_code)
)

;


CREATE TABLE wells (
	npd_wellbore_code INTEGER NOT NULL, 
	wellbore_code TEXT, 
	wellbore_name TEXT NOT NULL, 
	npd_field_code INTEGER NOT NULL, 
	npd_field_name TEXT NOT NULL, 
	npd_facility_code INTEGER, 
	npd_facility_name TEXT, 
	wellbore_type TEXT NOT NULL, 
	purpose TEXT NOT NULL, 
	content TEXT, 
	completion_year INTEGER, 
	parent_npd_wellbore_code INTEGER, 
	has_production BOOLEAN NOT NULL, 
	PRIMARY KEY (npd_wellbore_code), 
	FOREIGN KEY(parent_npd_wellbore_code) REFERENCES wells (npd_wellbore_code)
)

;

CREATE INDEX ix_daily_date ON daily_production (date);

CREATE INDEX ix_daily_wellbore ON daily_production (npd_wellbore_code);

CREATE INDEX ix_monthly_date ON monthly_production (date);

CREATE INDEX ix_monthly_wellbore ON monthly_production (npd_wellbore_code);