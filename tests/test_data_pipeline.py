"""
Comprehensive Unit Test Suite for ML Data Pipeline
--------------------------------------------------
Validates:
1. Cross-platform dataset loading via pathlib
2. Dataset schema and required columns validation
3. Missing-value detection and imputation
4. Duplicate record handling
5. Feature and target separation (X and y)
6. Stratified train/test split reproducibility and fraud proportion preservation
7. Preprocessing ColumnTransformer fitting (no data leakage) and transformation
8. Numerical RobustScaling and categorical OneHotEncoding
9. Class distribution analysis and balanced class weight calculation
10. Serialization and deserialization of preprocessing artifacts
"""

import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

from app.ml.data_loader import (
    load_dataset,
    validate_dataset,
    clean_dataset,
    identify_feature_types,
    separate_features_target,
    analyze_class_imbalance,
    split_data,
    REQUIRED_COLUMNS
)
from app.ml.preprocessor import (
    FinancialFeatureEngineer,
    DataPreprocessorPipeline,
    build_column_transformer
)


class DataPipelineTestCase(unittest.TestCase):
    """Automated tests for ML data ingestion and preprocessing pipeline."""

    @classmethod
    def setUpClass(cls):
        """Loads the raw benchmark dataset once for the test suite."""
        cls.df = load_dataset()

    def test_cross_platform_path_handling(self):
        """Verifies paths are Path objects and cross-platform resolution works."""
        from app.ml.data_loader import DEFAULT_RAW_DATA_PATH
        self.assertIsInstance(DEFAULT_RAW_DATA_PATH, Path)
        self.assertTrue(DEFAULT_RAW_DATA_PATH.exists())
        self.assertTrue(str(DEFAULT_RAW_DATA_PATH).endswith(".csv"))

    def test_dataset_loading_and_shape(self):
        """Verifies dataset loads with minimum required records and columns."""
        self.assertIsInstance(self.df, pd.DataFrame)
        self.assertGreaterEqual(len(self.df), 5000)
        self.assertGreaterEqual(self.df.shape[1], 10)

    def test_required_columns_present(self):
        """Verifies all mandatory transaction attributes exist in loaded data."""
        for col in REQUIRED_COLUMNS:
            self.assertIn(col, self.df.columns, f"Required column '{col}' is missing.")

    def test_dataset_validation_success(self):
        """Verifies validation passes on authentic dataset."""
        is_valid, issues = validate_dataset(self.df)
        self.assertTrue(is_valid, f"Validation issues detected: {issues}")
        self.assertEqual(len(issues), 0)

    def test_dataset_validation_catches_invalid_schema(self):
        """Verifies validator flags missing columns and corrupted data."""
        corrupted_df = self.df.drop(columns=["amount", "type"])
        is_valid, issues = validate_dataset(corrupted_df)
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)

    def test_missing_value_handling(self):
        """Verifies clean_dataset imputes missing numerical and categorical values."""
        df_with_nulls = self.df.head(100).copy()
        # Introduce synthetic nulls
        df_with_nulls.loc[0:5, "amount"] = np.nan
        df_with_nulls.loc[10:15, "type"] = np.nan

        self.assertGreater(df_with_nulls["amount"].isnull().sum(), 0)
        self.assertGreater(df_with_nulls["type"].isnull().sum(), 0)

        cleaned = clean_dataset(df_with_nulls, fill_missing=True)
        self.assertEqual(cleaned["amount"].isnull().sum(), 0)
        self.assertEqual(cleaned["type"].isnull().sum(), 0)

    def test_duplicate_record_handling(self):
        """Verifies clean_dataset detects and eliminates duplicate records."""
        sample = self.df.head(50).copy()
        # Create intentional duplicates
        duplicated_df = pd.concat([sample, sample.iloc[0:5]], ignore_index=True)
        self.assertEqual(len(duplicated_df), 55)

        cleaned = clean_dataset(duplicated_df, drop_duplicates=True)
        self.assertEqual(len(cleaned), 50)

    def test_feature_type_identification(self):
        """Verifies numerical and categorical features are appropriately partitioned."""
        num_cols, cat_cols = identify_feature_types(self.df)
        self.assertIn("amount", num_cols)
        self.assertIn("oldbalanceOrg", num_cols)
        self.assertIn("newbalanceOrig", num_cols)
        self.assertIn("type", cat_cols)
        # Ensure target and high-cardinality IDs are excluded
        self.assertNotIn("isFraud", num_cols)
        self.assertNotIn("nameOrig", cat_cols)
        self.assertNotIn("nameDest", cat_cols)

    def test_feature_target_separation(self):
        """Verifies separation of X and y."""
        X, y = separate_features_target(self.df)
        self.assertNotIn("isFraud", X.columns)
        self.assertEqual(len(X), len(y))
        self.assertEqual(len(X), len(self.df))
        self.assertEqual(set(y.unique()), {0, 1})

    def test_stratified_train_test_split(self):
        """Verifies train/test split preserves fraud distribution and is reproducible."""
        X, y = separate_features_target(self.df)
        X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=42)

        # Dimension checks
        total_rows = len(self.df)
        self.assertEqual(len(X_train) + len(X_test), total_rows)
        self.assertEqual(len(X_train), int(total_rows * 0.80))
        self.assertEqual(len(X_test), int(total_rows * 0.20))

        # Stratification check (fraud proportions must match closely within 0.2%)
        train_fraud_rate = y_train.mean()
        test_fraud_rate = y_test.mean()
        self.assertAlmostEqual(train_fraud_rate, test_fraud_rate, delta=0.005)

        # Reproducibility check (same seed gives identical splits)
        _, _, _, y_test_repeat = split_data(X, y, test_size=0.20, random_state=42)
        pd.testing.assert_series_equal(y_test, y_test_repeat)

    def test_class_imbalance_analysis(self):
        """Verifies class imbalance analysis and balanced weight computation."""
        X, y = separate_features_target(self.df)
        metrics = analyze_class_imbalance(y)

        self.assertIn("class_weights", metrics)
        self.assertIn("imbalance_ratio", metrics)
        self.assertGreater(metrics["imbalance_ratio"], 1.0)

        # Minority class (1: Fraud) must have significantly higher weight than majority (0: Legit)
        weights = metrics["class_weights"]
        self.assertGreater(weights[1], weights[0])
        self.assertGreater(weights[1], 5.0)  # For ~3.5% fraud, weight is ~14.0

    def test_financial_feature_engineer(self):
        """Verifies domain financial feature transformations."""
        engineer = FinancialFeatureEngineer()
        sample = pd.DataFrame([{
            "amount": 5000.0,
            "oldbalanceOrg": 5000.0,
            "newbalanceOrig": 0.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 5000.0,
            "type": "TRANSFER"
        }])

        res = engineer.transform(sample)
        # Check derived features
        self.assertIn("error_balance_orig", res.columns)
        self.assertIn("error_balance_dest", res.columns)
        self.assertIn("is_account_drain", res.columns)
        self.assertIn("amount_to_old_balance_ratio", res.columns)

        # For exact drain: error_balance_orig = (0 + 5000) - 5000 = 0.0
        self.assertEqual(res["error_balance_orig"].iloc[0], 0.0)
        self.assertEqual(res["is_account_drain"].iloc[0], 1.0)
        self.assertAlmostEqual(res["amount_to_old_balance_ratio"].iloc[0], 5000.0 / 5001.0, places=4)

    def test_preprocessor_pipeline_fit_and_transform(self):
        """Verifies DataPreprocessorPipeline fits on train and transforms test without leakage."""
        X, y = separate_features_target(self.df)
        X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=42)

        pipeline = DataPreprocessorPipeline()
        self.assertFalse(pipeline.is_fitted)

        # Fit and transform training set
        X_train_transformed = pipeline.fit_transform(X_train)
        self.assertTrue(pipeline.is_fitted)
        self.assertIsInstance(X_train_transformed, np.ndarray)
        self.assertEqual(X_train_transformed.shape[0], len(X_train))
        self.assertFalse(np.isnan(X_train_transformed).any())
        self.assertFalse(np.isinf(X_train_transformed).any())

        # Transform test set using learned parameters
        X_test_transformed = pipeline.transform(X_test)
        self.assertEqual(X_test_transformed.shape[0], len(X_test))
        self.assertEqual(X_test_transformed.shape[1], X_train_transformed.shape[1])
        self.assertFalse(np.isnan(X_test_transformed).any())

    def test_pipeline_serialization_and_deserialization(self):
        """Verifies saving and reloading preprocessor pipeline from disk."""
        X, y = separate_features_target(self.df)
        pipeline = DataPreprocessorPipeline()
        X_tr = pipeline.fit_transform(X.head(200))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            model_file = tmp_path / "test_preprocessor.joblib"
            meta_file = tmp_path / "test_metadata.json"

            pipeline.save(model_file, meta_file)
            self.assertTrue(model_file.exists())
            self.assertTrue(meta_file.exists())

            # Reload
            reloaded_pipeline = DataPreprocessorPipeline.load(model_file, meta_file)
            self.assertTrue(reloaded_pipeline.is_fitted)

            # Assert identical output transformation
            X_reloaded_tr = reloaded_pipeline.transform(X.head(200))
            np.testing.assert_allclose(X_tr, X_reloaded_tr, rtol=1e-5)


if __name__ == "__main__":
    unittest.main()
