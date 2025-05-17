#!/bin/bash

ENV_FILE=$(find $(pwd) -maxdepth 4 -name ".env" | head -1)

get_env_var() {
  grep -o "$1='[^']*'" "$ENV_FILE" | sed "s/$1='\(.*\)'/\1/"
}
DB_NAME=$(get_env_var "DB_NAME")
DB_USER=$(get_env_var "DB_USER")
DB_PASSWORD=$(get_env_var "DB_PASSWORD")
DB_HOST=$(get_env_var "DB_HOST")
DB_PORT=$(get_env_var "DB_PORT")

# list all tables from database  
sqoop list-tables \
  --connect jdbc:postgresql://${DB_HOST}/${DB_NAME} \
  --username $DB_USER \
  --password $DB_PASSWORD \
  2> /dev/null

# import all tables from database
BASE_DIR="project/warehouse/"
hdfs dfs -rm -r -skipTrash $BASE_DIR

echo "Importing all tables from PostgreSQL to HDFS using Sqoop..."
echo "Using Parquet format with Gzip compression..."
sqoop import-all-tables \
  --connect jdbc:postgresql://${DB_HOST}/${DB_NAME} \
  --username $DB_USER \
  --password $DB_PASSWORD \
  --compression-codec=org.apache.hadoop.io.compress.GzipCodec \
  --compress \
  --as-parquetfile \
  --warehouse-dir=$BASE_DIR \
  --outdir output/hdfs/ \
  --m 1 \
  2> /dev/null

echo "Creating directory for AVSC schema files..."
hdfs dfs -mkdir -p $BASE_DIR/avsc

echo "Copying AVSC schema files to HDFS..."
hdfs dfs -put output/hdfs/*.avsc $BASE_DIR/avsc/