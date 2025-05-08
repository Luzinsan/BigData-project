USE team3_projectdb;

-- Удаляем старую таблицу результатов, если существует
DROP TABLE IF EXISTS q1_results;

CREATE EXTERNAL TABLE q1_results(
    h3_09 STRING,
    total_sum DECIMAL(15,2))
    
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q1';

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

INSERT OVERWRITE TABLE q1_results
SELECT 
    h3_09, 
    ROUND(SUM(sum), 2) AS total_sum 
FROM transactions_partitioned 
GROUP BY h3_09
ORDER BY total_sum DESC
LIMIT 20;
