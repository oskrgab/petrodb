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


CREATE TABLE wells (
	npd_wellbore_code INTEGER NOT NULL, 
	wellbore_code TEXT NOT NULL, 
	wellbore_name TEXT NOT NULL, 
	npd_field_code INTEGER NOT NULL, 
	npd_field_name TEXT NOT NULL, 
	npd_facility_code INTEGER NOT NULL, 
	npd_facility_name TEXT NOT NULL, 
	PRIMARY KEY (npd_wellbore_code)
)

;

CREATE INDEX ix_daily_date ON daily_production (date);

CREATE INDEX ix_daily_wellbore ON daily_production (npd_wellbore_code);

CREATE INDEX ix_monthly_wellbore ON monthly_production (npd_wellbore_code);

CREATE INDEX ix_monthly_date ON monthly_production (date);