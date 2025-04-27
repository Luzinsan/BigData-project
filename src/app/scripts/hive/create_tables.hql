CREATE DATABASE IF NOT EXISTS team3_projectdb 
LOCATION '/user/team3/project/hive/warehouse';

USE team3_projectdb;

-- 1. Таблица locations
CREATE EXTERNAL TABLE IF NOT EXISTS locations (
    h3_09 STRING,
    lat FLOAT,
    lon FLOAT
)
STORED AS TEXTFILE
LOCATION '/user/team3/project/warehouse/locations';

-- 2. Таблица transactions
CREATE EXTERNAL TABLE IF NOT EXISTS transactions (
    transaction_pk BIGINT,
    h3_09 STRING,
    customer_id BIGINT,
    datetime_id STRING,
    count SMALLINT,
    sum FLOAT,
    avg FLOAT,
    min FLOAT,
    max FLOAT,
    std FLOAT,
    count_distinct SMALLINT,
    mcc_code SMALLINT
)
STORED AS TEXTFILE
LOCATION '/user/team3/project/warehouse/transactions';

-- 3. Таблица cash_withdrawals
CREATE EXTERNAL TABLE IF NOT EXISTS cash_withdrawals (
    h3_09 STRING,
    customer_id BIGINT
)
STORED AS TEXTFILE
LOCATION '/user/team3/project/warehouse/cash_withdrawals';

-- 4. Таблица moscow
CREATE EXTERNAL TABLE IF NOT EXISTS moscow (
    id STRING,
    tags STRING,
    lat FLOAT,
    lon FLOAT,
    h3_09 STRING,
    h3_09_center STRING
)
STORED AS TEXTFILE
LOCATION '/user/team3/project/warehouse/moscow';