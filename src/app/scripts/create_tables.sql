CREATE SCHEMA IF NOT EXISTS Banking;
SET search_path TO Banking, public;

CREATE TABLE IF NOT EXISTS Banking.locations (
	h3_09 varchar(16) PRIMARY KEY NOT NULL,
	type varchar NOT NULL,
	lat real,
	lon real
) TABLESPACE pg_default;

CREATE TABLE IF NOT EXISTS Banking.transactions (
	transaction_pk bigserial PRIMARY KEY NOT NULL,
	h3_09 varchar(16) NOT NULL,
	customer_id bigint NOT NULL,
	datetime_id varchar NOT NULL,
	count smallint NOT NULL,
	sum real NOT NULL,
	avg real NOT NULL,
	min real NOT NULL,
	max real NOT NULL,
	std real NOT NULL,
	count_distinct smallint NOT NULL,
	mcc_code int4range NOT NULL,
	CONSTRAINT fk_locations_h3_09_to_transactions_h3_09 FOREIGN KEY (h3_09) REFERENCES Banking.locations (h3_09)
) TABLESPACE pg_default;

CREATE TABLE IF NOT EXISTS Banking.cash_withdrawals (
	h3_09 varchar(16) NOT NULL,
	customer_id bigint NOT NULL,
	CONSTRAINT withdrawal PRIMARY KEY (h3_09, customer_id),
	CONSTRAINT fk_locations_h3_09_to_cash_withdrawals_h3_09 FOREIGN KEY (h3_09) REFERENCES Banking.locations (h3_09)
) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_transaction
 ON ONLY Banking.transactions USING BTREE (customer_id ASC, h3_09 ASC, datetime_id ASC) 
 TABLESPACE pg_default;