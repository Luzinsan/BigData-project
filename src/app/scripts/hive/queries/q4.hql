USE team3_projectdb;

DROP TABLE IF EXISTS q4_results;

CREATE TABLE q4_results(
  total_transactions  BIGINT,
  overall_sum         DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q4';

INSERT OVERWRITE TABLE q4_results
SELECT
  COUNT(*)                   AS total_transactions,
  SUM(CAST(`sum` AS DOUBLE)) AS overall_sum
FROM transactions;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;
SELECT
  total_transactions,
  overall_sum
FROM q4_results;

