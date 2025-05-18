DROP DATABASE IF EXISTS team3_projectdb CASCADE;
CREATE DATABASE team3_projectdb LOCATION 'project/hive/warehouse';
USE team3_projectdb;

SET hive.exec.dynamic.partition.mode=nonstrict;

---------------- Locations ----------------
CREATE EXTERNAL TABLE locations_parquet (
    h3_09 STRING,
    lat FLOAT,
    lon FLOAT
)
STORED AS PARQUET
LOCATION 'project/warehouse/locations';

CREATE EXTERNAL TABLE locations (
    h3_09 STRING,
    lat FLOAT,
    lon FLOAT
)
STORED AS ORC
LOCATION 'project/hive/warehouse/locations';

INSERT OVERWRITE TABLE locations
SELECT * FROM locations_parquet;

DROP TABLE locations_parquet;

DESCRIBE FORMATTED locations;

SELECT * FROM locations LIMIT 5;

---------------- Transactions ----------------
CREATE EXTERNAL TABLE transactions_parquet (
    transaction_pk BIGINT,
    customer_id BIGINT,
    datetime_id SMALLINT,
    count SMALLINT,
    sum FLOAT,
    avg FLOAT,
    min FLOAT,
    max FLOAT,
    std FLOAT,
    count_distinct SMALLINT,
    mcc_code SMALLINT,
    h3_09 STRING
)
STORED AS PARQUET
LOCATION 'project/warehouse/transactions';

CREATE EXTERNAL TABLE transactions (
    transaction_pk BIGINT,
    customer_id BIGINT,
    count SMALLINT,
    sum FLOAT,
    avg FLOAT,
    min FLOAT,
    max FLOAT,
    std FLOAT,
    count_distinct SMALLINT,
    h3_09 STRING
)
PARTITIONED BY (datetime_id SMALLINT, mcc_code SMALLINT)
STORED AS ORC
LOCATION 'project/hive/warehouse/transactions';

INSERT OVERWRITE TABLE transactions
SELECT 
    transaction_pk,
    customer_id,
    count,
    sum,
    avg,
    min,
    max,
    std,
    count_distinct,
    h3_09,
    datetime_id,
    mcc_code
FROM transactions_parquet;

DROP TABLE transactions_parquet;

DESCRIBE FORMATTED transactions;

SELECT * FROM transactions LIMIT 5;

---------------- Cash Withdrawals ----------------
CREATE EXTERNAL TABLE cash_withdrawals_parquet (
    customer_id BIGINT,
    h3_09 STRING
)
STORED AS PARQUET
LOCATION 'project/warehouse/cash_withdrawals';

CREATE EXTERNAL TABLE cash_withdrawals (
    customer_id BIGINT,
    h3_09 STRING
)
CLUSTERED BY (customer_id) INTO 50 BUCKETS
STORED AS ORC
LOCATION 'project/hive/warehouse/cash_withdrawals';

INSERT OVERWRITE TABLE cash_withdrawals
SELECT customer_id, h3_09
FROM cash_withdrawals_parquet;

DROP TABLE cash_withdrawals_parquet;

DESCRIBE FORMATTED cash_withdrawals;

SELECT * FROM cash_withdrawals LIMIT 5;

---------------- Moscow ----------------
CREATE EXTERNAL TABLE moscow_parquet (
    id STRING,
    tags STRING,
    lat FLOAT,
    lon FLOAT,
    h3_09 STRING,
    h3_09_center STRING
)
STORED AS PARQUET
LOCATION 'project/warehouse/moscow';

CREATE EXTERNAL TABLE moscow (
    id STRING,
    tags STRING,
    lat FLOAT,
    lon FLOAT,
    h3_09 STRING,
    h3_09_center STRING
)
STORED AS ORC
LOCATION 'project/hive/warehouse/moscow';

INSERT OVERWRITE TABLE moscow
SELECT * FROM moscow_parquet;

DROP TABLE moscow_parquet;

DESCRIBE FORMATTED moscow;

SELECT * FROM moscow LIMIT 5;

SHOW TABLES;