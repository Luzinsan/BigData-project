from typing import Tuple, List
import argparse
import logging
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline
from pyspark.ml.regression import RandomForestRegressor
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
    num_trees: int,
    max_depth: int,
    min_instances_per_node: int,
    min_info_gain: float,
    subsampling_rate: float,
    num_folds: int,
    output_path: str
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train random forest models for coordinate prediction."""
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
    rf_lon = RandomForestRegressor(
        featuresCol="features",
        labelCol="lon",
        numTrees=num_trees,
        maxDepth=max_depth,
        minInstancesPerNode=min_instances_per_node,
        minInfoGain=min_info_gain,
        subsamplingRate=subsampling_rate
    )
    
    rf_lat = RandomForestRegressor(
        featuresCol="features",
        labelCol="lat",
        numTrees=num_trees,
        maxDepth=max_depth,
        minInstancesPerNode=min_instances_per_node,
        minInfoGain=min_info_gain,
        subsamplingRate=subsampling_rate
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(rf_lon.numTrees, [num_trees]) \
        .addGrid(rf_lon.maxDepth, [max_depth]) \
        .addGrid(rf_lon.minInstancesPerNode, [min_instances_per_node]) \
        .addGrid(rf_lon.minInfoGain, [min_info_gain]) \
        .addGrid(rf_lon.subsamplingRate, [subsampling_rate]) \
        .build()
    
    evaluator = RegressionEvaluator(
        labelCol="lon",
        predictionCol="prediction",
        metricName="mae"
    )
    
    cv_lon = CrossValidator(
        estimator=rf_lon,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds
    )
    
    cv_lat = CrossValidator(
        estimator=rf_lat,
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
            "num_trees": num_trees,
            "max_depth": max_depth,
            "min_instances_per_node": min_instances_per_node,
            "min_info_gain": min_info_gain,
            "subsampling_rate": subsampling_rate,
            "num_folds": num_folds
        }
    }
    save_metrics(metrics, "random_forest", logger)
    
    # Save feature importance
    save_model_parameters(
        cv_model_lon,
        feature_names,
        spark,
        logger,
        "random_forest",
        "lon",
        "importance"
    )
    
    save_model_parameters(
        cv_model_lat,
        feature_names,
        spark,
        logger,
        "random_forest",
        "lat",
        "importance"
    )
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Train random forest models")
    parser.add_argument(
        "--num-trees",
        type=int,
        default=20,
        help="Number of trees in the forest"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum depth of the trees"
    )
    parser.add_argument(
        "--min-instances",
        type=int,
        default=10,
        help="Minimum number of instances per node"
    )
    parser.add_argument(
        "--min-info-gain",
        type=float,
        default=0.0,
        help="Minimum information gain for a split"
    )
    parser.add_argument(
        "--subsampling-rate",
        type=float,
        default=1.0,
        help="Fraction of the training data used for learning each tree"
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
    
    logger = setup_logger("random_forest")
    
    try:
        spark = init_spark_session(
            "team3", 
            f"{output_path}/project/warehouse", 
            "Distributed Random Forest"
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
            args.num_trees,
            args.max_depth,
            args.min_instances,
            args.min_info_gain,
            args.subsampling_rate,
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
            "random_forest"
        )
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("Work completed...")


if __name__ == "__main__":
    main() 