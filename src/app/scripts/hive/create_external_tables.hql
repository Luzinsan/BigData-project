CREATE DATABASE IF NOT EXISTS team3_projectdb 
LOCATION '/user/team3/project/hive/warehouse';

USE team3_projectdb;

-- 1. Таблица locations
CREATE EXTERNAL TABLE IF NOT EXISTS locations_avro
STORED AS AVRO
LOCATION '/user/team3/project/warehouse/locations'
TBLPROPERTIES ('avro.schema.url'='/user/team3/project/warehouse/avsc/locations.avsc');

-- 2. Таблица transactions
CREATE EXTERNAL TABLE IF NOT EXISTS transactions_avro
STORED AS AVRO
LOCATION '/user/team3/project/warehouse/transactions'
TBLPROPERTIES ('avro.schema.url'='/user/team3/project/warehouse/avsc/transactions.avsc');

-- 3. Партиционированная версия transactions по дате
CREATE EXTERNAL TABLE IF NOT EXISTS transactions_partitioned
PARTITIONED BY (transaction_date STRING)
STORED AS AVRO
LOCATION '/user/team3/project/warehouse/transactions_partitioned'
TBLPROPERTIES ('avro.schema.url'='/user/team3/project/warehouse/avsc/transactions.avsc');

-- Заполняем партиционированную таблицу
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

INSERT OVERWRITE TABLE transactions_partitioned PARTITION(transaction_date)
SELECT 
    t.*,
    substr(datetime_id, 1, 10) as transaction_date 
FROM transactions_avro t;

-- 4. Таблица cash_withdrawals с бакетированием
CREATE EXTERNAL TABLE IF NOT EXISTS cash_withdrawals_bucketed
CLUSTERED BY (customer_id) INTO 10 BUCKETS
STORED AS AVRO
LOCATION '/user/team3/project/warehouse/cash_withdrawals_bucketed'
TBLPROPERTIES ('avro.schema.url'='/user/team3/project/warehouse/avsc/cash_withdrawals.avsc');

-- Копируем данные в бакетированную таблицу
INSERT OVERWRITE TABLE cash_withdrawals_bucketed
SELECT * FROM cash_withdrawals_avro;

-- Удаляем исходные неоптимизированные таблицы
DROP TABLE IF EXISTS transactions_avro;
DROP TABLE IF EXISTS cash_withdrawals_avro;
