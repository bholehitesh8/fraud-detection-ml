"""
Data Loading, Validation, and Partitioning Subsystem
---------------------------------------------------
Provides cross-platform, robust utilities for:
- Loading raw financial transaction datasets using pathlib
- Schema and integrity validation before model consumption
- Missing value resolution and duplicate elimination
- Feature/target partitioning (X and y)
- Class imbalance diagnostics and balanced weight calculation
- Stratified train/test dataset splitting to prevent data leakage
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

# Configure module-level logging
logger = logging.getLogger("fraud_detection.data_loader")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cross-platform paths
DEFAULT_RAW_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "online_fraud_dataset.csv"

# Expected PaySim schema definition
REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud"
]

NUMERICAL_COLUMNS = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest"
]

CATEGORICAL_COLUMNS = [
    "type"
]


def load_dataset(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads transaction records from a CSV file into a pandas DataFrame.

    Args:
        filepath: Optional Path object. Defaults to data/raw/online_fraud_dataset.csv.

    Returns:
        pd.DataFrame containing the loaded dataset.

    Raises:
        FileNotFoundError: If the specified CSV does not exist.
        ValueError: If file is empty or corrupted.
    """
    path = Path(filepath) if filepath else DEFAULT_RAW_DATA_PATH
    logger.info("Loading transaction dataset from: %s", path)

    if not path.exists():
        msg = f"Dataset file not found at: {path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.error("Failed to parse CSV file: %s", e)
        raise ValueError(f"Unable to read CSV dataset: {e}") from e

    if df.empty:
        msg = f"Loaded dataset at {path} is empty."
        logger.error(msg)
        raise ValueError(msg)

    logger.info("Successfully loaded %d records across %d columns.", len(df), df.shape[1])
    return df


def validate_dataset(df: pd.DataFrame, target_col: str = "isFraud") -> Tuple[bool, List[str]]:
    """
    Validates schema conformance, data types, and logical value ranges.

    Args:
        df: Input DataFrame to validate.
        target_col: Name of the ground-truth classification column.

    Returns:
        Tuple of (is_valid: bool, issues: List[str]).
    """
    issues: List[str] = []

    if not isinstance(df, pd.DataFrame):
        return False, ["Input is not a pandas DataFrame."]

    # 1. Required columns presence
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        issues.append(f"Missing mandatory columns: {missing_cols}")

    # 2. Target column validation
    if target_col not in df.columns:
        issues.append(f"Target column '{target_col}' not found.")
    else:
        unique_targets = set(df[target_col].dropna().unique())
        if not unique_targets.issubset({0, 1}):
            issues.append(f"Target column '{target_col}' must be binary (0 or 1), got: {unique_targets}")

    # 3. Numeric constraints (amounts and balances must be >= 0)
    for col in NUMERICAL_COLUMNS:
        if col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"Column '{col}' expected numeric, got {df[col].dtype}")
            else:
                neg_count = (df[col] < 0).sum()
                if neg_count > 0:
                    issues.append(f"Column '{col}' contains {neg_count} negative values.")

    is_valid = len(issues) == 0
    if not is_valid:
        logger.warning("Dataset validation failed with %d issues: %s", len(issues), issues)
    else:
        logger.info("Dataset validation passed successfully.")

    return is_valid, issues


def clean_dataset(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    fill_missing: bool = True
) -> pd.DataFrame:
    """
    Cleans dataset by detecting and resolving duplicate records and missing values.

    Args:
        df: Raw DataFrame.
        drop_duplicates: Whether to drop identical transaction rows.
        fill_missing: Whether to impute missing values (median for numeric, mode for categorical).

    Returns:
        Cleaned pd.DataFrame.
    """
    clean_df = df.copy()

    # 1. Duplicate handling
    dup_count = clean_df.duplicated().sum()
    if dup_count > 0:
        logger.warning("Detected %d duplicate records in dataset.", dup_count)
        if drop_duplicates:
            clean_df = clean_df.drop_duplicates().reset_index(drop=True)
            logger.info("Dropped %d duplicate records. Retained %d unique rows.", dup_count, len(clean_df))
    else:
        logger.info("Zero duplicate records found.")

    # 2. Missing value handling
    null_counts = clean_df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if not cols_with_nulls.empty:
        logger.warning("Columns containing missing values:\n%s", cols_with_nulls.to_dict())
        if fill_missing:
            for col in clean_df.columns:
                if clean_df[col].isnull().any():
                    if pd.api.types.is_numeric_dtype(clean_df[col]):
                        med_val = clean_df[col].median()
                        clean_df[col] = clean_df[col].fillna(med_val)
                        logger.info("Imputed missing values in '%s' with median (%s).", col, med_val)
                    else:
                        mode_val = clean_df[col].mode().iloc[0] if not clean_df[col].mode().empty else "UNKNOWN"
                        clean_df[col] = clean_df[col].fillna(mode_val)
                        logger.info("Imputed missing values in '%s' with mode ('%s').", col, mode_val)
    else:
        logger.info("Zero missing values detected in dataset.")

    return clean_df


