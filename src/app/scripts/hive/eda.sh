#!/bin/bash

ENV_FILE=$(find $(pwd) -maxdepth 4 -name ".env" | head -1)

get_env_var() {
  grep -o "$1='[^']*'" "$ENV_FILE" | sed "s/$1='\(.*\)'/\1/"
}
password=$(get_env_var "DB_PASSWORD")

mkdir -p output/hive/eda/
for query in src/app/scripts/hive/queries/q*.hql; do
  query_name=$(basename "$query" .hql)
  beeline \
    -u jdbc:hive2://hadoop-03.uni.innopolis.ru:10001 \
    --outputformat=csv2 \
    --silent=true \
    -n team3 \
    -p $password \
    -f "$query" \
    | grep -v "^$" \
    > "output/hive/eda/${query_name}.csv"
done