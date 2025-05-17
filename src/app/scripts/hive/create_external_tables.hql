DROP DATABASE IF EXISTS team3_projectdb CASCADE;
CREATE DATABASE team3_projectdb LOCATION '/user/team3/project/hive/warehouse';
USE team3_projectdb;

CREATE EXTERNAL TABLE locations
STORED AS PARQUET
LOCATION '/user/team3/project/warehouse/locations';

CREATE EXTERNAL TABLE transactions
STORED AS PARQUET
LOCATION '/user/team3/project/warehouse/transactions';

-- 3. Партиционированная версия transactions по дате
CREATE EXTERNAL TABLE transactions_partitioned
PARTITIONED BY (transaction_date STRING)
STORED AS PARQUET
LOCATION '/user/team3/project/warehouse/transactions_partitioned';

-- Заполняем партиционированную таблицу
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

INSERT OVERWRITE TABLE transactions_partitioned PARTITION(transaction_date)
SELECT 
    t.*,
    substr(datetime_id, 1, 10) as transaction_date 
FROM transactions_avro t;

-- 4. Таблица cash_withdrawals с бакетированием
CREATE EXTERNAL TABLE cash_withdrawals_bucketed
CLUSTERED BY (customer_id) INTO 10 BUCKETS
STORED AS PARQUET
LOCATION '/user/team3/project/warehouse/cash_withdrawals_bucketed';

-- Копируем данные в бакетированную таблицу
INSERT OVERWRITE TABLE cash_withdrawals_bucketed
SELECT * FROM cash_withdrawals_avro;

-- Удаляем исходные неоптимизированные таблицы
DROP TABLE IF EXISTS transactions_avro;
DROP TABLE IF EXISTS cash_withdrawals_avro;
