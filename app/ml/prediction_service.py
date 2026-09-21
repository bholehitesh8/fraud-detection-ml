"""
Production-Ready Machine Learning Prediction Service
----------------------------------------------------
Responsible for thread-safe, cached in-memory loading of:
- Trained ML model (fraud_model.joblib)
- Preprocessing pipeline (preprocessor_pipeline.joblib)
- Pipeline and model selection metadata
- ISO 4217 multi-currency conversion

Ensures high throughput by avoiding reloading from disk or retraining
on incoming API requests, while providing detailed error diagnostics.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import joblib

from app.ml.preprocessor import DataPreprocessorPipeline, TransactionPreprocessor
from app.utils.currency import convert_to_base_currency, normalize_currency_code
from app.utils.helpers import determine_risk_level

logger = logging.getLogger("fraud_detection.prediction_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cross-platform artifact paths using pathlib
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SAVED_MODELS_DIR = ROOT_DIR / "saved_models"
DEFAULT_MODEL_PATH = DEFAULT_SAVED_MODELS_DIR / "fraud_model.joblib"
DEFAULT_PIPELINE_PATH = DEFAULT_SAVED_MODELS_DIR / "preprocessor_pipeline.joblib"
DEFAULT_PIPELINE_META_PATH = DEFAULT_SAVED_MODELS_DIR / "pipeline_metadata.json"
DEFAULT_BEST_META_PATH = DEFAULT_SAVED_MODELS_DIR / "best_model_meta.json"


class ModelArtifactError(Exception):
    """Raised when machine learning artifacts are missing, unreadable, or corrupted."""
    pass


class PredictionService:
    """
    Singleton service managing model inference, preprocessor execution,
    and multi-currency transaction scaling.
    """
    _instance: Optional["PredictionService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PredictionService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_path: Optional[Path] = None,
        pipeline_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None
    ):
        if self._initialized:
            return

        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.pipeline_path = Path(pipeline_path) if pipeline_path else DEFAULT_PIPELINE_PATH
        self.metadata_path = Path(metadata_path) if metadata_path else DEFAULT_PIPELINE_META_PATH
        self.best_meta_path = DEFAULT_BEST_META_PATH

        self._model = None
        self._pipeline = None
        self._metadata = {}
        self._best_meta = {}
        self._model_name = "Unknown"
        self._model_version = "1.0.0"
        self._load_error: Optional[str] = None

        self.load_artifacts()
        self._initialized = True

    def load_artifacts(self) -> bool:
        """
        Loads all required ML model and preprocessor artifacts into memory once.
        Captures meaningful error diagnostics without throwing uncaught exceptions.
        """
        logger.info("Initializing prediction service artifacts from: %s", DEFAULT_SAVED_MODELS_DIR)
        errors = []

        # 1. Load Preprocessor Pipeline
        if not self.pipeline_path.exists():
            errors.append(f"Preprocessor pipeline file not found at: {self.pipeline_path}")
            self._pipeline = None
        else:
            try:
                self._pipeline = DataPreprocessorPipeline.load(self.pipeline_path)
                logger.info("Fitted preprocessor pipeline loaded successfully.")
            except Exception as e:
                err_msg = f"Failed to deserialize preprocessor pipeline: {e}"
                logger.error(err_msg)
                errors.append(err_msg)
                self._pipeline = None

        # 2. Load Trained Classifier Model
        if not self.model_path.exists():
            errors.append(f"Model artifact file not found at: {self.model_path}")
            self._model = None
        else:
            try:
                self._model = joblib.load(self.model_path)
                logger.info("Trained classifier loaded successfully: %s", type(self._model).__name__)
            except Exception as e:
                err_msg = f"Failed to deserialize model artifact: {e}"
                logger.error(err_msg)
                errors.append(err_msg)
                self._model = None

        # 3. Load Metadata
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning("Could not read pipeline metadata: %s", e)

        if self.best_meta_path.exists():
            try:
                with open(self.best_meta_path, "r", encoding="utf-8") as f:
                    self._best_meta = json.load(f)
                    self._model_name = self._best_meta.get("selected_model_name", type(self._model).__name__ if self._model else "Classifier")
            except Exception as e:
                logger.warning("Could not read best model metadata: %s", e)
        elif self._model:
            self._model_name = type(self._model).__name__

        if errors:
            self._load_error = "; ".join(errors)
            logger.warning("PredictionService started in degraded state: %s", self._load_error)
            return False

        self._load_error = None
        logger.info("PredictionService fully initialized and ready for real-time inference.")
        return True

    @property
    def is_ready(self) -> bool:
        """Returns True if all required ML artifacts are active in memory."""
        return (
            self._model is not None and
            self._pipeline is not None and
            self._pipeline.is_fitted
        )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Provides detailed system diagnostics for the GET /api/health endpoint.
        """
        model_exists = self.model_path.exists()
        pipeline_exists = self.pipeline_path.exists()
        meta_exists = self.metadata_path.exists()

        all_artifacts_available = model_exists and pipeline_exists and meta_exists
        is_operational = self.is_ready

        return {
            "api_running": True,
            "ml_model_loaded": self._model is not None,
            "preprocessor_loaded": self._pipeline is not None and self._pipeline.is_fitted,
            "artifacts_available": all_artifacts_available,
            "service_ready": is_operational,
            "artifacts": {
                "model_file": {"path": str(self.model_path), "exists": model_exists},
                "preprocessor_file": {"path": str(self.pipeline_path), "exists": pipeline_exists},
                "metadata_file": {"path": str(self.metadata_path), "exists": meta_exists}
            },
            "model_info": {
                "name": self._model_name,
                "version": self._model_version,
                "algorithm": type(self._model).__name__ if self._model else "None",
                "engineered_feature_count": len(self._pipeline.feature_names_out_) if (self._pipeline and self._pipeline.is_fitted) else 0
            },
            "load_error": self._load_error
        }

    def predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes ML preprocessing and inference on a validated transaction payload.

        Supports ISO 4217 multi-currency by normalizing non-USD amounts to base currency.

        Args:
            transaction: Validated transaction dictionary.

        Returns:
            Structured prediction dictionary.
        """
        if not self.is_ready:
            # Attempt one graceful reload in case artifacts were created post-startup
            if not self.load_artifacts() or not self.is_ready:
                raise ModelArtifactError(
                    f"Machine learning model or preprocessor artifacts are not available: {self._load_error or 'Artifacts not loaded'}"
                )

        # 1. Currency Normalization (ISO 4217 standard)
        currency_code = normalize_currency_code(transaction.get("currency", "USD"))
        raw_amount = float(transaction.get("amount", 0.0))
        raw_old_orig = float(transaction.get("old_balance_org", transaction.get("oldbalanceOrg", 0.0)))
        raw_new_orig = float(transaction.get("new_balance_orig", transaction.get("newbalanceOrig", 0.0)))
        raw_old_dest = float(transaction.get("old_balance_dest", transaction.get("oldbalanceDest", 0.0)))
        raw_new_dest = float(transaction.get("new_balance_dest", transaction.get("newbalanceDest", 0.0)))

        # Convert monetary amounts into model base currency (USD)
        norm_amount, rate, is_ref_rate = convert_to_base_currency(raw_amount, currency_code)
        norm_old_orig, _, _ = convert_to_base_currency(raw_old_orig, currency_code)
        norm_new_orig, _, _ = convert_to_base_currency(raw_new_orig, currency_code)
        norm_old_dest, _, _ = convert_to_base_currency(raw_old_dest, currency_code)
        norm_new_dest, _, _ = convert_to_base_currency(raw_new_dest, currency_code)

        txn_type = str(transaction.get("transaction_type", transaction.get("type", "PAYMENT"))).strip().upper()
        step_val = float(transaction.get("step", 1.0))

        # 2. Format single-row DataFrame matching the preprocessor schema
        row_df = pd.DataFrame([{
            "step": step_val,
            "type": txn_type,
            "amount": norm_amount,
            "oldbalanceOrg": norm_old_orig,
            "newbalanceOrig": norm_new_orig,
            "oldbalanceDest": norm_old_dest,
            "newbalanceDest": norm_new_dest
        }])

        # 3. Transform features via ColumnTransformer pipeline
        try:
            X_input = self._pipeline.transform(row_df)
        except Exception as e:
            logger.error("Preprocessing feature transformation error: %s", e)
            raise RuntimeError(f"Error during feature engineering and transformation: {e}") from e

        # 4. Model Scoring
        try:
            pred_class = int(self._model.predict(X_input)[0])
        except Exception as e:
            logger.error("Model prediction inference error: %s", e)
            raise RuntimeError(f"Error during model classification inference: {e}") from e

        # 5. Probability and Confidence calculation
        has_proba = False
        if hasattr(self._model, "predict_proba"):
            try:
                probs = self._model.predict_proba(X_input)[0]
                fraud_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
                has_proba = True
            except Exception:
                fraud_prob = 1.0 if pred_class == 1 else 0.0
        elif hasattr(self._model, "decision_function"):
            try:
                score = float(self._model.decision_function(X_input)[0])
                fraud_prob = float(1.0 / (1.0 + np.exp(-score)))
                has_proba = True
            except Exception:
                fraud_prob = 1.0 if pred_class == 1 else 0.0
        else:
            fraud_prob = 1.0 if pred_class == 1 else 0.0

        confidence = round(fraud_prob * 100.0, 2)
        is_fraud = bool(pred_class == 1)
        label = "Fraudulent" if is_fraud else "Legitimate"
        risk = determine_risk_level(fraud_prob)

        # Feature summary for inspection
        features_dict = TransactionPreprocessor.extract_features({
            "amount": norm_amount,
            "old_balance_org": norm_old_orig,
            "new_balance_orig": norm_new_orig,
            "transaction_type": txn_type
        })

        timestamp_iso = datetime.now(timezone.utc).isoformat()

        return {
            "is_fraud": is_fraud,
            "predicted_class": pred_class,
            "prediction_label": label,
            "fraud_probability": round(fraud_prob, 4) if has_proba else None,
            "confidence_score": confidence,
            "risk_level": risk,
            "currency": currency_code,
            "original_amount": raw_amount,
            "normalized_amount_usd": norm_amount,
            "exchange_rate": rate,
            "is_reference_currency": is_ref_rate,
            "model_info": {
                "name": self._model_name,
                "version": self._model_version,
                "algorithm": type(self._model).__name__
            },
            "timestamp": timestamp_iso,
            "validation_status": "Valid",
            "features": features_dict,
            "model_status": f"Active trained model ({self._model_name}) & Preprocessor Pipeline"
        }


def get_prediction_service() -> PredictionService:
    """Convenience helper to obtain the singleton PredictionService instance."""
    return PredictionService()
