"""
Machine Learning Model Registry and Factory
-------------------------------------------
Defines candidate classification algorithms for financial fraud detection,
configured with balanced class weighting to handle class imbalance,
reproducible random seeds, and regularization to mitigate overfitting.
"""

from typing import Dict, Any
from sklearn.base import BaseEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier,
    ExtraTreesClassifier
)


# Algorithmic justifications and metadata for academic reporting
MODEL_METADATA = {
    "LogisticRegression": {
        "name": "Logistic Regression",
        "category": "Linear Classifier",
        "description": "L2-regularized linear model with balanced class weighting. Serves as an interpretable baseline.",
        "imbalance_handling": "class_weight='balanced' inversely scales inverse frequencies.",
        "supports_probabilities": True
    },
    "DecisionTree": {
        "name": "Decision Tree",
        "category": "Tree-based Classifier",
        "description": "Single decision tree with depth bounding (max_depth=10) and minimum sample constraints to mitigate overfitting.",
        "imbalance_handling": "class_weight='balanced' calculates split impurity with class frequencies.",
        "supports_probabilities": True
    },
    "RandomForest": {
        "name": "Random Forest",
        "category": "Bagging Ensemble",
        "description": "Ensemble of 100 decorrelated decision trees with balanced bootstrap sampling. Excellent resilience to variance.",
        "imbalance_handling": "class_weight='balanced' weights each bootstrap sample.",
        "supports_probabilities": True
    },
    "HistGradientBoosting": {
        "name": "Hist Gradient Boosting",
        "category": "Boosting Ensemble",
        "description": "Histogram-binned gradient boosted decision trees. Highly effective on non-linear numerical boundaries.",
        "imbalance_handling": "class_weight='balanced' automatically weights sample gradients.",
        "supports_probabilities": True
    },
    "ExtraTrees": {
        "name": "Extra Trees (Extremely Randomized Trees)",
        "category": "Randomized Bagging Ensemble",
        "description": "Ensemble of 100 randomized trees with randomized split thresholds. Offers superior regularization on noisy financial records.",
        "imbalance_handling": "class_weight='balanced' penalizes minority misclassification.",
        "supports_probabilities": True
    }
}


def get_candidate_models(random_state: int = 42) -> Dict[str, BaseEstimator]:
    """
    Returns a dictionary of candidate classification models configured for
    imbalanced financial fraud detection.

    Args:
        random_state: Seed for pseudo-random number generation for reproducibility.

    Returns:
        Dict mapping model key string to un-fitted scikit-learn estimator instance.
    """
    models: Dict[str, BaseEstimator] = {
        "LogisticRegression": LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=1000,
            random_state=random_state,
            solver="lbfgs"
        ),
        "DecisionTree": DecisionTreeClassifier(
            criterion="gini",
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=random_state
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=14,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=8,
            learning_rate=0.1,
            class_weight="balanced",
            random_state=random_state
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=100,
            max_depth=14,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1
        )
    }

    return models
