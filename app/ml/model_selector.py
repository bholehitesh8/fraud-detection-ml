"""
Metric-Driven Model Selection Subsystem
---------------------------------------
Selects the winning classification algorithm using a documented,
academically rigorous metric-based rule tailored for imbalanced fraud detection.

Selection Rule:
1. Primary Metric: Fraud Class F1-Score (Minority Class 1).
   - High Accuracy is rejected as a primary selection metric because on an imbalanced
     dataset (~3.5% fraud), a trivial model predicting all transactions as legitimate
     would achieve ~96.5% Accuracy while capturing zero fraudulent activity (0% Recall, 0% F1).
   - F1-Score represents the harmonic mean of Precision and Recall, directly balancing
     the operational cost of missed fraud (false negatives) with customer friction from
     false declines (false positives).
2. Secondary Metric (Tie-Breaker): ROC-AUC Score.
   - Measures overall discriminative capability across all classification thresholds.
3. Tertiary Metric (Tie-Breaker): Fraud Recall.
   - When models exhibit comparable F1 and ROC-AUC, the classifier catching the highest
     proportion of actual fraud is prioritized.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger("fraud_detection.model_selector")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def select_best_model(
    eval_results: Dict[str, Dict[str, Any]],
    primary_metric: str = "fraud_f1",
    tie_breaker_metric: str = "roc_auc"
) -> Dict[str, Any]:
    """
    Applies multi-criteria decision rule to select the optimal fraud classification model.

    Args:
        eval_results: Dictionary of evaluation results keyed by model identifier.
        primary_metric: Primary selection criterion (default: 'fraud_f1').
        tie_breaker_metric: Secondary criterion in case of primary score ties (default: 'roc_auc').

    Returns:
        Dictionary containing selected model identifier, selection rationale, and metadata.
    """
    if not eval_results:
        raise ValueError("Cannot select best model from empty evaluation results.")

    logger.info(
        "Applying selection rule -> Primary: %s, Secondary: %s, Tertiary: fraud_recall",
        primary_metric, tie_breaker_metric
    )

    def sort_key(item: Tuple[str, Dict[str, Any]]):
        name, res = item
        primary_val = res.get(primary_metric, 0.0) or 0.0
        tie_breaker_val = res.get(tie_breaker_metric, 0.0) or 0.0
        recall_val = res.get("fraud_recall", 0.0) or 0.0
        return (primary_val, tie_breaker_val, recall_val)

    sorted_candidates = sorted(eval_results.items(), key=sort_key, reverse=True)
    best_name, best_metrics = sorted_candidates[0]

    rationale = (
        f"Selected '{best_name}' out of {len(eval_results)} candidate models based on "
        f"optimal {primary_metric.replace('_', ' ').title()} ({best_metrics.get(primary_metric):.4f}), "
        f"{tie_breaker_metric.replace('_', ' ').upper()} ({best_metrics.get(tie_breaker_metric, 'N/A')}), "
        f"and Fraud Recall ({best_metrics.get('fraud_recall'):.4f}). "
        f"Accuracy alone ({best_metrics.get('accuracy') * 100:.2f}%) was not used as the decision criterion "
        f"due to severe class imbalance."
    )

    selection_meta = {
        "selected_model_name": best_name,
        "selection_rule": {
            "primary_metric": primary_metric,
            "tie_breaker_metric": tie_breaker_metric,
            "tertiary_metric": "fraud_recall",
            "justification": (
                "Fraud detection demands high sensitivity to rare positive events (~3.5% fraud) "
                "while minimizing false customer declines. F1-score balances precision and recall, "
                "surpassing accuracy which is misleading in imbalanced financial data."
            )
        },
        "metrics": {
            "accuracy": best_metrics.get("accuracy"),
            "balanced_accuracy": best_metrics.get("balanced_accuracy"),
            "fraud_precision": best_metrics.get("fraud_precision"),
            "fraud_recall": best_metrics.get("fraud_recall"),
            "fraud_f1": best_metrics.get("fraud_f1"),
            "roc_auc": best_metrics.get("roc_auc"),
            "pr_auc": best_metrics.get("pr_auc"),
            "confusion_matrix": best_metrics.get("confusion_matrix")
        },
        "rationale": rationale,
        "ranked_candidates": [
            {
                "rank": idx + 1,
                "model_name": name,
                primary_metric: res.get(primary_metric),
                tie_breaker_metric: res.get(tie_breaker_metric),
                "fraud_recall": res.get("fraud_recall"),
                "accuracy": res.get("accuracy")
            }
            for idx, (name, res) in enumerate(sorted_candidates)
        ],
        "selection_timestamp": datetime.now().isoformat()
    }

    logger.info("Winner: %s (Fraud F1=%.4f, ROC-AUC=%s, Fraud Recall=%.4f)",
                best_name,
                best_metrics.get(primary_metric, 0.0),
                best_metrics.get(tie_breaker_metric, "N/A"),
                best_metrics.get("fraud_recall", 0.0))
    return selection_meta


def save_best_model_metadata(metadata: Dict[str, Any], output_path: Path) -> Path:
    """
    Serializes best model metadata to JSON on disk.

    Args:
        metadata: Selection metadata dictionary.
        output_path: Path object for destination JSON.

    Returns:
        Path to written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved best model metadata to: %s", output_path)
    return output_path