def identify_feature_types(
    df: pd.DataFrame,
    target_col: str = "isFraud",
    exclude_identifiers: bool = True
) -> Tuple[List[str], List[str]]:
    """
    Categorizes input features into numerical and categorical candidate subsets.

    Args:
        df: Input DataFrame.
        target_col: Target label column name to exclude.
        exclude_identifiers: Whether to filter out high-cardinality IDs (e.g. nameOrig, nameDest).

    Returns:
        Tuple of (numerical_features, categorical_features).
    """
    excluded = {target_col, "isFlaggedFraud"}
    if exclude_identifiers:
        excluded.update({"nameOrig", "nameDest"})

    candidate_cols = [c for c in df.columns if c not in excluded]

    num_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in candidate_cols if not pd.api.types.is_numeric_dtype(df[c])]

    logger.info("Feature categorization: %d numerical, %d categorical.", len(num_cols), len(cat_cols))
    return num_cols, cat_cols


def separate_features_target(
    df: pd.DataFrame,
    target_col: str = "isFraud",
    drop_identifiers: bool = True
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Separates predictor matrix X from target vector y.

    Args:
        df: Input cleaned DataFrame.
        target_col: Target classification label.
        drop_identifiers: Exclude raw account IDs (nameOrig, nameDest) from X.

    Returns:
        Tuple of (X: pd.DataFrame, y: pd.Series).
    """
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not present in DataFrame.")

    cols_to_drop = [target_col]
    if "isFlaggedFraud" in df.columns:
        cols_to_drop.append("isFlaggedFraud")
    if drop_identifiers:
        for id_col in ["nameOrig", "nameDest"]:
            if id_col in df.columns:
                cols_to_drop.append(id_col)

    X = df.drop(columns=cols_to_drop, errors="ignore")
    y = df[target_col].astype(int)

    logger.info("Separated features X (shape: %s) and target y (len: %d).", X.shape, len(y))
    return X, y


def analyze_class_imbalance(y: pd.Series) -> Dict[str, Any]:
    """
    Analyzes class frequencies and calculates balanced class weighting to address imbalance.

    Args:
        y: Ground-truth target series (binary: 0 and 1).

    Returns:
        Dictionary with count, percentages, ratio, and balanced class weights.
    """
    counts = y.value_counts().to_dict()
    total = len(y)
    n_legit = counts.get(0, 0)
    n_fraud = counts.get(1, 0)

    fraud_percentage = (n_fraud / total * 100.0) if total > 0 else 0.0
    imbalance_ratio = (n_legit / n_fraud) if n_fraud > 0 else float("inf")

    # Compute balanced class weights via scikit-learn
    classes = np.array([0, 1])
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    class_weights_dict = {int(c): float(round(w, 4)) for c, w in zip(classes, weights)}

    metrics = {
        "total_samples": total,
        "legitimate_count": n_legit,
        "fraudulent_count": n_fraud,
        "fraud_percentage": round(fraud_percentage, 2),
        "imbalance_ratio": round(imbalance_ratio, 2),
        "class_weights": class_weights_dict
    }

    logger.info("Class imbalance analysis: Legit=%d, Fraud=%d (%.2f%%). Ratio=%.2f:1. Weights=%s",
                n_legit, n_fraud, fraud_percentage, imbalance_ratio, class_weights_dict)
    return metrics


def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Splits features and target into reproducible training and testing partitions
    using stratified sampling to preserve the exact fraud ratio in both sets.

    Args:
        X: Feature matrix.
        y: Target series.
        test_size: Proportion for testing (default: 0.20 = 20%).
        random_state: Seed for reproducibility.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    logger.info("Splitting dataset into train (%.0f%%) and test (%.0f%%) using stratified split (seed=%d)...",
                (1.0 - test_size) * 100, test_size * 100, random_state)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    logger.info("Split completed: Train shape=%s (Fraud: %d, %.2f%%), Test shape=%s (Fraud: %d, %.2f%%)",
                X_train.shape, int(y_train.sum()), y_train.mean() * 100,
                X_test.shape, int(y_test.sum()), y_test.mean() * 100)

    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    # Standalone execution for verification
    data = load_dataset()
    valid, errs = validate_dataset(data)
    cleaned = clean_dataset(data)
    num_f, cat_f = identify_feature_types(cleaned)
    X, y = separate_features_target(cleaned)
    imbalance = analyze_class_imbalance(y)
    X_train, X_test, y_train, y_test = split_data(X, y)
    print("\nData loader verification complete.")
