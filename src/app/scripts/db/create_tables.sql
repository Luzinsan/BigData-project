START TRANSACTION;

DROP TABLE IF EXISTS locations CASCADE;
CREATE TABLE locations (
	h3_09 varchar(16) PRIMARY KEY NOT NULL,
	lat real,
	lon real
) TABLESPACE pg_default;

DROP TABLE IF EXISTS transactions CASCADE;
CREATE TABLE transactions (
	transaction_pk bigserial PRIMARY KEY NOT NULL,
	h3_09 varchar(16) NOT NULL,
	customer_id bigint NOT NULL,
	datetime_id smallint NOT NULL,
	count smallint NOT NULL,
	sum real NOT NULL,
	avg real NOT NULL,
	min real NOT NULL,
	max real NOT NULL,
	std real,
	count_distinct smallint NOT NULL,
	mcc_code smallint NOT NULL,
	CONSTRAINT fk_locations_h3_09_to_transactions_h3_09 FOREIGN KEY (h3_09) REFERENCES locations (h3_09)
) TABLESPACE pg_default;

DROP TABLE IF EXISTS cash_withdrawals CASCADE;
CREATE TABLE cash_withdrawals (
	h3_09 varchar(16) NOT NULL,
	customer_id bigint NOT NULL,
	CONSTRAINT withdrawal PRIMARY KEY (h3_09, customer_id),
	CONSTRAINT fk_locations_h3_09_to_cash_withdrawals_h3_09 FOREIGN KEY (h3_09) REFERENCES locations (h3_09)
) TABLESPACE pg_default;

DROP TABLE IF EXISTS moscow CASCADE;
CREATE TABLE moscow (
	id varchar(16) PRIMARY KEY NOT NULL,
	tags text,
	lat real,
	lon real,
	h3_09 varchar(16),
	h3_09_center varchar(16),
	CONSTRAINT fk_locations_h3_09_to_moscow_h3_09 FOREIGN KEY (h3_09_center) REFERENCES locations (h3_09)
) TABLESPACE pg_default;

DROP INDEX IF EXISTS idx_transaction;
CREATE INDEX idx_transaction
 ON ONLY transactions USING BTREE (customer_id ASC, h3_09 ASC, datetime_id ASC) 
 TABLESPACE pg_default;


COMMIT;