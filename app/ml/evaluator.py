"""
Model Evaluation and Diagnostic Subsystem
-----------------------------------------
Computes comprehensive classification metrics on unseen test partitions,
generates confusion matrices and ROC curves, and persists evaluation reports
in structured JSON/CSV formats alongside publication-ready visualization charts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    average_precision_score,
    confusion_matrix,
    classification_report
)

# Use non-interactive backend for cross-platform headless rendering
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger("fraud_detection.evaluator")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def evaluate_single_model(
    name: str,
    model: BaseEstimator,
    X_test: np.ndarray,
    y_test: pd.Series
) -> Dict[str, Any]:
    """
    Evaluates a trained classifier on unseen test data and calculates detailed metrics.

    Args:
        name: Name/identifier of the model.
        model: Trained scikit-learn estimator.
        X_test: Preprocessed test feature matrix.
        y_test: Ground-truth target labels.

    Returns:
        Dictionary containing scalar metrics, confusion matrix, and ROC curve coordinates.
    """
    logger.info("Evaluating model '%s' on %d test instances...", name, len(y_test))

    # Binary class predictions
    y_pred = model.predict(X_test)

    # Class probability estimates
    has_proba = False
    y_prob = None
    if hasattr(model, "predict_proba"):
        try:
            probs = model.predict_proba(X_test)
            y_prob = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
            has_proba = True
        except Exception as e:
            logger.warning("Failed to obtain predict_proba for %s: %s", name, e)
    elif hasattr(model, "decision_function"):
        try:
            scores = model.decision_function(X_test)
            # Min-max normalize scores to [0, 1] range for ROC computation
            min_s, max_s = scores.min(), scores.max()
            y_prob = (scores - min_s) / (max_s - min_s + 1e-9)
            has_proba = True
        except Exception as e:
            logger.warning("Failed to obtain decision_function for %s: %s", name, e)

    # Scalar evaluation metrics
    acc = float(accuracy_score(y_test, y_pred))
    bal_acc = float(balanced_accuracy_score(y_test, y_pred))
    prec_fraud = float(precision_score(y_test, y_pred, pos_label=1, zero_division=0))
    rec_fraud = float(recall_score(y_test, y_pred, pos_label=1, zero_division=0))
    f1_fraud = float(f1_score(y_test, y_pred, pos_label=1, zero_division=0))

    prec_macro = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    # ROC-AUC & PR-AUC
    roc_auc = None
    pr_auc = None
    roc_curve_data = {}

    if has_proba and y_prob is not None:
        try:
            roc_auc = float(roc_auc_score(y_test, y_prob))
            pr_auc = float(average_precision_score(y_test, y_prob))
            fpr, tpr, thresh = roc_curve(y_test, y_prob)
            roc_curve_data = {
                "fpr": [float(x) for x in fpr],
                "tpr": [float(x) for x in tpr],
                "thresholds": [float(x) for x in thresh]
            }
        except Exception as e:
            logger.warning("ROC calculation failed for %s: %s", name, e)

    # Confusion matrix: [[TN, FP], [FN, TP]]
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]

    cm_data = {
        "raw": [[tn, fp], [fn, tp]],
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    }

    result = {
        "model_name": name,
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "fraud_precision": round(prec_fraud, 4),
        "fraud_recall": round(rec_fraud, 4),
        "fraud_f1": round(f1_fraud, 4),
        "macro_precision": round(prec_macro, 4),
        "macro_recall": round(rec_macro, 4),
        "macro_f1": round(f1_macro, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "confusion_matrix": cm_data,
        "roc_curve": roc_curve_data
    }

    logger.info(
        "Model %s -> Accuracy: %.2f%% | Fraud Prec: %.4f | Fraud Rec: %.4f | Fraud F1: %.4f | ROC-AUC: %s",
        name, acc * 100, prec_fraud, rec_fraud, f1_fraud,
        f"{roc_auc:.4f}" if roc_auc is not None else "N/A"
    )
    return result


def generate_comparison_table(eval_results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Assembles a pandas DataFrame comparing key metrics across all evaluated models.

    Args:
        eval_results: Dict mapping model name to evaluation result dictionary.

    Returns:
        pd.DataFrame sorted with key evaluation metrics.
    """
    rows = []
    for model_name, res in eval_results.items():
        rows.append({
            "Model": model_name,
            "Accuracy": res["accuracy"],
            "Balanced_Accuracy": res["balanced_accuracy"],
            "Fraud_Precision": res["fraud_precision"],
            "Fraud_Recall": res["fraud_recall"],
            "Fraud_F1": res["fraud_f1"],
            "ROC_AUC": res["roc_auc"] if res["roc_auc"] is not None else np.nan,
            "PR_AUC": res["pr_auc"] if res["pr_auc"] is not None else np.nan,
            "TP": res["confusion_matrix"]["true_positives"],
            "FP": res["confusion_matrix"]["false_positives"],
            "TN": res["confusion_matrix"]["true_negatives"],
            "FN": res["confusion_matrix"]["false_negatives"]
        })

    df = pd.DataFrame(rows)
    return df


