from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

spark = SparkSession.builder \
    .appName("Project Stage 3") \
    .master("yarn") \
    .config("hive.metastore.uris", "thrift://hadoop-02.uni.innopolis.ru:9883") \
    .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
    .enableHiveSupport() \
    .getOrCreate()

spark.sparkContext.setLogLevel("INFO")
spark.sql("USE team3_projectdb")

transactions = spark.read.format("avro").table("team3_projectdb.transactions")
cash_withdrawals = spark.read.format("avro").table("team3_projectdb.cash_withdrawals")
locations = spark.read.format("avro").table("team3_projectdb.locations")

data = transactions.join(cash_withdrawals, ["h3_09", "customer_id"], "inner") \
    .join(locations, ["h3_09"], "inner") \
    .drop("lat", "lon") \
    .dropna(subset=["datetime_id", "count", "sum", "avg", "min", "max", "std", "count_distinct"])

indexer = StringIndexer(inputCol="mcc_code", outputCol="mcc_index").setHandleInvalid("keep")
label_indexer = StringIndexer(inputCol="h3_09", outputCol="label").fit(data)
data = label_indexer.transform(data)
assembler = VectorAssembler(
    inputCols=["datetime_id", "count", "sum", "avg", "min", "max", "std", "count_distinct", "mcc_index"],
    outputCol="features"
).setHandleInvalid("skip")

pipeline = Pipeline(stages=[indexer, assembler])
preprocessed_data = pipeline.fit(data).transform(data)

train_data, test_data = preprocessed_data.randomSplit([0.8, 0.2], seed=42)
train_data.write.mode("overwrite").json("/user/team3/project/data/train")
test_data.write.mode("overwrite").json("/user/team3/project/data/test")

lr = LogisticRegression(featuresCol="features", labelCol="label")
param_grid_lr = ParamGridBuilder() \
    .addGrid(lr.regParam, [0.01, 0.1]) \
    .addGrid(lr.elasticNetParam, [0.0, 0.5]) \
    .build()
cv_lr = CrossValidator(estimator=lr,
                      estimatorParamMaps=param_grid_lr,
                      evaluator=MulticlassClassificationEvaluator(metricName="f1"),
                      numFolds=3)
model_lr = cv_lr.fit(train_data)
model_lr.bestModel.write().overwrite().save("hdfs:///project/models/model1")
predictions_lr = model_lr.transform(test_data)
predictions_lr.select("label", "prediction") \
    .coalesce(1) \
    .write.mode("overwrite") \
    .csv("hdfs:///project/output/model1_predictions")

rf = RandomForestClassifier(featuresCol="features", labelCol="label")
param_grid_rf = ParamGridBuilder() \
    .addGrid(rf.numTrees, [20, 50]) \
    .addGrid(rf.maxDepth, [5, 10]) \
    .build()
cv_rf = CrossValidator(estimator=rf,
                      estimatorParamMaps=param_grid_rf,
                      evaluator=MulticlassClassificationEvaluator(metricName="f1"),
                      numFolds=3)
model_rf = cv_rf.fit(train_data)
model_rf.bestModel.write().overwrite().save("hdfs:///project/models/model2")
predictions_rf = model_rf.transform(test_data)
predictions_rf.select("label", "prediction") \
    .coalesce(1) \
    .write.mode("overwrite") \
    .csv("hdfs:///project/output/model2_predictions")

evaluator = MulticlassClassificationEvaluator(metricName="accuracy")
lr_accuracy = evaluator.evaluate(predictions_lr)
rf_accuracy = evaluator.evaluate(predictions_rf)

results = spark.createDataFrame([
    ("Logistic Regression", lr_accuracy),
    ("Random Forest", rf_accuracy)
], ["model", "accuracy"])
results.coalesce(1) \
    .write.mode("overwrite") \
    .csv("hdfs:///project/output/evaluation")

spark.stop()
