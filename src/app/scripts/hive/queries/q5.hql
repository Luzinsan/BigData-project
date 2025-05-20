USE team3_projectdb;

DROP TABLE IF EXISTS transactions_per_h3;

CREATE TABLE transactions_per_h3(
  h3_09     STRING,
  total_sum DECIMAL(15,2),
  lat       DOUBLE,
  lon       DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q5';

INSERT OVERWRITE TABLE transactions_per_h3
SELECT
  t.h3_09,
  t.total_sum,
  l.lat,
  l.lon
FROM (
  SELECT
    h3_09,
    ROUND(SUM(CAST(`sum` AS DOUBLE)), 2) AS total_sum
  FROM transactions
  GROUP BY h3_09
) t
  JOIN locations l
    ON t.h3_09 = l.h3_09
WHERE t.h3_09 IS NOT NULL;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT *
FROM transactions_per_h3
ORDER BY total_sum DESC
LIMIT 10;