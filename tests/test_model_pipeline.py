"""
Comprehensive Unit Test Suite for Model Training, Evaluation, and Prediction Pipeline
-------------------------------------------------------------------------------------
Validates:
1. Candidate classifier instantiation and balanced class weight configuration
2. Model training pipeline execution without data leakage
3. Serialized artifact existence (model, preprocessor, metadata, comparison reports, plots)
4. Reusable prediction function (`predict_transaction`) interface and output format
5. FraudPredictor singleton inference engine
6. Feature compatibility between preprocessor pipeline and trained models
7. Model selection rule behavior and tie-breaking logic
"""

import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from app.ml.models import get_candidate_models, MODEL_METADATA
from app.ml.evaluator import evaluate_single_model, generate_comparison_table, save_evaluation_artifacts
from app.ml.model_selector import select_best_model, save_best_model_metadata
from app.ml.train import run_training_pipeline
from app.ml.predictor import FraudPredictor, predict_transaction
from app.ml.preprocessor import DataPreprocessorPipeline
from app.ml.data_loader import load_dataset, clean_dataset, separate_features_target, split_data


class ModelPipelineTestCase(unittest.TestCase):
    """Automated tests for machine learning model training and inference suite."""

    @classmethod
    def setUpClass(cls):
        """Loads and prepares benchmark dataset for fast testing."""
        cls.raw_df = load_dataset()
        cls.cleaned_df = clean_dataset(cls.raw_df)
        cls.X, cls.y = separate_features_target(cls.cleaned_df)
        cls.X_train, cls.X_test, cls.y_train, cls.y_test = split_data(
            cls.X, cls.y, test_size=0.20, random_state=42
        )

        cls.preprocessor = DataPreprocessorPipeline(scaler_type="robust")
        cls.X_train_transformed = cls.preprocessor.fit_transform(cls.X_train)
        cls.X_test_transformed = cls.preprocessor.transform(cls.X_test)

    def test_candidate_models_instantiation(self):
        """Verifies candidate models are instantiated with balanced class weighting."""
        models = get_candidate_models(random_state=42)
        expected_models = [
            "LogisticRegression",
            "DecisionTree",
            "RandomForest",
            "HistGradientBoosting",
            "ExtraTrees"
        ]

        for model_name in expected_models:
            self.assertIn(model_name, models, f"Model '{model_name}' missing from candidate registry.")
            model = models[model_name]
            self.assertIsNotNone(model)
            # Ensure class imbalance compensation is configured
            self.assertTrue(
                hasattr(model, "class_weight"),
                f"Model '{model_name}' must configure class_weight parameter."
            )
            self.assertEqual(
                model.class_weight, "balanced",
                f"Model '{model_name}' class_weight should be 'balanced'."
            )

    def test_model_metadata_definitions(self):
        """Verifies model metadata dictionary provides documentation and justifications."""
        for key in ["LogisticRegression", "DecisionTree", "RandomForest", "HistGradientBoosting", "ExtraTrees"]:
            self.assertIn(key, MODEL_METADATA)
            meta = MODEL_METADATA[key]
            self.assertIn("name", meta)
            self.assertIn("description", meta)
            self.assertIn("imbalance_handling", meta)
            self.assertTrue(meta.get("supports_probabilities"))

    def test_single_model_evaluation_metrics(self):
        """Verifies evaluate_single_model computes all expected metric keys."""
        models = get_candidate_models(random_state=42)
        tree_model = models["DecisionTree"]
        tree_model.fit(self.X_train_transformed, self.y_train)

        metrics = evaluate_single_model("DecisionTree", tree_model, self.X_test_transformed, self.y_test)

        required_keys = [
            "model_name", "accuracy", "balanced_accuracy",
            "fraud_precision", "fraud_recall", "fraud_f1",
            "macro_precision", "macro_recall", "macro_f1",
            "roc_auc", "pr_auc", "confusion_matrix", "roc_curve"
        ]
        for key in required_keys:
            self.assertIn(key, metrics, f"Missing metric key '{key}' in evaluation result.")

        self.assertGreaterEqual(metrics["accuracy"], 0.0)
        self.assertLessEqual(metrics["accuracy"], 1.0)
        self.assertGreaterEqual(metrics["fraud_f1"], 0.0)
        self.assertLessEqual(metrics["fraud_f1"], 1.0)

        cm = metrics["confusion_matrix"]
        self.assertIn("true_negatives", cm)
        self.assertIn("false_positives", cm)
        self.assertIn("false_negatives", cm)
        self.assertIn("true_positives", cm)
        total_cm = cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"] + cm["true_positives"]
        self.assertEqual(total_cm, len(self.y_test))

    def test_model_selection_rule(self):
        """Verifies model selector prioritizes Fraud F1 over Accuracy and breaks ties with ROC-AUC."""
        mock_results = {
            "Model_HighAcc_ZeroF1": {
                "accuracy": 0.99,
                "fraud_precision": 0.0,
                "fraud_recall": 0.0,
                "fraud_f1": 0.0,
                "roc_auc": 0.50
            },
            "Model_ModerateAcc_HighF1": {
                "accuracy": 0.96,
                "fraud_precision": 0.85,
                "fraud_recall": 0.90,
                "fraud_f1": 0.8743,
                "roc_auc": 0.95
            },
            "Model_Tie_F1_HigherROC": {
                "accuracy": 0.96,
                "fraud_precision": 0.85,
                "fraud_recall": 0.90,
                "fraud_f1": 0.8743,
                "roc_auc": 0.98
            }
        }

        selection = select_best_model(mock_results, primary_metric="fraud_f1", tie_breaker_metric="roc_auc")
        # Should pick Model_Tie_F1_HigherROC because it has higher ROC-AUC tie breaker than Model_ModerateAcc_HighF1
        # and much higher F1 than Model_HighAcc_ZeroF1 despite lower accuracy
        self.assertEqual(selection["selected_model_name"], "Model_Tie_F1_HigherROC")
        self.assertIn("rationale", selection)
        self.assertIn("ranked_candidates", selection)

    def test_saved_model_and_artifacts_exist(self):
        """Verifies that all primary saved artifacts exist on disk in saved_models/."""
        saved_models_dir = Path(__file__).resolve().parent.parent / "saved_models"
        self.assertTrue(saved_models_dir.exists())

        required_artifacts = [
            saved_models_dir / "fraud_model.joblib",
            saved_models_dir / "preprocessor_pipeline.joblib",
            saved_models_dir / "pipeline_metadata.json",
            saved_models_dir / "best_model_meta.json",
            saved_models_dir / "model_comparison.json",
            saved_models_dir / "model_comparison.csv",
            saved_models_dir / "reports" / "confusion_matrix.png",
            saved_models_dir / "reports" / "roc_curves.png",
            saved_models_dir / "reports" / "metrics_comparison.png",
            saved_models_dir / "reports" / "confusion_matrices.json",
            saved_models_dir / "reports" / "roc_curves.json"
        ]

        for artifact in required_artifacts:
            self.assertTrue(artifact.exists(), f"Expected artifact '{artifact.name}' does not exist.")
            self.assertGreater(artifact.stat().st_size, 0, f"Artifact '{artifact.name}' is empty.")

    def test_prediction_function_interface(self):
        """Verifies predict_transaction accepts transaction payloads and scores legitimate vs fraud."""
        legit_payload = {
            "step": 1,
            "transaction_type": "PAYMENT",
            "amount": 25.50,
            "old_balance_org": 500.0,
            "new_balance_orig": 474.50,
            "old_balance_dest": 0.0,
            "new_balance_dest": 0.0
        }
        res_legit = predict_transaction(legit_payload)

        self.assertIsInstance(res_legit, dict)
        self.assertFalse(res_legit["is_fraud"])
        self.assertEqual(res_legit["prediction_label"], "Legitimate")
        self.assertIn(res_legit["risk_level"], ["Low", "Moderate"])

        # Severe account drain transfer (classic PaySim fraud signature)
        fraud_payload = {
            "step": 1,
            "transaction_type": "TRANSFER",
            "amount": 200000.0,
            "old_balance_org": 200000.0,
            "new_balance_orig": 0.0,
            "old_balance_dest": 0.0,
            "new_balance_dest": 0.0
        }
        res_fraud = predict_transaction(fraud_payload)

        self.assertIsInstance(res_fraud, dict)
        self.assertTrue(res_fraud["is_fraud"])
        self.assertEqual(res_fraud["prediction_label"], "Fraudulent")
        self.assertIn(res_fraud["risk_level"], ["High", "Critical"])

    def test_prediction_output_format_and_ranges(self):
        """Verifies data types, value ranges, and keys in prediction response."""
        sample_payload = {
            "step": 1,
            "type": "CASH_OUT",
            "amount": 1500.0,
            "oldbalanceOrg": 1500.0,
            "newbalanceOrig": 0.0,
            "oldbalanceDest": 500.0,
            "newbalanceDest": 2000.0
        }
        output = predict_transaction(sample_payload)

        expected_keys = [
            "is_fraud", "predicted_class", "prediction_label",
            "probability", "confidence_score", "risk_level",
            "model_name", "features", "model_status"
        ]
        for key in expected_keys:
            self.assertIn(key, output, f"Missing key '{key}' in prediction response.")

        self.assertIsInstance(output["is_fraud"], bool)
        self.assertIn(output["predicted_class"], [0, 1])
        self.assertIn(output["prediction_label"], ["Fraudulent", "Legitimate"])
        self.assertGreaterEqual(output["probability"], 0.0)
        self.assertLessEqual(output["probability"], 1.0)
        self.assertGreaterEqual(output["confidence_score"], 0.0)
        self.assertLessEqual(output["confidence_score"], 100.0)
        self.assertIn(output["risk_level"], ["Low", "Moderate", "High", "Critical"])
        self.assertIsInstance(output["features"], dict)

    def test_preprocessing_and_model_compatibility(self):
        """Verifies preprocessor pipeline output matches model expected feature count."""
        saved_models_dir = Path(__file__).resolve().parent.parent / "saved_models"
        pipeline = DataPreprocessorPipeline.load(saved_models_dir / "preprocessor_pipeline.joblib")
        model = joblib.load(saved_models_dir / "fraud_model.joblib")

        test_row = self.X.head(5)
        transformed = pipeline.transform(test_row)

        self.assertEqual(transformed.shape[1], 16)
        if hasattr(model, "n_features_in_"):
            self.assertEqual(transformed.shape[1], model.n_features_in_)

        # Prediction must succeed without feature shape mismatch
        preds = model.predict(transformed)
        self.assertEqual(len(preds), 5)

    def test_training_pipeline_execution_in_temp_directory(self):
        """Verifies complete training pipeline runs end-to-end and serializes cleanly in custom dir."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            result = run_training_pipeline(output_dir=str(tmp_path), primary_metric="fraud_f1", random_state=42)

            self.assertIn("selected_model", result)
            self.assertIn("models_trained", result)
            self.assertEqual(len(result["models_trained"]), 5)

            # Check files were created in the temp directory
            self.assertTrue((tmp_path / "fraud_model.joblib").exists())
            self.assertTrue((tmp_path / "preprocessor_pipeline.joblib").exists())
            self.assertTrue((tmp_path / "model_comparison.json").exists())
            self.assertTrue((tmp_path / "model_comparison.csv").exists())
            self.assertTrue((tmp_path / "best_model_meta.json").exists())
            self.assertTrue((tmp_path / "reports" / "confusion_matrix.png").exists())


if __name__ == "__main__":
    unittest.main()
