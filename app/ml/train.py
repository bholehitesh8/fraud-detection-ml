"""
Machine Learning Training and Model Comparison Pipeline
-------------------------------------------------------
End-to-end, modular, and cross-platform training orchestrator that:
1. Ingests, validates, and cleans the real financial transaction dataset.
2. Performs a reproducible, stratified train/test split.
3. Fits the feature engineering and ColumnTransformer pipeline strictly on
   the training set to prevent data leakage.
4. Trains multiple supervised classifiers with class-imbalance compensation.
5. Evaluates all models across precision, recall, f1, accuracy, and ROC-AUC.
6. Generates confusion matrices, ROC curves, and structured comparison reports.
7. Selects the winning model based on a documented metric-based decision rule
   (prioritizing Fraud F1-Score over misleading accuracy).
8. Persists the selected model, candidate models, and all preprocessing artifacts.

Usage:
    python -m app.ml.train
    python app/ml/train.py
    python app/ml/train.py --data data/raw/online_fraud_dataset.csv --metric fraud_f1
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import joblib

# Ensure workspace root is on sys.path for direct script or module execution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.ml.data_loader import (
    load_dataset,
    validate_dataset,
    clean_dataset,
    separate_features_target,
    analyze_class_imbalance,
    split_data
)
from app.ml.preprocessor import DataPreprocessorPipeline
from app.ml.models import get_candidate_models, MODEL_METADATA
from app.ml.evaluator import evaluate_single_model, save_evaluation_artifacts
from app.ml.model_selector import select_best_model, save_best_model_metadata

logger = logging.getLogger("fraud_detection.train")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def run_training_pipeline(
    data_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    primary_metric: str = "fraud_f1",
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Executes end-to-end ML model training, evaluation, comparison, selection,
    and artifact serialization.

    Args:
        data_path: Path to CSV dataset (defaults to data/raw/online_fraud_dataset.csv).
        output_dir: Destination directory for artifacts (defaults to saved_models/).
        primary_metric: Primary selection metric (defaults to 'fraud_f1').
        random_state: Seed for reproducibility across splits and models.

    Returns:
        Dictionary containing pipeline execution summary, metrics, and artifact paths.
    """
    start_total_time = time.time()
    dest_dir = Path(output_dir) if output_dir else ROOT_DIR / "saved_models"
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir = dest_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("      Online Transaction Fraud Detection - ML Training & Comparison Pipeline")
    print("=" * 80)

    # 1. Dataset Loading
    csv_path = Path(data_path) if data_path else None
    logger.info("Step 1/8: Loading dataset...")
    df = load_dataset(csv_path)

    # 2. Schema Validation
    logger.info("Step 2/8: Validating dataset schema...")
    is_valid, issues = validate_dataset(df)
    if not is_valid:
        raise ValueError(f"Dataset failed validation checks: {issues}")

    # 3. Data Cleaning (Deduplication & Imputation)
    logger.info("Step 3/8: Cleaning records and resolving anomalies...")
    cleaned_df = clean_dataset(df, drop_duplicates=True, fill_missing=True)

    # 4. Feature and Target Separation
    X, y = separate_features_target(cleaned_df, target_col="isFraud")

    # 5. Class Imbalance Analysis
    imbalance_info = analyze_class_imbalance(y)
    print(f"\n[*] Dataset Diagnostics:")
    print(f"    - Total Records     : {imbalance_info['total_samples']:,}")
    print(f"    - Legitimate (0)    : {imbalance_info['legitimate_count']:,} ({100 - imbalance_info['fraud_percentage']:.2f}%)")
    print(f"    - Fraudulent (1)    : {imbalance_info['fraudulent_count']:,} ({imbalance_info['fraud_percentage']:.2f}%)")
    print(f"    - Imbalance Ratio   : {imbalance_info['imbalance_ratio']}:1")
    print(f"    - Computed Weights  : {imbalance_info['class_weights']}")

    # 6. Stratified Train/Test Split (Prevent Data Leakage)
    logger.info("Step 4/8: Performing stratified train/test split (80/20)...")
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.20, random_state=random_state)

    # 7. Fit Preprocessor Pipeline Strictly on Train Set
    logger.info("Step 5/8: Fitting preprocessor pipeline on training data...")
    preprocessor = DataPreprocessorPipeline(scaler_type="robust")
    X_train_transformed = preprocessor.fit_transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    # Persist Preprocessor Artifacts
    preprocessor_pipeline_path = dest_dir / "preprocessor_pipeline.joblib"
    preprocessor_meta_path = dest_dir / "pipeline_metadata.json"
    preprocessor.save(preprocessor_pipeline_path, preprocessor_meta_path)

    n_features = X_train_transformed.shape[1]
    print(f"\n[*] Engineered Features : {n_features} features generated after ColumnTransformer")
    print(f"[*] Training partition  : {X_train_transformed.shape[0]:,} samples")
    print(f"[*] Testing partition   : {X_test_transformed.shape[0]:,} samples")

    # 8. Train & Evaluate Candidate Classification Models
    logger.info("Step 6/8: Initializing and training candidate classifiers...")
    candidate_models = get_candidate_models(random_state=random_state)
    eval_results: Dict[str, Dict[str, Any]] = {}
    trained_models: Dict[str, Any] = {}

    print("\n" + "-" * 80)
    print(f"{'Model Name':<24} | {'Train Time':<10} | {'Accuracy':<9} | {'Fraud F1':<9} | {'Fraud Rec':<9} | {'ROC-AUC':<8}")
    print("-" * 80)

    for name, model in candidate_models.items():
        t0 = time.time()
        model.fit(X_train_transformed, y_train)
        train_duration = time.time() - t0
        trained_models[name] = model

        # Serialize candidate model
        candidate_file = candidates_dir / f"{name}.joblib"
        joblib.dump(model, candidate_file)

        # Evaluate on unseen test partition
        res = evaluate_single_model(name, model, X_test_transformed, y_test)
        res["train_time_seconds"] = round(train_duration, 3)
        eval_results[name] = res

        roc_str = f"{res['roc_auc']:.4f}" if res['roc_auc'] is not None else "N/A"
        print(f"{name:<24} | {train_duration:>8.2f}s | {res['accuracy']*100:>7.2f}% | {res['fraud_f1']:>9.4f} | {res['fraud_recall']:>9.4f} | {roc_str:>8}")

    print("-" * 80)

    # 9. Save Evaluation Artifacts (JSON, CSV, Plots)
    logger.info("Step 7/8: Generating comparison tables and diagnostic plots...")
    json_summary_path, csv_summary_path = save_evaluation_artifacts(eval_results, dest_dir)

    # 10. Metric-Driven Best Model Selection
    logger.info("Step 8/8: Selecting best model based on rule (Primary: %s)...", primary_metric)
    selection_meta = select_best_model(eval_results, primary_metric=primary_metric)
    best_model_name = selection_meta["selected_model_name"]
    best_model = trained_models[best_model_name]

    # Save Selected Model as primary backend artifact
    selected_model_path = dest_dir / "fraud_model.joblib"
    joblib.dump(best_model, selected_model_path)
    logger.info("Selected model '%s' saved to primary path: %s", best_model_name, selected_model_path)

    # Save selection metadata
    best_meta_path = dest_dir / "best_model_meta.json"
    save_best_model_metadata(selection_meta, best_meta_path)

    total_duration = time.time() - start_total_time

    # Print Final Summary
    print("\n" + "=" * 80)
    print("                         TRAINING PIPELINE SUMMARY")
    print("=" * 80)
    print(f"[*] Winning Model       : {best_model_name}")
    print(f"[*] Selection Metric    : {primary_metric} = {selection_meta['metrics']['fraud_f1']:.4f}")
    print(f"[*] Fraud Precision     : {selection_meta['metrics']['fraud_precision']:.4f}")
    print(f"[*] Fraud Recall        : {selection_meta['metrics']['fraud_recall']:.4f}")
    print(f"[*] ROC-AUC Score       : {selection_meta['metrics']['roc_auc']}")
    print(f"[*] Overall Accuracy    : {selection_meta['metrics']['accuracy'] * 100:.2f}%")
    print(f"[*] Total Pipeline Time : {total_duration:.2f} seconds")
    print(f"[*] Artifacts Persisted :")
    print(f"    - Winning Model     : {selected_model_path}")
    print(f"    - Preprocessor      : {preprocessor_pipeline_path}")
    print(f"    - Pipeline Metadata : {preprocessor_meta_path}")
    print(f"    - Selection Meta    : {best_meta_path}")
    print(f"    - Comparison CSV    : {csv_summary_path}")
    print(f"    - Comparison JSON   : {json_summary_path}")
    print(f"    - Reports Directory : {dest_dir / 'reports'}")
    print("=" * 80 + "\n")

    return {
        "dataset_records": len(df),
        "dataset_features": X.shape[1],
        "engineered_features": n_features,
        "models_trained": list(candidate_models.keys()),
        "selected_model": best_model_name,
        "selection_meta": selection_meta,
        "eval_results": eval_results,
        "artifact_paths": {
            "model": selected_model_path,
            "preprocessor": preprocessor_pipeline_path,
            "metadata": preprocessor_meta_path,
            "best_meta": best_meta_path,
            "comparison_csv": csv_summary_path,
            "comparison_json": json_summary_path,
            "reports_dir": dest_dir / "reports"
        }
    }


def train_model(data_path: Optional[str] = None, output_path: Optional[str] = None):
    """
    Backward-compatible entry point that wraps run_training_pipeline.
    """
    result = run_training_pipeline(data_path=data_path)
    if output_path:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(joblib.load(result["artifact_paths"]["model"]), target_path)
        return target_path
    return result["artifact_paths"]["model"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="End-to-end Machine Learning Training and Comparison Pipeline for Online Fraud Detection"
    )
    parser.add_argument("--data", type=str, default=None, help="Path to raw CSV dataset")
    parser.add_argument("--output-dir", type=str, default=None, help="Destination directory for model artifacts")
    parser.add_argument(
        "--metric",
        type=str,
        default="fraud_f1",
        choices=["fraud_f1", "roc_auc", "fraud_recall", "fraud_precision", "balanced_accuracy"],
        help="Primary metric used to select best model (default: fraud_f1)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")

    args = parser.parse_args()
    run_training_pipeline(
        data_path=args.data,
        output_dir=args.output_dir,
        primary_metric=args.metric,
        random_state=args.seed
    )
