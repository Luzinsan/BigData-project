from typing import Tuple, List
import argparse
import logging
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel

from src.app.utils.common import (
    setup_logger,
    init_spark_session,
    load_or_prepare_data,
    save_results,
    save_metrics,
    save_model_parameters
)


def train_models(
    train_data: DataFrame,
    test_data: DataFrame,
    logger: logging.Logger,
    num_trees: int,
    max_depth: int,
    min_instances_per_node: int,
    min_info_gain: float,
    subsampling_rate: float,
    num_folds: int
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train random forest models for coordinate prediction."""
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
    
    # Get feature names
    feature_names = train_transformed.schema["features"].metadata["ml_attr"]["attrs"]["numeric"] + \
                   train_transformed.schema["features"].metadata["ml_attr"]["attrs"]["binary"]
    feature_names = [f["name"] for f in feature_names]
    
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
        args.output_path,
        logger,
        "random_forest",
        "lon",
        "importance"
    )
    
    save_model_parameters(
        cv_model_lat,
        feature_names,
        args.output_path,
        logger,
        "random_forest",
        "lat",
        "importance"
    )
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Distributed Random Forest Pipeline")
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
        default=2,
        help="Number of folds for cross-validation"
    )
    parser.add_argument(
        "--force-prepare",
        action="store_true",
        help="Force data preparation even if preprocessed data exists"
    )
    args = parser.parse_args()
    
    logger = setup_logger("random_forest")
    
    try:
        spark = init_spark_session(args.team, args.warehouse, "Distributed Random Forest")
        spark.sparkContext.setLogLevel("ERROR")
        spark.sparkContext.setCheckpointDir(
            f"{args.output_path}/checkpoints"
        )
        
        data = load_or_prepare_data(
            spark,
            logger,
            args.output_path,
            args.force_prepare
        )
        
        train_data, test_data = data.randomSplit([0.8, 0.2], seed=42)
        
        cv_model_lon, cv_model_lat, mae_lon, mae_lat = train_models(
            train_data,
            test_data,
            logger,
            args.num_trees,
            args.max_depth,
            args.min_instances,
            args.min_info_gain,
            args.subsampling_rate,
            args.num_folds
        )
        
        save_results(
            cv_model_lon,
            cv_model_lat,
            cv_model_lon.transform(test_data),
            cv_model_lat.transform(test_data),
            args.output_path,
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