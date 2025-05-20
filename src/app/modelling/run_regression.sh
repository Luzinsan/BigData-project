#!/bin/bash

ENV_FILE=$(find $(pwd) -maxdepth 4 -name ".env" | head -1)

get_env_var() {
  grep -o "$1='[^']*'" "$ENV_FILE" | sed "s/$1='\(.*\)'/\1/"
}
password=$(get_env_var "DB_PASSWORD")

mkdir -p output/models/linear
spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.memory=4G \
    --conf spark.executor.memory=4G \
    --conf spark.executor.instances=2 \
    --conf spark.logConf=false \
    ./src/app/modelling/linear_regressor.py --force-prepare


mkdir -p output/models/decision_tree
spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.memory=4G \
    --conf spark.executor.memory=4G \
    --conf spark.executor.instances=2 \
    --conf spark.logConf=false \
    ./src/app/modelling/decision_tree.py --force-prepare


mkdir -p output/models/random_forest
spark-submit \
    --master yarn \
    --deploy-mode client \
--conf spark.driver.memory=4G \
--conf spark.executor.memory=4G \
--conf spark.executor.instances=2 \
--conf spark.logConf=false \
./src/app/modelling/random_forest.py


mkdir -p output/models/gbt
spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.memory=4G \
    --conf spark.executor.memory=4G \
    --conf spark.executor.instances=2 \
    --conf spark.logConf=false \
    ./src/app/modelling/mlp.py