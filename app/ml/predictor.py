"""
Machine Learning Inference Engine
---------------------------------
Encapsulates saved model loading, preprocessor pipeline integration,
and real-time transaction scoring with proper error handling and logging.

Provides both:
1. `predict_transaction(...)`: Top-level functional interface.
2. `FraudPredictor`: High-performance singleton class interface used by Flask routes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import numpy as np
import pandas as pd
import joblib

from app.ml.preprocessor import DataPreprocessorPipeline, TransactionPreprocessor
from app.utils.helpers import determine_risk_level

logger = logging.getLogger("fraud_detection.predictor")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cross-platform paths using pathlib
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SAVED_MODELS_DIR = ROOT_DIR / "saved_models"
DEFAULT_MODEL_PATH = DEFAULT_SAVED_MODELS_DIR / "fraud_model.joblib"
DEFAULT_PIPELINE_PATH = DEFAULT_SAVED_MODELS_DIR / "preprocessor_pipeline.joblib"
DEFAULT_BEST_META_PATH = DEFAULT_SAVED_MODELS_DIR / "best_model_meta.json"


class FraudPredictor:
    """
    Inference orchestrator that coordinates the fitted DataPreprocessorPipeline
    and trained classification model to score incoming transactions.
    """
    _instance = None
    _model = None
    _pipeline = None
    _model_name = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FraudPredictor, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        pipeline_path: Optional[Union[str, Path]] = None
    ):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.pipeline_path = Path(pipeline_path) if pipeline_path else DEFAULT_PIPELINE_PATH

        if self._model is None:
            self.load_model()
        if self._pipeline is None:
            self.load_pipeline()
        if self._model_name is None:
            self._load_metadata()

    def _load_metadata(self) -> None:
        """Loads model name from best_model_meta.json if present."""
        if DEFAULT_BEST_META_PATH.exists():
            try:
                with open(DEFAULT_BEST_META_PATH, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self._model_name = meta.get("selected_model_name", "TrainedClassifier")
            except Exception as e:
                logger.warning("Could not parse best model metadata: %s", e)
                self._model_name = type(self._model).__name__ if self._model else "UnknownModel"
        elif self._model:
            self._model_name = type(self._model).__name__
        else:
            self._model_name = "NotLoaded"

    def load_model(self) -> bool:
        """Loads serialized scikit-learn model artifact from disk."""
        if not self.model_path.exists():
            logger.warning("Model artifact not found at: %s", self.model_path)
            return False

        try:
            self._model = joblib.load(self.model_path)
            self._load_metadata()
            logger.info("Successfully loaded trained model artifact from: %s", self.model_path)
            return True
        except Exception as e:
            logger.error("Error loading model from %s: %s", self.model_path, e)
            self._model = None
            return False

    def load_pipeline(self) -> bool:
        """Loads serialized preprocessing ColumnTransformer pipeline."""
        if not self.pipeline_path.exists():
            logger.warning("Preprocessor pipeline artifact not found at: %s", self.pipeline_path)
            return False

        try:
            self._pipeline = DataPreprocessorPipeline.load(self.pipeline_path)
            logger.info("Successfully loaded preprocessor pipeline from: %s", self.pipeline_path)
            return True
        except Exception as e:
            logger.error("Error loading preprocessor from %s: %s", self.pipeline_path, e)
            self._pipeline = None
            return False

    @property
    def is_model_loaded(self) -> bool:
        """Returns True if a trained model artifact is active in memory."""
        return self._model is not None

    @property
    def is_pipeline_loaded(self) -> bool:
        """Returns True if the preprocessor pipeline artifact is active."""
        return self._pipeline is not None and self._pipeline.is_fitted

    @property
    def model_name(self) -> str:
        """Returns the name of the currently active model."""
        return self._model_name or (type(self._model).__name__ if self._model else "None")

    def predict(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes end-to-end ML preprocessing and classification on the transaction payload.

        Args:
            transaction_data: Dictionary containing transaction features.

        Returns:
            Dict containing:
            - is_fraud: bool
            - predicted_class: int (0 or 1)
            - prediction_label: "Fraudulent" | "Legitimate"
            - probability: float (0.0 to 1.0)
            - confidence_score: float (0.0 to 100.0)
            - risk_level: "Low" | "Moderate" | "High" | "Critical"
            - model_name: str
            - features: Dict of extracted features
            - model_status: str
        """
        if not isinstance(transaction_data, dict):
            raise TypeError(f"transaction_data must be a dict, got {type(transaction_data)}")

        # Extract features for UI and transparency
        features_dict = TransactionPreprocessor.extract_features(transaction_data)

        # Ensure model is ready
        if not self.is_model_loaded:
            if not self.load_model():
                logger.warning("Inference attempted without trained model.")
                return {
                    "is_fraud": False,
                    "predicted_class": 0,
                    "prediction_label": "Model Not Ready",
                    "probability": 0.0,
                    "confidence_score": 0.0,
                    "risk_level": "Unclassified",
                    "model_name": "None",
                    "features": features_dict,
                    "model_status": "No trained model file found. Please run 'python -m app.ml.train' first."
                }

        # Format input DataFrame matching the training schema
        try:
            step_val = float(transaction_data.get("step", 1.0))
            txn_type = str(transaction_data.get("transaction_type", transaction_data.get("type", "PAYMENT"))).strip().upper()
            amount_val = float(transaction_data.get("amount", 0.0))
            old_orig = float(transaction_data.get("old_balance_org", transaction_data.get("oldbalanceOrg", 0.0)))
            new_orig = float(transaction_data.get("new_balance_orig", transaction_data.get("newbalanceOrig", 0.0)))
            old_dest = float(transaction_data.get("old_balance_dest", transaction_data.get("oldbalanceDest", 0.0)))
            new_dest = float(transaction_data.get("new_balance_dest", transaction_data.get("newbalanceDest", 0.0)))

            row_df = pd.DataFrame([{
                "step": step_val,
                "type": txn_type,
                "amount": amount_val,
                "oldbalanceOrg": old_orig,
                "newbalanceOrig": new_orig,
                "oldbalanceDest": old_dest,
                "newbalanceDest": new_dest
            }])
        except Exception as e:
            logger.error("Error parsing transaction payload fields: %s", e)
            raise ValueError(f"Invalid transaction payload data format: {e}") from e

        # Preprocessing transformation
        if self.is_pipeline_loaded or self.load_pipeline():
            X_input = self._pipeline.transform(row_df)
        else:
            logger.warning("Using fallback vector extraction since preprocessor pipeline is not serialized.")
            X_input = np.array([TransactionPreprocessor.to_feature_vector(transaction_data)])

        # Predict class
        try:
            pred_class = int(self._model.predict(X_input)[0])
        except Exception as e:
            logger.error("Model prediction failed: %s", e)
            raise RuntimeError(f"Model prediction failed: {e}") from e

        # Calculate probability and confidence score
        if hasattr(self._model, "predict_proba"):
            try:
                probs = self._model.predict_proba(X_input)[0]
                fraud_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
            except Exception:
                fraud_prob = 1.0 if pred_class == 1 else 0.0
        elif hasattr(self._model, "decision_function"):
            try:
                score = float(self._model.decision_function(X_input)[0])
                # Sigmoid transform for pseudo-probability
                fraud_prob = float(1.0 / (1.0 + np.exp(-score)))
            except Exception:
                fraud_prob = 1.0 if pred_class == 1 else 0.0
        else:
            fraud_prob = 1.0 if pred_class == 1 else 0.0

        confidence = round(fraud_prob * 100.0, 2)
        is_fraud = bool(pred_class == 1)
        label = "Fraudulent" if is_fraud else "Legitimate"
        risk = determine_risk_level(fraud_prob)

        return {
            "is_fraud": is_fraud,
            "predicted_class": pred_class,
            "prediction_label": label,
            "probability": round(fraud_prob, 4),
            "confidence_score": confidence,
            "risk_level": risk,
            "model_name": self.model_name,
            "features": features_dict,
            "model_status": f"Active trained model ({self.model_name}) & Preprocessor Pipeline"
        }


def predict_transaction(
    transaction_data: Dict[str, Any],
    model_path: Optional[Union[str, Path]] = None,
    pipeline_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Reusable top-level function to evaluate a single transaction.

    Args:
        transaction_data: Dictionary of transaction features.
        model_path: Optional custom path to serialized .joblib model.
        pipeline_path: Optional custom path to serialized .joblib preprocessor.

    Returns:
        Dict containing prediction class, probability, confidence, and risk level.
    """
    predictor = FraudPredictor(model_path=model_path, pipeline_path=pipeline_path)
    return predictor.predict(transaction_data)
