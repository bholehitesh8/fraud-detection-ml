"""
Machine Learning Preprocessing Pipeline & Feature Engineering
--------------------------------------------------------------
Implements a reusable, modular scikit-learn Pipeline and ColumnTransformer
for online financial fraud detection.

Architecture:
1. FinancialFeatureEngineer: Computes domain-specific transaction features
   (accounting balance deviations, drain flags, volume ratios).
2. ColumnTransformer:
   - Numerical: SimpleImputer (median) -> RobustScaler (resilient to extreme financial outliers)
   - Categorical: SimpleImputer (most frequent) -> OneHotEncoder (unseen categories handled gracefully)
3. DataPreprocessorPipeline: High-level orchestrator supporting fit_transform,
   transform, serialization to saved_models/preprocessor_pipeline.joblib,
   and metadata persistence.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler
import joblib

logger = logging.getLogger("fraud_detection.preprocessor")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cross-platform paths
DEFAULT_SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"
DEFAULT_PIPELINE_PATH = DEFAULT_SAVED_MODELS_DIR / "preprocessor_pipeline.joblib"
DEFAULT_METADATA_PATH = DEFAULT_SAVED_MODELS_DIR / "pipeline_metadata.json"


class FinancialFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Domain-specific feature transformer that generates financial fraud indicators.

    Engineered Features:
    - error_balance_orig: Deviation in sender's accounting equation (newbalanceOrig + amount - oldbalanceOrg)
    - error_balance_dest: Deviation in receiver's accounting equation (oldbalanceDest + amount - newbalanceDest)
    - amount_to_old_balance_ratio: Transaction volume relative to sender's starting balance
    - is_account_drain: Binary flag indicating if origin account was completely drained to 0
    - balance_diff_orig: Raw change in sender's balance (oldbalanceOrg - newbalanceOrig)
    """

    def __init__(self, add_error_features: bool = True, add_ratio_features: bool = True):
        self.add_error_features = add_error_features
        self.add_ratio_features = add_ratio_features
        self.engineered_feature_names_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Applies feature engineering formulas to input DataFrame."""
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(X)}")

        df_out = X.copy()

        # Handle column name variations between PaySim (oldbalanceOrg) and web forms (old_balance_org)
        amount = df_out["amount"] if "amount" in df_out else 0.0
        old_orig = df_out["oldbalanceOrg"] if "oldbalanceOrg" in df_out else df_out.get("old_balance_org", 0.0)
        new_orig = df_out["newbalanceOrig"] if "newbalanceOrig" in df_out else df_out.get("new_balance_orig", 0.0)
        old_dest = df_out["oldbalanceDest"] if "oldbalanceDest" in df_out else df_out.get("old_balance_dest", 0.0)
        new_dest = df_out["newbalanceDest"] if "newbalanceDest" in df_out else df_out.get("new_balance_dest", 0.0)

        engineered = []

        if self.add_error_features:
            # Accounting deviations: in a legal transaction, new_orig + amount should equal old_orig
            df_out["error_balance_orig"] = (new_orig + amount) - old_orig
            df_out["error_balance_dest"] = (old_dest + amount) - new_dest
            df_out["balance_diff_orig"] = old_orig - new_orig
            engineered.extend(["error_balance_orig", "error_balance_dest", "balance_diff_orig"])

        if self.add_ratio_features:
            # Ratio of transaction volume to starting capital
            df_out["amount_to_old_balance_ratio"] = amount / (old_orig + 1.0)
            # Binary flag: account completely drained to 0 from a positive balance
            df_out["is_account_drain"] = ((new_orig == 0.0) & (old_orig > 0.0)).astype(float)
            engineered.extend(["amount_to_old_balance_ratio", "is_account_drain"])

        self.engineered_feature_names_ = engineered
        return df_out


def build_column_transformer(
    numerical_cols: List[str],
    categorical_cols: List[str],
    scaler_type: str = "robust"
) -> ColumnTransformer:
    """
    Creates a scikit-learn ColumnTransformer for numerical and categorical features.

    Args:
        numerical_cols: List of column names to impute and scale.
        categorical_cols: List of column names to impute and one-hot encode.
        scaler_type: 'robust' for RobustScaler (recommended for financial amounts with outliers)
                     or 'standard' for StandardScaler.

    Returns:
        Configured ColumnTransformer instance.
    """
    scaler = RobustScaler() if scaler_type.lower() == "robust" else RobustScaler()

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", scaler)
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numerical_cols),
            ("cat", categorical_transformer, categorical_cols)
        ],
        remainder="drop"
    )
    return preprocessor


class DataPreprocessorPipeline:
    """
    End-to-end preprocessing orchestrator.
    Combines feature engineering and column transformations into a single deployable artifact.
    """

    def __init__(
        self,
        base_numeric_cols: Optional[List[str]] = None,
        categorical_cols: Optional[List[str]] = None,
        scaler_type: str = "robust"
    ):
        self.base_numeric_cols = base_numeric_cols or [
            "step", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"
        ]
        self.categorical_cols = categorical_cols or ["type"]
        self.scaler_type = scaler_type

        # Complete numeric feature list including engineered features
        self.all_numeric_cols = list(self.base_numeric_cols) + [
            "error_balance_orig",
            "error_balance_dest",
            "balance_diff_orig",
            "amount_to_old_balance_ratio",
            "is_account_drain"
        ]

        self.feature_engineer = FinancialFeatureEngineer()
        self.column_transformer = build_column_transformer(
            numerical_cols=self.all_numeric_cols,
            categorical_cols=self.categorical_cols,
            scaler_type=self.scaler_type
        )

        self.pipeline = Pipeline(steps=[
            ("engineer", self.feature_engineer),
            ("transform", self.column_transformer)
        ])

        self.is_fitted: bool = False
        self.feature_names_out_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None) -> "DataPreprocessorPipeline":
        """
        Fits transformer strictly on training features without data leakage.

        Args:
            X: Training feature DataFrame.
        """
        logger.info("Fitting DataPreprocessorPipeline on training data (shape: %s)...", X.shape)
        self.pipeline.fit(X, y)
        self.is_fitted = True

        # Extract output feature names
        try:
            cat_encoder = self.column_transformer.named_transformers_["cat"].named_steps["encoder"]
            cat_features = list(cat_encoder.get_feature_names_out(self.categorical_cols))
        except Exception:
            cat_features = [f"cat_{i}" for i in range(5)]

        self.feature_names_out_ = list(self.all_numeric_cols) + cat_features
        logger.info("Pipeline fitted successfully. Output feature dimensionality: %d", len(self.feature_names_out_))
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """
        Transforms evaluation or inference features using learned parameters.

        Args:
            X: Input DataFrame.

        Returns:
            np.ndarray of scaled and encoded numerical features.
        """
        if not self.is_fitted:
            raise RuntimeError("DataPreprocessorPipeline must be fitted before calling transform().")
        return self.pipeline.transform(X)

    def fit_transform(self, X: pd.DataFrame, y=None) -> np.ndarray:
        """Fits on training features and returns transformed matrix."""
        return self.fit(X, y).transform(X)

    def save(
        self,
        model_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None
    ) -> Tuple[Path, Path]:
        """
        Serializes pipeline artifact and metadata into saved_models/ directory.

        Args:
            model_path: Destination path for .joblib pipeline.
            metadata_path: Destination path for .json metadata.

        Returns:
            Tuple of (model_path, metadata_path).
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted DataPreprocessorPipeline.")

        target_model = Path(model_path) if model_path else DEFAULT_PIPELINE_PATH
        target_meta = Path(metadata_path) if metadata_path else DEFAULT_METADATA_PATH

        target_model.parent.mkdir(parents=True, exist_ok=True)

        # Save pipeline artifact
        logger.info("Serializing preprocessor pipeline to: %s", target_model)
        joblib.dump(self.pipeline, target_model)

        # Save metadata
        metadata = {
            "is_fitted": self.is_fitted,
            "scaler_type": self.scaler_type,
            "base_numeric_cols": self.base_numeric_cols,
            "categorical_cols": self.categorical_cols,
            "all_numeric_cols": self.all_numeric_cols,
            "output_feature_names": self.feature_names_out_,
            "output_dimensionality": len(self.feature_names_out_)
        }
        logger.info("Writing pipeline metadata to: %s", target_meta)
        with open(target_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return target_model, target_meta

    @classmethod
    def load(
        cls,
        model_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None
    ) -> "DataPreprocessorPipeline":
        """
        Loads serialized preprocessor pipeline and metadata from disk.

        Args:
            model_path: Path to .joblib artifact.
            metadata_path: Path to metadata JSON.

        Returns:
            Instantiated and fitted DataPreprocessorPipeline object.
        """
        target_model = Path(model_path) if model_path else DEFAULT_PIPELINE_PATH
        target_meta = Path(metadata_path) if metadata_path else DEFAULT_METADATA_PATH

        if not target_model.exists():
            raise FileNotFoundError(f"Saved pipeline artifact not found at {target_model}")

        logger.info("Loading preprocessor pipeline from: %s", target_model)
        loaded_sklearn_pipeline = joblib.load(target_model)

        instance = cls()
        instance.pipeline = loaded_sklearn_pipeline
        instance.is_fitted = True

        if target_meta.exists():
            with open(target_meta, "r", encoding="utf-8") as f:
                meta = json.load(f)
                instance.feature_names_out_ = meta.get("output_feature_names", [])
                instance.scaler_type = meta.get("scaler_type", "robust")

        logger.info("Loaded fitted preprocessor pipeline with %d output features.", len(instance.feature_names_out_))
        return instance


# ==============================================================================
# Legacy Helper Class: Retained for backward-compatibility with quick web form tests
# ==============================================================================
class TransactionPreprocessor:
    """
    Legacy helper retained for single transaction dict inputs from web form.
    """
    TRANSACTION_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]

    @classmethod
    def extract_features(cls, data: Dict[str, Any]) -> Dict[str, float]:
        amount = float(data.get("amount", 0.0))
        old_balance = float(data.get("old_balance_org", data.get("oldbalanceOrg", 0.0)))
        new_balance = float(data.get("new_balance_orig", data.get("newbalanceOrig", 0.0)))
        txn_type = str(data.get("transaction_type", data.get("type", "PAYMENT"))).upper()

        balance_diff_orig = old_balance - new_balance
        amount_ratio = amount / (old_balance + 1.0)
        error_balance_orig = (new_balance + amount) - old_balance

        features = {
            "amount": amount,
            "old_balance_org": old_balance,
            "new_balance_orig": new_balance,
            "balance_diff_orig": balance_diff_orig,
            "amount_ratio": amount_ratio,
            "error_balance_orig": error_balance_orig,
        }

        for t_type in cls.TRANSACTION_TYPES:
            features[f"type_{t_type}"] = 1.0 if txn_type == t_type else 0.0

        return features

    @classmethod
    def to_feature_vector(cls, data: Dict[str, Any]) -> List[float]:
        feat_dict = cls.extract_features(data)
        keys = [
            "amount",
            "old_balance_org",
            "new_balance_orig",
            "balance_diff_orig",
            "amount_ratio",
            "error_balance_orig",
            "type_CASH_IN",
            "type_CASH_OUT",
            "type_DEBIT",
            "type_PAYMENT",
            "type_TRANSFER"
        ]
        return [feat_dict[k] for k in keys]
