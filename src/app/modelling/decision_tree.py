from typing import Tuple, List
import argparse
import logging
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline
from pyspark.ml.regression import DecisionTreeRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel
import sys, os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.app.utils.common import (
    setup_logger,
    init_spark_session,
    load_or_prepare_data,
    save_results,
    save_metrics,
    save_model_parameters,
    prepare_features_pipeline
)


def train_models(
    train_data: DataFrame,
    test_data: DataFrame,
    logger: logging.Logger,
    spark: SparkSession,
    max_depth: int,
    min_instances_per_node: int,
    min_info_gain: float,
    num_folds: int,
    output_path: str
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train decision tree models for coordinate prediction."""
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
    dt_lon = DecisionTreeRegressor(
        featuresCol="features",
        labelCol="lon",
        maxDepth=max_depth,
        minInstancesPerNode=min_instances_per_node,
        minInfoGain=min_info_gain
    )
    
    dt_lat = DecisionTreeRegressor(
        featuresCol="features",
        labelCol="lat",
        maxDepth=max_depth,
        minInstancesPerNode=min_instances_per_node,
        minInfoGain=min_info_gain
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(dt_lon.maxDepth, [max_depth]) \
        .addGrid(dt_lon.minInstancesPerNode, [min_instances_per_node]) \
        .addGrid(dt_lon.minInfoGain, [min_info_gain]) \
        .build()
    
    evaluator = RegressionEvaluator(
        labelCol="lon",
        predictionCol="prediction",
        metricName="mae"
    )
    
    cv_lon = CrossValidator(
        estimator=dt_lon,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds
    )
    
    cv_lat = CrossValidator(
        estimator=dt_lat,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds
    )
    
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
    
    predictions_lon = cv_model_lon.transform(test_data)
    predictions_lat = cv_model_lat.transform(test_data)
    
    mae_lon = evaluator.evaluate(predictions_lon)
    evaluator.setLabelCol("lat")
    mae_lat = evaluator.evaluate(predictions_lat)
    
    logger.info(f"Test MAE for longitude: {mae_lon}")
    logger.info(f"Test MAE for latitude: {mae_lat}")
    
    metrics = {
        "longitude_mae": float(mae_lon),
        "latitude_mae": float(mae_lat),
        "model_params": {
            "max_depth": max_depth,
            "min_instances_per_node": min_instances_per_node,
            "min_info_gain": min_info_gain,
            "num_folds": num_folds
        }
    }
    save_metrics(metrics, "decision_tree", logger)
    
    save_model_parameters(
        cv_model_lon,
        feature_names,
        spark,
        logger,
        "decision_tree",
        "lon",
        "importance"
    )
    
    save_model_parameters(
        cv_model_lat,
        feature_names,
        spark,
        logger,
        "decision_tree",
        "lat",
        "importance"
    )
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Train decision tree models")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum depth of the tree"
    )
    parser.add_argument(
        "--min-instances",
        type=int,
        default=3,
        help="Minimum number of instances per node"
    )
    parser.add_argument(
        "--min-info-gain",
        type=float,
        default=0.0,
        help="Minimum information gain for a split"
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
    
    logger = setup_logger("decision_tree")
    
    try:
        spark = init_spark_session(
            "team3", 
            f"{output_path}/project/warehouse", 
            "Distributed Decision Tree"
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
            args.max_depth,
            args.min_instances,
            args.min_info_gain,
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
            "decision_tree"
        )
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("Work completed...")


if __name__ == "__main__":
    main() 