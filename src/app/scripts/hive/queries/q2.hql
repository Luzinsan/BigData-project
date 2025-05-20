USE team3_projectdb;

DROP TABLE IF EXISTS word_frequency;

CREATE TABLE word_frequency(
  text_label  STRING,
  size_metric INT
)

ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/q2';

INSERT OVERWRITE TABLE word_frequency
SELECT 
  q.place_name AS text_label,
  COUNT(*) as size_metric
FROM cleaned_moscow q
INNER JOIN transactions t ON q.h3_09_center = t.h3_09
GROUP BY q.place_name
ORDER BY size_metric DESC;

SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT *
FROM word_frequency
ORDER BY size_metric DESC
LIMIT 20;
