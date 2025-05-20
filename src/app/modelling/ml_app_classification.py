from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
from pyspark.sql.functions import col, concat_ws, collect_list, when

team = "team3"
warehouse = "project/hive/warehouse"

spark = SparkSession.builder \
    .appName(f"{team} - Spark ML") \
    .master("yarn") \
    .config("hive.metastore.uris", "thrift://hadoop-02.uni.innopolis.ru:9883") \
    .config("spark.sql.warehouse.dir", warehouse) \
    .enableHiveSupport() \
    .getOrCreate()

# spark = SparkSession.builder \
#     .appName(f"{team} - Spark ML") \
#     .master("local[*]") \
#     .config("hive.metastore.uris", "thrift://hadoop-02.uni.innopolis.ru:9883") \
#     .config("spark.sql.warehouse.dir", warehouse) \
#     .enableHiveSupport() \
#     .getOrCreate()


spark.sparkContext.setLogLevel("ERROR")
# spark.sql("USE team3_projectdb")
transactions = spark.read.format("parquet").table("team3_projectdb.transactions")
cash_withdrawals = spark.read.format("parquet").table("team3_projectdb.cash_withdrawals")
locations = spark.read.format("parquet").table("team3_projectdb.locations")
moscow = spark.read.format("parquet").table("team3_projectdb.q6_results")

# filtered_moscow = moscow.filter(
#     col("h3_09_center").isNotNull() & 
#     col("tags").isNotNull() &
#     ~col("tags").contains("traffic_light")
# )
grouped_moscow = moscow.groupBy("h3_09_center") \
    .agg(concat_ws(" ", collect_list("place_name")).alias("combined_tags")) \
    .withColumnRenamed("h3_09_center", "h3_09")

# data = transactions.join(cash_withdrawals, ["h3_09", "customer_id"]) \
#     .join(locations, "h3_09")
# data = data.join(grouped_moscow, "h3_09",  
#     "left") \
#     .drop("lat", "lon") \
#     .dropna(subset=["datetime_id", "count", "sum", "avg", "min", "max", "std", "count_distinct"]) \
#     .cache()

data = transactions.join(cash_withdrawals, ["h3_09", "customer_id"]) \
    .join(locations, "h3_09")
data = data.join(grouped_moscow, "h3_09", "left") \
    .drop("lat", "lon")

# Замена null в std на 0
data = data.withColumn("std", when(col("std").isNull(), 0).otherwise(col("std")))

# Замена пустых значений в combined_tags на "Не известно" вместо place_name
data = data.withColumn("combined_tags", 
    when((col("combined_tags").isNull()) | (col("combined_tags") == ""), "Не известно")
    .otherwise(col("combined_tags"))
)

data = data.dropna(subset=["datetime_id", "count", "sum", "avg", "min", "max", "std", "count_distinct"]) \
    .cache()

mcc_indexer = StringIndexer(inputCol="mcc_code", outputCol="mcc_index", handleInvalid="keep")
label_indexer = StringIndexer(inputCol="h3_09", outputCol="label", handleInvalid="keep")
tags_indexer = StringIndexer(inputCol="combined_tags", outputCol="tags_index")

assembler = VectorAssembler(
    inputCols=["datetime_id", "count", "sum", "avg", "min", "max", "std", "count_distinct", "mcc_index", "tags_index"],
    outputCol="features",
    handleInvalid="skip"
)

train, test = data.randomSplit([0.8, 0.2], seed=42)
train.write.mode("overwrite").json("train")
test.write.mode("overwrite").json("test")


def train_model(pipeline_stages, param_grid, model_name):
    full_pipeline = Pipeline(stages=[mcc_indexer, label_indexer, tags_indexer, assembler] + pipeline_stages)
    evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="f1")
    cv = CrossValidator(estimator=full_pipeline, estimatorParamMaps=param_grid, evaluator=evaluator, numFolds=3)
    cv_model = cv.fit(train)
    cv_model.bestModel.write().overwrite().save(f"models/{model_name}")
    return cv_model

lr_param_grid = ParamGridBuilder() \
    .addGrid(LogisticRegression.regParam, [0.01, 0.1]) \
    .addGrid(LogisticRegression.elasticNetParam, [0.0, 0.5]) \
    .build()

lr_model = train_model([LogisticRegression(featuresCol="features", labelCol="label")], lr_param_grid, "model1")

rf_param_grid = ParamGridBuilder() \
    .addGrid(RandomForestClassifier.numTrees, [20, 50]) \
    .addGrid(RandomForestClassifier.maxDepth, [5, 10]) \
    .build()

rf_model = train_model([RandomForestClassifier(featuresCol="features", labelCol="label")], rf_param_grid, "model2")

def evaluate_model(model, test_data, model_name):
    predictions = model.transform(test_data)
    evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")
    accuracy = evaluator.evaluate(predictions)
    predictions.select("label", "prediction").coalesce(1).write.mode("overwrite").csv(f"output/{model_name}_predictions")
    return accuracy

lr_accuracy = evaluate_model(lr_model, test, "model1")
rf_accuracy = evaluate_model(rf_model, test, "model2")

results = spark.createDataFrame([
    ("Logistic Regression", lr_accuracy),
    ("Random Forest", rf_accuracy)
], ["model", "accuracy"])

results.coalesce(1).write.mode("overwrite").csv("output/evaluation")

spark.stop()