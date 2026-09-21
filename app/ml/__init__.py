"""
Machine Learning Subsystem
--------------------------
Handles dataset ingestion, data validation, preprocessing pipelines,
model training and comparison, metric-driven model selection,
and real-time transaction inference.
"""

from app.ml.preprocessor import (
    TransactionPreprocessor,
    FinancialFeatureEngineer,
    DataPreprocessorPipeline,
    build_column_transformer
)
from app.ml.data_loader import (
    load_dataset,
    validate_dataset,
    clean_dataset,
    identify_feature_types,
    separate_features_target,
    analyze_class_imbalance,
    split_data
)
from app.ml.models import get_candidate_models, MODEL_METADATA
from app.ml.evaluator import evaluate_single_model, save_evaluation_artifacts
from app.ml.model_selector import select_best_model, save_best_model_metadata
from app.ml.predictor import FraudPredictor, predict_transaction
from app.ml.prediction_service import PredictionService, get_prediction_service, ModelArtifactError
from app.ml.train import run_training_pipeline, train_model

__all__ = [
    "TransactionPreprocessor",
    "FinancialFeatureEngineer",
    "DataPreprocessorPipeline",
    "build_column_transformer",
    "load_dataset",
    "validate_dataset",
    "clean_dataset",
    "identify_feature_types",
    "separate_features_target",
    "analyze_class_imbalance",
    "split_data",
    "get_candidate_models",
    "MODEL_METADATA",
    "evaluate_single_model",
    "save_evaluation_artifacts",
    "select_best_model",
    "save_best_model_metadata",
    "FraudPredictor",
    "predict_transaction",
    "PredictionService",
    "get_prediction_service",
    "ModelArtifactError",
    "run_training_pipeline",
    "train_model"
]