def plot_confusion_matrices(eval_results: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    """
    Plots a multi-panel grid of annotated confusion matrices for all candidate models.

    Args:
        eval_results: Model evaluation results dictionary.
        output_path: Destination PNG filepath.
    """
    n_models = len(eval_results)
    if n_models == 0:
        return

    cols = min(3, n_models)
    rows = int(np.ceil(n_models / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4.5 * rows), squeeze=False)
    model_names = list(eval_results.keys())

    for idx, name in enumerate(model_names):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        cm_raw = np.array(eval_results[name]["confusion_matrix"]["raw"])

        # Heatmap display
        cax = ax.matshow(cm_raw, cmap=plt.cm.Blues, alpha=0.85)
        for i in range(2):
            for j in range(2):
                val = cm_raw[i, j]
                text_color = "white" if val > cm_raw.max() / 2 else "black"
                label = f"{val}\n({'TN' if (i==0 and j==0) else 'FP' if (i==0 and j==1) else 'FN' if (i==1 and j==0) else 'TP'})"
                ax.text(j, i, label, ha="center", va="center", color=text_color, fontsize=12, fontweight="bold")

        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Legit", "Fraud"], fontsize=10)
        ax.set_yticklabels(["Legit", "Fraud"], fontsize=10)
        ax.set_xlabel("Predicted Label", fontsize=11, fontweight="medium")
        ax.set_ylabel("True Ground Truth", fontsize=11, fontweight="medium")
        f1_val = eval_results[name]["fraud_f1"]
        ax.set_title(f"{name}\n(Fraud F1: {f1_val:.4f})", fontsize=12, fontweight="bold", pad=12)

    # Hide unused subplots
    for idx in range(n_models, rows * cols):
        r, c = divmod(idx, cols)
        fig.delaxes(axes[r][c])

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved confusion matrix visualization to: %s", output_path)


def plot_roc_curves(eval_results: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    """
    Overlays Receiver Operating Characteristic (ROC) curves with AUC benchmarks.

    Args:
        eval_results: Model evaluation results dictionary.
        output_path: Destination PNG filepath.
    """
    plt.figure(figsize=(8, 6))

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    color_idx = 0

    for name, res in eval_results.items():
        roc_data = res.get("roc_curve", {})
        fpr = roc_data.get("fpr", [])
        tpr = roc_data.get("tpr", [])
        auc_val = res.get("roc_auc")

        if fpr and tpr and auc_val is not None:
            plt.plot(
                fpr, tpr,
                label=f"{name} (AUC = {auc_val:.4f})",
                color=colors[color_idx % len(colors)],
                linewidth=2.2
            )
            color_idx += 1

    # Diagonal no-skill line
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random Classifier (AUC = 0.5000)", alpha=0.8)
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="medium")
    plt.ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=11, fontweight="medium")
    plt.title("ROC Curves Comparison - Financial Fraud Detection", fontsize=13, fontweight="bold", pad=12)
    plt.legend(loc="lower right", fontsize=10, frameon=True)
    plt.grid(True, linestyle=":", alpha=0.6)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("Saved ROC curves visualization to: %s", output_path)


