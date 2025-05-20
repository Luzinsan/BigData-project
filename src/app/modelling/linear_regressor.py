from typing import Tuple, List
import argparse
import logging
import time
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import (
    VectorAssembler,
    StandardScaler,
    HashingTF,
    Tokenizer
)
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel
from pyspark.sql.functions import (
    col,
    concat_ws,
    collect_list,
    when,
    count,
    max,
    min,
    avg,
    stddev
)
import os, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))



def setup_logger() -> logging.Logger:
    """Setup logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    file_handler = logging.FileHandler(
        f'output/models/linear_regression/logs/ml_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def init_spark_session(team: str, warehouse: str) -> SparkSession:
    """Initialize Spark session."""
    return SparkSession.builder \
        .appName(f"{team} - Distributed ML") \
        .master("yarn") \
        .config("hive.metastore.uris", "thrift://hadoop-02.uni.innopolis.ru:9883") \
        .config("spark.sql.warehouse.dir", warehouse) \
        .config("spark.sql.shuffle.partitions", "100") \
        .config("spark.default.parallelism", "100") \
        .config("spark.memory.fraction", "0.6") \
        .config("spark.memory.storageFraction", "0.5") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.kryoserializer.buffer.max", "512m") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.ui.port", "4060") \
        .config("spark.port.maxRetries", "20") \
        .enableHiveSupport() \
        .getOrCreate()


def load_data(
    spark: SparkSession,
    logger: logging.Logger
) -> Tuple[DataFrame, DataFrame, DataFrame, DataFrame]:
    """Load data from Hive tables."""
    start_time = time.time()
    
    transactions = spark.read.format("parquet").table("team3_projectdb.transactions")
    cash_withdrawals = spark.read.format("parquet").table(
        "team3_projectdb.cash_withdrawals"
    )
    locations = spark.read.format("parquet").table("team3_projectdb.locations")
    moscow = spark.read.format("parquet").table("team3_projectdb.cleaned_moscow")
    
    logger.info(
        f"Data loading completed in {time.time() - start_time:.2f} seconds"
    )
    
    return transactions, cash_withdrawals, locations, moscow


def prepare_moscow_data(
    moscow: DataFrame,
    logger: logging.Logger
) -> DataFrame:
    """Prepare Moscow locations data."""
    start_time = time.time()
    
    grouped_moscow = moscow.groupBy("h3_09_center") \
        .agg(concat_ws(" ", collect_list("place_name")).alias("combined_tags")) \
        .withColumnRenamed("h3_09_center", "h3_09") \
        .checkpoint()
    
    logger.info(
        f"Moscow data preparation completed in {time.time() - start_time:.2f} seconds"
    )
    
    return grouped_moscow


def create_transaction_features(
    transactions: DataFrame,
    logger: logging.Logger
) -> Tuple[DataFrame, DataFrame]:
    """Create features from transaction history."""
    start_time = time.time()
    
    # User statistics
    user_transaction_stats = transactions.groupBy("customer_id") \
        .agg(
            count("*").alias("total_transactions"),
            count("mcc_code").alias("unique_mcc_count"),
            avg("sum").alias("avg_transaction_amount"),
            stddev("sum").alias("std_transaction_amount"),
            max("datetime_id").alias("max_time_slot"),
            min("datetime_id").alias("min_time_slot")
        )
    
    # User-location pair statistics
    user_location_stats = transactions.groupBy("customer_id", "h3_09") \
        .agg(
            count("*").alias("location_transaction_count"),
            avg("sum").alias("location_avg_amount"),
            count("mcc_code").alias("location_unique_mcc_count")
        )
    
    logger.info(
        f"Feature creation completed in {time.time() - start_time:.2f} seconds"
    )
    
    return user_transaction_stats, user_location_stats


def prepare_features_pipeline() -> Pipeline:
    """Create features pipeline."""
    tokenizer = Tokenizer(
        inputCol="combined_tags",
        outputCol="tags_tokens"
    )
    hashingTF = HashingTF(
        inputCol="tags_tokens",
        outputCol="tags_features",
        numFeatures=25
    )
    
    numeric_cols = [
        "total_transactions", "unique_mcc_count",
        "avg_transaction_amount", "std_transaction_amount",
        "max_time_slot", "min_time_slot",
        "location_transaction_count", "location_avg_amount",
        "location_unique_mcc_count"
    ]
    
    numeric_assembler = VectorAssembler(
        inputCols=numeric_cols,
        outputCol="numeric_features"
    )
    scaler = StandardScaler(
        inputCol="numeric_features",
        outputCol="scaled_features"
    )
    
    final_assembler = VectorAssembler(
        inputCols=["tags_features", "scaled_features"],
        outputCol="features"
    )
    
    return Pipeline(stages=[
        tokenizer, hashingTF,
        numeric_assembler, scaler,
        final_assembler
    ])


def train_models(
    train_data: DataFrame,
    test_data: DataFrame,
    logger: logging.Logger
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train models for coordinate prediction."""
    pipeline = prepare_features_pipeline()
    
    # Data transformation
    logger.info("Transforming data for longitude prediction...")
    start_time = time.time()
    
    pipeline_model = pipeline.fit(train_data)
    train_transformed = pipeline_model.transform(train_data).cache()
    test_transformed = pipeline_model.transform(test_data).cache()
    
    logger.info(
        f"Data transformation completed in {time.time() - start_time:.2f} seconds"
    )
    
    # Model setup
    lr_lon = LinearRegression(
        featuresCol="features",
        labelCol="lon",
        maxIter=100,
        regParam=0.1,
        elasticNetParam=0.0,
        solver="normal"
    )
    
    lr_lat = LinearRegression(
        featuresCol="features",
        labelCol="lat",
        maxIter=100,
        regParam=0.1,
        elasticNetParam=0.0,
        solver="normal"
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(lr_lon.regParam, [0.1]) \
        .addGrid(lr_lon.elasticNetParam, [0.0]) \
        .build()
    
    evaluator = RegressionEvaluator(
        labelCol="lon",
        predictionCol="prediction",
        metricName="mae"
    )
    
    cv_lon = CrossValidator(
        estimator=lr_lon,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=2
    )
    
    cv_lat = CrossValidator(
        estimator=lr_lat,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=2
    )
    
    # Model training
    logger.info("Training longitude prediction model...")
    start_time = time.time()
    cv_model_lon = cv_lon.fit(train_transformed)
    logger.info(
        f"Longitude model training completed in {time.time() - start_time:.2f} seconds"
    )
    
    logger.info("Training latitude prediction model...")
    start_time = time.time()
    cv_model_lat = cv_lat.fit(train_transformed)
    logger.info(
        f"Latitude model training completed in {time.time() - start_time:.2f} seconds"
    )
    
    # Model evaluation
    predictions_lon = cv_model_lon.transform(test_transformed)
    predictions_lat = cv_model_lat.transform(test_transformed)
    
    mae_lon = evaluator.evaluate(predictions_lon)
    evaluator.setLabelCol("lat")
    mae_lat = evaluator.evaluate(predictions_lat)
    
    logger.info(f"Test MAE for longitude: {mae_lon}")
    logger.info(f"Test MAE for latitude: {mae_lat}")
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def save_results(
    cv_model_lon: CrossValidatorModel,
    cv_model_lat: CrossValidatorModel,
    predictions_lon: DataFrame,
    predictions_lat: DataFrame,
    output_path: str,
    logger: logging.Logger
) -> None:
    """Save models and predictions."""
    logger.info("Saving models and predictions...")
    
    # Save models
    cv_model_lon.bestModel.write().overwrite().save(
        f"{output_path}/models/lr_model_lon"
    )
    cv_model_lat.bestModel.write().overwrite().save(
        f"{output_path}/models/lr_model_lat"
    )
    
    # Combine and save predictions
    predictions = predictions_lon.select(
        "customer_id", "h3_09", "lon", "prediction"
    ) \
        .withColumnRenamed("prediction", "predicted_lon") \
        .join(
            predictions_lat.select(
                "customer_id", "h3_09", "lat", "prediction"
            ),
            ["customer_id", "h3_09"]
        ) \
        .withColumnRenamed("prediction", "predicted_lat")
    
    predictions \
        .coalesce(1) \
        .write.mode("overwrite") \
        .parquet(f"{output_path}/predictions")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Distributed ML Pipeline")
    parser.add_argument(
        "--team",
        type=str,
        default="team3",
        help="Team name"
    )
    parser.add_argument(
        "--warehouse",
        type=str,
        default="project/hive/warehouse",
        help="Hive warehouse path"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="hdfs:///user/team3",
        help="Output path for models and predictions"
    )
    args = parser.parse_args()
    
    # Initialize logger
    logger = setup_logger()
    
    try:
        # Initialize Spark
        spark = init_spark_session(args.team, args.warehouse)
        spark.sparkContext.setLogLevel("ERROR")
        spark.sparkContext.setCheckpointDir(
            f"{args.output_path}/checkpoints"
        )
        
        # Load data
        transactions, cash_withdrawals, locations, moscow = load_data(
            spark, logger
        )
        
        # Prepare data
        grouped_moscow = prepare_moscow_data(moscow, logger)
        user_transaction_stats, user_location_stats = create_transaction_features(
            transactions, logger
        )
        
        # Combine data
        data = cash_withdrawals \
            .join(user_transaction_stats, "customer_id", "left") \
            .join(user_location_stats, ["customer_id", "h3_09"], "left") \
            .join(locations, "h3_09", "left") \
            .join(grouped_moscow, "h3_09", "left") \
            .withColumn(
                "combined_tags",
                when(
                    (col("combined_tags").isNull()) |
                    (col("combined_tags") == ""),
                    "Unknown"
                ).otherwise(col("combined_tags"))
            ) \
            .na.fill(0) \
            .repartition(100) \
            .cache()
        
        logger.info(f"Initial dataset size: {data.count()} rows")
        logger.info(
            f"Number of unique h3_09: "
            f"{data.select('h3_09').distinct().count()}"
        )
        
        # Split into train and test
        train_data, test_data = data.randomSplit([0.8, 0.2], seed=42)
        
        # Train models
        cv_model_lon, cv_model_lat, mae_lon, mae_lat = train_models(
            train_data, test_data, logger
        )
        
        # Save results
        save_results(
            cv_model_lon,
            cv_model_lat,
            cv_model_lon.transform(test_data),
            cv_model_lat.transform(test_data),
            args.output_path,
            logger
        )
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("Work completed...")


if __name__ == "__main__":
    main()