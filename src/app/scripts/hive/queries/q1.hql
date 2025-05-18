USE team3_projectdb;

DROP TABLE IF EXISTS q1_results;

CREATE TABLE q1_results(
    h3_09 STRING,
    total_sum DECIMAL(15,2)
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q1';

INSERT OVERWRITE TABLE q1_results
SELECT 
    h3_09, 
    ROUND(SUM(sum), 2) AS total_sum 
FROM transactions 
GROUP BY h3_09;

SET hive.resultset.use.unique.column.names = false;
SET hive.cli.print.header=true;
SELECT * FROM q1_results
ORDER BY total_sum DESC
LIMIT 20;