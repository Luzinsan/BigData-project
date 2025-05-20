USE team3_projectdb;

DROP TABLE IF EXISTS cleaned_moscow;

CREATE TABLE cleaned_moscow(
    h3_09        STRING,
    h3_09_center STRING,
    lat          DOUBLE,
    lon          DOUBLE,
    place_name   STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LOCATION 'project/hive/warehouse/cleaned_moscow';

INSERT OVERWRITE TABLE cleaned_moscow
SELECT
    h3_09,
    h3_09_center,
    lat,
    lon,
    LOWER(TRIM(
        REGEXP_EXTRACT(one_tag_pair_string, "^\\('name',\\s*'(.*?)'\\)?$", 1)
    )) AS place_name
FROM
    moscow m
LATERAL VIEW EXPLODE(
    SPLIT(
        REGEXP_REPLACE(
            SUBSTR(m.tags, 2, LENGTH(m.tags) - 2),
            "'\\),\\s*\\('",
            "###HIVEDELIMITER###"
        ),
        "###HIVEDELIMITER###"
    )
) exploded_tags_table AS one_tag_pair_string
WHERE
    one_tag_pair_string LIKE "('name',%"
    AND REGEXP_EXTRACT(one_tag_pair_string, "^\\('name',\\s*'(.*?)'\\)?$", 1) IS NOT NULL
    AND TRIM(REGEXP_EXTRACT(one_tag_pair_string, "^\\('name',\\s*'(.*?)'\\)?$", 1)) != '';


SET hive.resultset.use.unique.column.names=false;
SET hive.cli.print.header=true;

SELECT *
FROM cleaned_moscow
LIMIT 50;