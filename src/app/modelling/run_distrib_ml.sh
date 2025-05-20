spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.memory=4G \
    --conf spark.executor.memory=4G \
    --conf spark.executor.instances=2 \
    --conf spark.logConf=false \
    linear_regressor.py