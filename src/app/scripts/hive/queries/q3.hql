USE team3_projectdb;

DROP TABLE IF EXISTS q3_results;

CREATE TABLE q3_results(
  h3_09    STRING,
  avg_sum  DOUBLE,
  max_sum  DOUBLE,
  min_sum  DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q3';

INSERT OVERWRITE TABLE q3_results
SELECT
  h3_09,
  ROUND(AVG(CAST(`sum` AS DOUBLE)), 2) AS avg_sum,
  MAX(CAST(`sum` AS DOUBLE))           AS max_sum,
  MIN(CAST(`sum` AS DOUBLE))           AS min_sum
FROM transactions
GROUP BY h3_09;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT * FROM q3_results
ORDER BY avg_sum DESC
LIMIT 20;