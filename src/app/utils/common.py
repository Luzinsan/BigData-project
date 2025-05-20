import logging
import os
import traceback
import time
import json
from datetime import datetime
from typing import Tuple, List, Optional, Dict

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    VectorAssembler,
    StandardScaler,
    HashingTF,
    Tokenizer
)
from pyspark.ml.tuning import CrossValidatorModel
from pyspark.sql.functions import (
    col,
    concat_ws,
    collect_list,
    when,
    count,
    max,
    min,
    avg,
    stddev,
    current_timestamp,
    lit
)
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))


def setup_logger(
    name: str = __name__, 
    level: int = logging.INFO
) -> logging.Logger:
    """
    Logger setup
    
    Args:
        name (str): Logger name
        level (int): Logging level

    Returns:
        logger (logging.Logger): Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.hasHandlers():
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        os.makedirs(f'output/models/{name}/logs', exist_ok=True)
        file_handler = logging.FileHandler(
            f'output/models/{name}/logs/{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def init_spark_session(team: str, warehouse: str, app_name: str) -> SparkSession:
    """Initialize Spark session."""
    return SparkSession.builder \
        .appName(f"{team} - {app_name}") \
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
        .config("spark.ui.port", "4050") \
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


def prepare_data(
    cash_withdrawals: DataFrame,
    user_transaction_stats: DataFrame,
    user_location_stats: DataFrame,
    locations: DataFrame,
    grouped_moscow: DataFrame,
    logger: logging.Logger
) -> DataFrame:
    """Prepare combined dataset."""
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
    
    return data


def save_results(
    cv_model_lon: CrossValidatorModel,
    cv_model_lat: CrossValidatorModel,
    predictions_lon: DataFrame,
    predictions_lat: DataFrame,
    output_path: str,
    logger: logging.Logger,
    model_type: str = "model"
) -> None:
    """
    Save models and predictions.
    
    Args:
        cv_model_lon: CrossValidatorModel for longitude prediction
        cv_model_lat: CrossValidatorModel for latitude prediction
        predictions_lon: DataFrame with longitude predictions
        predictions_lat: DataFrame with latitude predictions
        output_path: Path to save results
        logger: Logger instance
        model_type: Type of model (e.g., "linear", "mlp") for naming
    """
    logger.info("Saving models and predictions...")
    
    # Save models
    cv_model_lon.bestModel.write().overwrite().save(
        f"{output_path}/models/{model_type}_model_lon"
    )
    cv_model_lat.bestModel.write().overwrite().save(
        f"{output_path}/models/{model_type}_model_lat"
    )
    
    # Combine and save predictions with all features
    predictions = predictions_lon.select(
        "customer_id", "h3_09", "lon", "prediction",
        "total_transactions", "unique_mcc_count",
        "avg_transaction_amount", "std_transaction_amount",
        "max_time_slot", "min_time_slot",
        "location_transaction_count", "location_avg_amount",
        "location_unique_mcc_count", "combined_tags"
    ) \
        .withColumnRenamed("prediction", "predicted_lon") \
        .withColumnRenamed("lon", "true_lon") \
        .join(
            predictions_lat.select(
                "customer_id", "h3_09", "lat", "prediction"
            ),
            ["customer_id", "h3_09"]
        ) \
        .withColumnRenamed("prediction", "predicted_lat") \
        .withColumnRenamed("lat", "true_lat")
    
    # Save predictions to HDFS
    predictions \
        .coalesce(1) \
        .write.mode("overwrite") \
        .parquet(f"{output_path}/predictions")
    
    # Save predictions locally
    local_predictions_dir = f"output/models/{model_type}/predictions"
    os.makedirs(local_predictions_dir, exist_ok=True)
    
    # Convert to pandas and save as CSV
    predictions_pd = predictions.toPandas()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    predictions_pd.to_csv(
        f"{local_predictions_dir}/predictions_{timestamp}.csv",
        index=False
    )
    
    logger.info(f"Predictions saved to {local_predictions_dir}")


def load_or_prepare_data(
    spark: SparkSession,
    logger: logging.Logger,
    output_path: str,
    force_prepare: bool = False
) -> DataFrame:
    """
    Load preprocessed data if exists, otherwise prepare it.
    
    Args:
        spark: SparkSession instance
        logger: Logger instance
        output_path: Path to save/load preprocessed data
        force_prepare: Force data preparation even if preprocessed data exists
        
    Returns:
        DataFrame: Preprocessed data
    """
    preprocessed_path = f"{output_path}/preprocessed_data"
    
    if not force_prepare:
        try:
            logger.info("Attempting to load preprocessed data...")
            data = spark.read.parquet(preprocessed_path)
            logger.info("Successfully loaded preprocessed data")
            return data
        except Exception as e:
            logger.warning(
                f"Could not load preprocessed data: {str(e)}. "
                "Will prepare data from scratch."
            )
    
    logger.info("Preparing data from scratch...")
    
    transactions, cash_withdrawals, locations, moscow = load_data(
        spark, logger
    )
    
    grouped_moscow = prepare_moscow_data(moscow, logger)
    user_transaction_stats, user_location_stats = create_transaction_features(
        transactions, logger
    )
    
    data = prepare_data(
        cash_withdrawals,
        user_transaction_stats,
        user_location_stats,
        locations,
        grouped_moscow,
        logger
    )
    
    logger.info("Saving preprocessed data...")
    data.write.mode("overwrite").parquet(preprocessed_path)
    logger.info("Preprocessed data saved successfully")
    
    return data


def save_metrics(
    metrics: Dict[str, float],
    model_name: str,
    logger: logging.Logger
) -> None:
    """
    Save model evaluation metrics to local filesystem.
    
    Args:
        metrics: Dictionary with metric names and values
        model_name: Name of the model (e.g., "linear", "mlp")
        logger: Logger instance
    """
    try:
        # Create directory if it doesn't exist
        metrics_dir = f"output/models/{model_name}/evaluate"
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Save metrics to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = f"{metrics_dir}/metrics_{timestamp}.json"
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=4)
        
        logger.info(f"Metrics saved to {metrics_file}")
        
    except Exception as e:
        logger.error(f"Failed to save metrics: {str(e)}")
        logger.error(traceback.format_exc())


def save_model_parameters(
    model: CrossValidatorModel,
    feature_names: List[str],
    output_path: str,
    logger: logging.Logger,
    model_type: str,
    coord_type: str,
    param_type: str = "coefficients"
) -> None:
    """
    Save model parameters (coefficients or feature importance) to Hive and local CSV.
    
    Args:
        model: Trained CrossValidatorModel
        feature_names: List of feature names
        output_path: Path to save results
        logger: Logger instance
        model_type: Type of model (e.g., "linear", "mlp", "decision_tree", "random_forest")
        coord_type: Type of coordinate ("lon" or "lat")
        param_type: Type of parameters to save ("coefficients" or "importance")
    """
    try:
        # Get parameters based on type
        if param_type == "coefficients":
            params = model.bestModel.coefficients.toArray()
            param_name = "coefficient"
        else:  # importance
            params = model.bestModel.featureImportances
            param_name = "importance"
        
        # Create DataFrame with parameters
        param_df = spark.createDataFrame(
            [(name, float(param)) for name, param in zip(feature_names, params)],
            ["feature", param_name]
        )
        
        # Add metadata columns
        param_df = param_df \
            .withColumn("model_type", lit(model_type)) \
            .withColumn("coord_type", lit(coord_type)) \
            .withColumn("timestamp", current_timestamp())
        
        # Save to Hive
        table_name = f"team3_projectdb.model_{param_type}"
        param_df.write.mode("append").saveAsTable(table_name)
        
        # Save locally
        local_dir = f"output/models/{model_type}/{param_type}"
        os.makedirs(local_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        param_df.toPandas().to_csv(
            f"{local_dir}/{coord_type}_{timestamp}.csv",
            index=False
        )
        
        logger.info(
            f"{param_type.capitalize()} for {coord_type} saved to {local_dir} "
            f"and Hive table {table_name}"
        )
        
    except Exception as e:
        logger.error(f"Failed to save {param_type}: {str(e)}")
        logger.error(traceback.format_exc())