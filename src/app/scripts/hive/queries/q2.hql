USE team3_projectdb;

DROP TABLE IF EXISTS q2_results;

CREATE TABLE q2_results(
  h3_09       STRING,
  trans_count INT
)

ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q2';

INSERT OVERWRITE TABLE q2_results
SELECT
  h3_09,
  COUNT(*) AS trans_count
FROM transactions
GROUP BY h3_09;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT *
FROM q2_results
ORDER BY trans_count DESC
LIMIT 20;