def plot_metrics_comparison(comparison_df: pd.DataFrame, output_path: Path) -> None:
    """
    Generates a grouped bar chart comparing Accuracy, Precision, Recall, F1, and ROC-AUC.

    Args:
        comparison_df: Comparison metrics DataFrame.
        output_path: Destination PNG filepath.
    """
    metrics_to_plot = ["Fraud_Precision", "Fraud_Recall", "Fraud_F1", "ROC_AUC"]
    available_metrics = [m for m in metrics_to_plot if m in comparison_df.columns]

    models = comparison_df["Model"].tolist()
    x = np.arange(len(models))
    width = 0.18

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ["#2b5c8f", "#d95f02", "#1b9e77", "#7570b3"]
    for i, metric in enumerate(available_metrics):
        values = comparison_df[metric].fillna(0.0).tolist()
        offset = (i - len(available_metrics) / 2 + 0.5) * width
        rects = ax.bar(x + offset, values, width, label=metric.replace("_", " "), color=colors[i % len(colors)], alpha=0.9)
        # Value labels above bars
        for rect in rects:
            h = rect.get_height()
            if h > 0.05:
                ax.annotate(f"{h:.2f}",
                            xy=(rect.get_x() + rect.get_width() / 2, h),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=8, rotation=45)

    ax.set_ylabel("Score (0.0 to 1.0)", fontsize=11, fontweight="medium")
    ax.set_title("Comparative Performance Across Key Fraud Detection Metrics", fontsize=13, fontweight="bold", pad=14)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=10, fontweight="medium", rotation=15)
    ax.set_ylim(0, 1.15)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved metrics comparison visualization to: %s", output_path)


def save_evaluation_artifacts(
    eval_results: Dict[str, Dict[str, Any]],
    output_dir: Path
) -> Tuple[Path, Path]:
    """
    Saves evaluation summaries to JSON and CSV formats and generates visual plots.

    Args:
        eval_results: Model evaluation results dictionary.
        output_dir: Directory where artifacts and reports are persisted.

    Returns:
        Tuple of (json_path, csv_path).
    """
    output_dir = Path(output_dir)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Comparison DataFrame & CSV
    comparison_df = generate_comparison_table(eval_results)
    csv_path = output_dir / "model_comparison.csv"
    comparison_df.to_csv(csv_path, index=False)
    logger.info("Saved model comparison table to: %s", csv_path)

    # 2. Complete JSON Report (strip large arrays for light-weight main JSON, save detailed arrays in reports/)
    main_summary = {
        model_name: {
            k: v for k, v in res.items() if k not in ["roc_curve"]
        }
        for model_name, res in eval_results.items()
    }
    json_path = output_dir / "model_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(main_summary, f, indent=2)
    logger.info("Saved model comparison JSON to: %s", json_path)

    # 3. Detailed ROC data JSON
    roc_data = {
        model_name: res.get("roc_curve", {})
        for model_name, res in eval_results.items()
    }
    roc_json_path = reports_dir / "roc_curves.json"
    with open(roc_json_path, "w", encoding="utf-8") as f:
        json.dump(roc_data, f, indent=2)

    # 4. Detailed Confusion Matrix JSON
    cm_data = {
        model_name: res.get("confusion_matrix", {})
        for model_name, res in eval_results.items()
    }
    cm_json_path = reports_dir / "confusion_matrices.json"
    with open(cm_json_path, "w", encoding="utf-8") as f:
        json.dump(cm_data, f, indent=2)

    # 5. Visual plots
    try:
        plot_confusion_matrices(eval_results, reports_dir / "confusion_matrix.png")
        plot_roc_curves(eval_results, reports_dir / "roc_curves.png")
        plot_metrics_comparison(comparison_df, reports_dir / "metrics_comparison.png")
    except Exception as e:
        logger.error("Failed to generate visual evaluation plots: %s", e)

    return json_path, csv_path
