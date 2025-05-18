USE team3_projectdb;

DROP TABLE IF EXISTS q5_results;

CREATE TABLE q5_results(
  h3_09     STRING,
  total_sum DECIMAL(15,2),
  lat       DOUBLE,
  lon       DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q5';

INSERT OVERWRITE TABLE q5_results
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
FROM q5_results
ORDER BY total_sum DESC
LIMIT 10;