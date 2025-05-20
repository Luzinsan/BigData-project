USE team3_projectdb;

DROP TABLE IF EXISTS withdraw_rate;

CREATE TABLE withdraw_rate(
  withdraw_tx    BIGINT,
  total_tx       BIGINT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q3';

INSERT OVERWRITE TABLE withdraw_rate
SELECT SUM(CASE
           WHEN w.customer_id IS NOT NULL THEN 1
           ELSE 0
        END) AS withdraw_tx,
      COUNT(*) AS total_tx
FROM transactions t
LEFT JOIN cash_withdrawals w ON t.customer_id = w.customer_id
AND t.h3_09 = w.h3_09;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT * FROM withdraw_rate;