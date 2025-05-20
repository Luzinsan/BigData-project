from typing import Tuple, List
import argparse
import logging
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline
from pyspark.ml.regression import MultilayerPerceptronRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel

from src.app.utils.common import (
    setup_logger,
    init_spark_session,
    load_or_prepare_data,
    save_results,
    save_metrics
)


def train_models(
    train_data: DataFrame,
    test_data: DataFrame,
    logger: logging.Logger,
    max_iter: int,
    layers: List[int],
    block_size: int,
    seed: int,
    num_folds: int
) -> Tuple[CrossValidatorModel, CrossValidatorModel, float, float]:
    """Train MLP models for coordinate prediction."""
    pipeline = prepare_features_pipeline()
    
    # Data transformation
    logger.info("Transforming data for longitude prediction...")
    start_time = time.time()
    
    pipeline_model = pipeline.fit(train_data)
    train_transformed = pipeline_model.transform(train_data).cache()
    test_transformed = pipeline_model.transform(test_data).cache()
    
    # Get feature dimension
    feature_dim = len(train_transformed.select("features").first()[0])
    
    # Update layers with input dimension
    layers = [feature_dim] + layers + [1]
    
    logger.info(
        f"Data transformation completed in {time.time() - start_time:.2f} seconds"
    )
    
    # Model setup
    mlp_lon = MultilayerPerceptronRegressor(
        featuresCol="features",
        labelCol="lon",
        layers=layers,
        maxIter=max_iter,
        blockSize=block_size,
        seed=seed
    )
    
    mlp_lat = MultilayerPerceptronRegressor(
        featuresCol="features",
        labelCol="lat",
        layers=layers,
        maxIter=max_iter,
        blockSize=block_size,
        seed=seed
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(mlp_lon.maxIter, [max_iter]) \
        .addGrid(mlp_lon.blockSize, [block_size]) \
        .build()
    
    evaluator = RegressionEvaluator(
        labelCol="lon",
        predictionCol="prediction",
        metricName="mae"
    )
    
    cv_lon = CrossValidator(
        estimator=mlp_lon,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds
    )
    
    cv_lat = CrossValidator(
        estimator=mlp_lat,
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
            "max_iter": max_iter,
            "layers": layers,
            "block_size": block_size,
            "seed": seed,
            "num_folds": num_folds
        }
    }
    save_metrics(metrics, "mlp", logger)
    
    return cv_model_lon, cv_model_lat, mae_lon, mae_lat


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Distributed MLP Pipeline")
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
        "--max-iter",
        type=int,
        default=100,
        help="Maximum number of iterations for MLP"
    )
    parser.add_argument(
        "--hidden-layers",
        type=str,
        default="64,32",
        help="Comma-separated list of hidden layer sizes"
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=128,
        help="Block size for MLP training"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for MLP"
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
    
    layers = [int(x) for x in args.hidden_layers.split(",")]
    
    logger = setup_logger("mlp_pipeline")
    
    try:
        spark = init_spark_session(args.team, args.warehouse, "Distributed MLP")
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
        
        train_data, test_data = data.randomSplit([0.8, 0.2], seed=args.seed)
        
        cv_model_lon, cv_model_lat, mae_lon, mae_lat = train_models(
            train_data,
            test_data,
            logger,
            args.max_iter,
            layers,
            args.block_size,
            args.seed,
            args.num_folds
        )
        
        save_results(
            cv_model_lon,
            cv_model_lat,
            cv_model_lon.transform(test_data),
            cv_model_lat.transform(test_data),
            args.output_path,
            logger,
            "mlp"
        )
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("Work completed...")


if __name__ == "__main__":
    main() 