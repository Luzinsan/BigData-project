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

from src.app.utils.common import (
    setup_logger,
    init_spark_session,
    load_or_prepare_data,
    save_results,
    save_metrics,
    prepare_features_pipeline,
    save_model_parameters
)


def train_models(
    train_data: DataFrame,
    test_data: DataFrame,
    logger: logging.Logger,
    spark: SparkSession,
    max_iter: int,
    reg_param: float,
    elastic_net_param: float,
    num_folds: int,
    output_path: str
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train linear regression models for coordinate prediction."""
    # Get feature names
    feature_names = [
        "total_transactions", "unique_mcc_count",
        "avg_transaction_amount", "std_transaction_amount",
        "max_time_slot", "min_time_slot",
        "location_transaction_count", "location_avg_amount",
        "location_unique_mcc_count"
    ]
    # Add hashed feature names for text features
    feature_names.extend([f"tag_feature_{i}" for i in range(25)])
    
    # Model setup
    lr_lon = LinearRegression(
        featuresCol="features",
        labelCol="lon",
        maxIter=max_iter,
        regParam=reg_param,
        elasticNetParam=elastic_net_param,
        solver="normal"
    )
    
    lr_lat = LinearRegression(
        featuresCol="features",
        labelCol="lat",
        maxIter=max_iter,
        regParam=reg_param,
        elasticNetParam=elastic_net_param,
        solver="normal"
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(lr_lon.regParam, [reg_param]) \
        .addGrid(lr_lon.elasticNetParam, [elastic_net_param]) \
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
        numFolds=num_folds
    )
    
    cv_lat = CrossValidator(
        estimator=lr_lat,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds
    )
    
    # Model training
    logger.info("Training longitude prediction model...")
    start_time = time.time()
    cv_model_lon = cv_lon.fit(train_data)
    logger.info(
        f"Longitude model training completed in {time.time() - start_time:.2f} seconds"
    )
    
    logger.info("Training latitude prediction model...")
    start_time = time.time()
    cv_model_lat = cv_lat.fit(train_data)
    logger.info(
        f"Latitude model training completed in {time.time() - start_time:.2f} seconds"
    )
    
    # Model evaluation
    predictions_lon = cv_model_lon.transform(test_data)
    predictions_lat = cv_model_lat.transform(test_data)
    
    mae_lon = evaluator.evaluate(predictions_lon)
    evaluator.setLabelCol("lat")
    mae_lat = evaluator.evaluate(predictions_lat)
    
    logger.info(f"Test MAE for longitude: {mae_lon}")
    logger.info(f"Test MAE for latitude: {mae_lat}")
    
    # Save metrics
    metrics = {
        "longitude_mae": float(mae_lon),
        "latitude_mae": float(mae_lat),
        "model_params": {
            "max_iter": max_iter,
            "reg_param": reg_param,
            "elastic_net_param": elastic_net_param,
            "num_folds": num_folds
        }
    }
    save_metrics(metrics, "linear", logger)
    
    # Save coefficients
    save_model_parameters(
        cv_model_lon,
        feature_names,
        spark,
        logger,
        "linear",
        "lon",
        "coefficients"
    )
    save_model_parameters(
        cv_model_lat,
        feature_names,
        spark,
        logger,
        "linear",
        "lat",
        "coefficients"
    )
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def main():
    """Main function to run the linear regression model training."""
    parser = argparse.ArgumentParser(description="Train linear regression models")
    parser.add_argument(
        "--max-iter",
        type=int,
        default=100,
        help="Maximum number of iterations for linear regression"
    )
    parser.add_argument(
        "--reg-param",
        type=float,
        default=0.1,
        help="Regularization parameter"
    )
    parser.add_argument(
        "--elastic-net-param",
        type=float,
        default=0.5,
        help="Elastic net parameter"
    )
    parser.add_argument(
        "--num-folds",
        type=int,
        default=3,
        help="Number of folds for cross-validation"
    )
    parser.add_argument(
        "--force-prepare",
        action="store_true",
        help="Force data preparation even if preprocessed data exists"
    )
    args = parser.parse_args()
    output_path = "hdfs:///user/team3"
    
    logger = setup_logger("linear")
    
    try:
        spark = init_spark_session(
            "team3", 
            f"{output_path}/project/warehouse", 
            "Distributed Linear Regression"
        )
        spark.sparkContext.setLogLevel("ERROR")
        spark.sparkContext.setCheckpointDir(
            f"{output_path}/checkpoints"
        )
        
        # Load or prepare train/test data
        train_data, test_data = load_or_prepare_data(
            spark,
            logger,
            output_path,
            args.force_prepare
        )
        
        cv_model_lon, cv_model_lat, mae_lon, mae_lat = train_models(
            train_data,
            test_data,
            logger,
            spark,
            args.max_iter,
            args.reg_param,
            args.elastic_net_param,
            args.num_folds,
            output_path
        )
        
        # Get predictions
        predictions_lon = cv_model_lon.transform(test_data)
        predictions_lat = cv_model_lat.transform(test_data)
        
        save_results(
            cv_model_lon,
            cv_model_lat,
            predictions_lon,
            predictions_lat,
            output_path,
            logger,
            "linear"
        )
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("Work completed...")


if __name__ == "__main__":
    main()