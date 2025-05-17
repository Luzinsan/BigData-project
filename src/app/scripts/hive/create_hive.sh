#!/bin/bash

ENV_FILE=$(find $(pwd) -maxdepth 4 -name ".env" | head -1)

get_env_var() {
  grep -o "$1='[^']*'" "$ENV_FILE" | sed "s/$1='\(.*\)'/\1/"
}
password=$(get_env_var "DB_PASSWORD")

beeline -u jdbc:hive2://hadoop-03.uni.innopolis.ru:10001 -n team3 -p $password -f src/app/scripts/hive/db.hql
