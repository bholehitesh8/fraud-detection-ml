# Fraud Detection in Online Transactions using Machine Learning

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Backend-Flask%203.1-black.svg)](https://palletsprojects.com/p/flask/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![Database](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-135%20Passed-brightgreen.svg)](https://docs.python.org/3/library/unittest.html)

A diploma-level Machine Learning project that classifies financial transactions in real-time as **Legitimate** or **Fraudulent** using professional data preprocessing, multi-model classification, and metric-driven model selection.

---

## 📌 1. Project Overview

With the exponential surge in online banking, UPI, credit card payments, and digital wallets, financial fraud has become increasingly sophisticated. Conventional rule-based systems (e.g., fixed spending limits) trigger high false-alarm rates and cannot adapt to evolving attack patterns such as automated account draining and sudden cross-border cash-outs.

This project implements an end-to-end Machine Learning pipeline integrated with a responsive web application built using **Python Flask**, **SQLite**, and **Vanilla HTML/CSS/JavaScript**. Incoming transactions are preprocessed, analyzed by a trained supervised Machine Learning model, and saved into a local SQLite database for compliance auditing.

---

## 📊 2. Dataset Information & Schema

The project utilizes a domain-authentic financial transaction benchmark dataset modeled after the **PaySim mobile money financial transaction benchmark** (Lopez-Rojas et al., IEEE), simulating real-world operational logs of digital payment networks.

* **File Location:** `data/raw/online_fraud_dataset.csv`
* **Total Instances:** 6,000 transactions
* **Total Attributes:** 11 columns
* **Target Variable:** `isFraud` (Binary classification: `0` = Legitimate, `1` = Fraudulent)
* **Fraud Distribution:** 5,790 Legitimate (96.50%), 210 Fraudulent (3.50%)
* **Imbalance Ratio:** 27.57 : 1

### Attribute Description

| Attribute | Data Type | Role | Description |
| :--- | :--- | :--- | :--- |
| `step` | Integer | Numerical Feature | Simulation time unit (1 step = 1 hour; values range 1 to 744 hours / 30 days) |
| `type` | String | Categorical Feature | Transaction category: `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN` |
| `amount` | Float | Numerical Feature | Monetary value of the transaction in currency units |
| `nameOrig` | String | Identifier | Customer ID initiating the payment (e.g., `C1234567890`) |
| `oldbalanceOrg` | Float | Numerical Feature | Originating customer account balance prior to transaction |
| `newbalanceOrig` | Float | Numerical Feature | Originating customer account balance after transaction |
| `nameDest` | String | Identifier | Recipient identifier (`C...` for customer, `M...` for merchant) |
| `oldbalanceDest` | Float | Numerical Feature | Destination account balance prior to transaction |
| `newbalanceDest` | Float | Numerical Feature | Destination account balance after transaction |
| `isFraud` | Integer (0/1) | **Target Label** | Ground-truth classification: `1` = Fraudulent transaction, `0` = Legitimate |
| `isFlaggedFraud` | Integer (0/1) | Business Flag | Rule flag triggered on single transfers exceeding $200,000 |

---

## ⚙️ 3. Data Preprocessing & Feature Engineering Pipeline

All transformations are structured using reusable, modular scikit-learn components encapsulated in `app/ml/preprocessor.py` and `app/ml/data_loader.py`:

```
Raw CSV / Form Input
         │
         ▼
[ Data Validation & Integrity Check ] ──> Schema conformance, non-negativity check
         │
         ▼
[ Deduplication & Missing Imputation ] ──> Median (numerical), Mode (categorical)
         │
         ▼
[ FinancialFeatureEngineer ] ─────────> Computes domain financial anomaly indicators:
         │                              • error_balance_orig = (newbalanceOrig + amount) - oldbalanceOrg
         │                              • error_balance_dest = (oldbalanceDest + amount) - newbalanceDest
         │                              • balance_diff_orig  = oldbalanceOrg - newbalanceOrig
         │                              • amount_to_old_balance_ratio = amount / (oldbalanceOrg + 1.0)
         │                              • is_account_drain   = 1 if (new_orig == 0 and old_orig > 0)
         │
         ▼
[ Scikit-Learn ColumnTransformer ]
         ├── Numerical Features (11) ──> SimpleImputer(median) ──> RobustScaler()
         └── Categorical Feature (1) ───> SimpleImputer(mode)   ──> OneHotEncoder(sparse=False)
         │
         ▼
Fitted Pipeline Artifact (.joblib) ────> Serialized into saved_models/preprocessor_pipeline.joblib
```

### Why `RobustScaler`?
Financial transaction volumes follow heavy-tailed, exponential distributions with extreme outliers (e.g. transfers ranging from $5 to $500,000). Standard z-score scaling (`StandardScaler`) is severely biased by massive outliers because the sample mean and variance are inflated. `RobustScaler` uses the median and Interquartile Range (IQR: 25th to 75th percentile), ensuring consistent scaling immune to extreme values.

---

## ⚖️ 4. Class Imbalance Strategy & Data Leakage Prevention

In financial transaction systems, fraud represents a tiny fraction of activity (typically 0.1% to 5%).

### Strict Data Leakage Prevention
* **Stratified Splitting:** Partitioning (`split_data`) allocates 80% to training (4,800 samples) and 20% to testing (1,200 samples) using **stratified sampling**, ensuring both partitions have the exact same 3.50% fraud proportion without mixing records.
* **Leakage-Free Fitting:** The `DataPreprocessorPipeline` is strictly fitted on `X_train`. Scaling medians, IQRs, and one-hot categories are calculated only on training observations; the test partition (`X_test`) is transformed purely using the learned training parameters.

### Justified Imbalance Strategy: Balanced Class Weights
Rather than blindly applying synthetic oversampling (e.g., SMOTE) — which frequently produces unrealistic synthetic balance combinations that violate accounting equations — the pipeline utilizes **balanced class weights** calculated via:
$$W_j = \frac{N}{2 \times N_j}$$

* Legitimate Class Weight ($W_0$): **0.5181**
* Fraudulent Class Weight ($W_1$): **14.2857**

During training, the loss function penalizes false negatives on fraud instances 27.57 times more heavily than misclassifying standard transactions, optimizing sensitivity without synthetic feature distortion.

---

## 🤖 5. Machine Learning Models & Comparative Benchmark

The pipeline trains, tunes, and evaluates 5 supervised classification algorithms configured with balanced class weighting:

1. **Logistic Regression:** Regularized linear classifier serving as an interpretable statistical baseline.
2. **Decision Tree:** Single tree with maximum depth regularization (`max_depth=10`, `min_samples_split=10`) to prevent overfitting.
3. **Random Forest:** Bagging ensemble of 100 decorrelated decision trees with balanced bootstrap subsampling.
4. **HistGradientBoosting:** State-of-the-art histogram-binned gradient boosted trees offering fast execution and non-linear partition modeling.
5. **Extra Trees (Extremely Randomized Trees):** Ensemble of 100 randomized trees with randomized split cut-points, offering superior variance reduction on noisy financial numbers.

### Empirical Benchmark Results (Unseen Test Partition: $N=1,200$)

| Model | Overall Accuracy | Balanced Accuracy | Fraud Precision | Fraud Recall | Fraud F1-Score | ROC-AUC | PR-AUC | False Positives | False Negatives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ExtraTrees** *(Selected)* | **100.00%** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0** | **0** |
| **RandomForest** | 99.92% | 0.9996 | 0.9767 | 1.0000 | 0.9882 | 1.0000 | 1.0000 | 1 | 0 |
| **HistGradientBoosting** | 99.75% | 0.9872 | 0.9535 | 0.9762 | 0.9647 | 0.9999 | 0.9984 | 2 | 1 |
| **LogisticRegression** | 99.67% | 0.9983 | 0.9130 | 1.0000 | 0.9545 | 0.9999 | 0.9983 | 4 | 0 |
| **DecisionTree** | 99.67% | 0.9868 | 0.9318 | 0.9762 | 0.9535 | 0.9876 | 0.9516 | 3 | 1 |

---

## 🎯 6. Model Selection Rule & Evaluation Criteria

### Why Accuracy Alone is Rejected
In highly imbalanced datasets (~3.5% fraud), a trivial model predicting all transactions as legitimate achieves **96.50% Accuracy** while failing to intercept even a single fraud attempt (**0% Recall, 0% F1**).

### Selection Rule Architecture
The automated selection engine (`app/ml/model_selector.py`) applies a multi-criteria decision hierarchy:
1. **Primary Metric — Fraud Class F1-Score:** Maximizes the harmonic mean of Precision and Recall on minority class `1`, balancing fraud detection rate against customer disruption.
2. **Secondary Metric (Tie-Breaker) — ROC-AUC Score:** Assesses discriminatory threshold separation across all operating points.
3. **Tertiary Metric (Tie-Breaker) — Fraud Recall:** Prioritizes catching every fraudulent dollar if F1 and ROC-AUC are identical.

**Winner:** `ExtraTrees` achieved the highest F1-Score (1.0000) and ROC-AUC (1.0000) on the test partition, capturing 100% of fraud (42/42) with zero false declines (0 FP). It is serialized as `saved_models/fraud_model.joblib`.

---

## 💾 7. Serialized Artifacts & Generated Reports

The pipeline saves structured data and visual charts into `saved_models/`:

```
saved_models/
├── fraud_model.joblib            # Selected winning model (ExtraTrees)
├── preprocessor_pipeline.joblib  # Fitted Scikit-Learn ColumnTransformer pipeline
├── pipeline_metadata.json        # Preprocessing feature metadata & scaling parameters
├── best_model_meta.json          # Winning model selection rationale & metrics
├── model_comparison.json         # Complete JSON summary of all candidate models
├── model_comparison.csv          # Comparative metrics table across all models
├── candidates/                   # Serialized candidate models
│   ├── DecisionTree.joblib
│   ├── ExtraTrees.joblib
│   ├── HistGradientBoosting.joblib
│   ├── LogisticRegression.joblib
│   └── RandomForest.joblib
└── reports/                      # Diagnostic plots & raw curve points
    ├── confusion_matrix.png      # Multi-panel confusion matrix grid
    ├── roc_curves.png            # Overlaid ROC curves with individual AUC scores
    ├── metrics_comparison.png    # Comparative bar chart across key metrics
    ├── confusion_matrices.json   # Raw TN, FP, FN, TP values
    └── roc_curves.json           # Raw FPR, TPR, and threshold coordinates
```

---

## 🏗️ 8. Project Architecture & Directory Structure

```
fraud_detection_ml/
│
├── app/                              # Core Flask Application Package
│   ├── __init__.py                   # Application Factory (create_app), DB bindings, Blueprints
│   ├── config.py                     # Environment configurations (Dev, Testing, Prod)
│   │
│   ├── models/                       # SQLite Database Models (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── transaction.py            # Transaction and ML audit log schema
│   │   └── migrator.py               # Idempotent SQLite schema migration & backfill
│   │
│   ├── routes/                       # Modular Blueprints
│   │   ├── __init__.py
│   │   ├── main_routes.py            # Home (/), Dashboard (/dashboard), About (/about)
│   │   ├── transaction_routes.py     # Evaluation & Prediction UI (/predict)
│   │   └── api_routes.py             # Programmatic JSON REST API (/api/health, /api/predict)
│   │
│   ├── ml/                           # Machine Learning Subsystem
│   │   ├── __init__.py               # Subsystem package exports
│   │   ├── data_loader.py            # Dataset loading, validation, and stratified splitting
│   │   ├── preprocessor.py           # Feature engineering & ColumnTransformer pipeline
│   │   ├── models.py                 # Candidate models registry & configurations
│   │   ├── evaluator.py              # Multi-metric evaluation, diagnostic plots, and report saving
│   │   ├── model_selector.py         # Metric-driven selection rule implementation
│   │   ├── prediction_service.py     # In-memory cached model inference & currency normalization
│   │   ├── predictor.py              # Reusable prediction module (predict_transaction & FraudPredictor)
│   │   └── train.py                  # End-to-end ML training & comparison pipeline CLI
│   ├── services/                     # Business Logic & Safe Data Access Layer
│   │   ├── __init__.py
│   │   └── prediction_repository.py  # Safe DB transactions, pagination, filters, sorting
│   │
│   ├── utils/                        # Helper Utilities
│   │   ├── __init__.py
│   │   ├── currency.py               # ISO 4217 currency validation & conversion rates
│   │   ├── validator.py              # Schema, numeric & categorical payload validator
│   │   └── helpers.py                # Risk tiering, account masking, general helpers
│   │
│   ├── static/                       # Frontend Assets
│   │   ├── css/style.css             # Modern responsive design system
│   │   └── js/main.js                # Preset autofill & client validation
│   │
│   └── templates/                    # Jinja2 HTML Templates
│       ├── base.html                 # Master layout template
│       ├── index.html                # Project landing page
│       ├── predict.html              # Transaction evaluation form
│       ├── dashboard.html            # Audit history and metrics
│       └── about.html                # Viva presentation & architecture docs
│
├── data/                             # Data Storage
│   ├── generate_dataset.py           # Reproducible benchmark dataset generator
│   ├── raw/
│   │   └── online_fraud_dataset.csv  # 6,000 transaction records benchmark
│   └── processed/                    # Cleaned feature sets (.gitkeep)
│
├── saved_models/                     # Serialized Model Artifacts & Reports
│   ├── fraud_model.joblib            # Selected winning classifier
│   ├── preprocessor_pipeline.joblib  # Fitted preprocessing pipeline
│   ├── pipeline_metadata.json        # Preprocessing metadata
│   ├── best_model_meta.json          # Best model selection metadata
│   ├── model_comparison.json         # Complete JSON metrics
│   ├── model_comparison.csv          # CSV comparison table
│   ├── candidates/                   # Candidate model files (.joblib)
│   └── reports/                      # PNG visualizations & JSON curve coordinates
│
├── instance/                         # SQLite Database Storage
│   └── fraud_detection_dev.db        # SQLite database
│
├── tests/                            # Automated Test Suite (63 Tests)
│   ├── __init__.py
│   ├── test_basic.py                 # Route, DB, and Web API unit tests (12 tests)
│   ├── test_data_pipeline.py         # Ingestion, schema, splitting & preprocessor tests (14 tests)
│   ├── test_model_pipeline.py        # Model training, comparison, prediction & compatibility tests (9 tests)
│   ├── test_api.py                   # Production API health, predictions, currency & error tests (13 tests)
│   └── test_prediction_history.py    # Database history, pagination, filtering, schema migration (15 tests)
│
├── run.py                            # Flask application entry point
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── .gitignore                        # Git exclusion rules
└── README.md                         # Project documentation
```

---

## 🚀 9. How to Train the Models & Run Predictions

### Step 1: Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 2: Run the Model Training & Comparison Pipeline
Executes data ingestion, validation, stratified splitting, preprocessing, model training across all 5 algorithms, evaluation, plot generation, and best model selection:

```powershell
# Standard execution (cross-platform: Windows / macOS / Linux)
python -m app.ml.train

# Or using custom data path and primary metric
python -m app.ml.train --data data/raw/online_fraud_dataset.csv --metric fraud_f1
```

**Available CLI Options:**
* `--data <path>`: Custom CSV dataset path.
* `--output-dir <path>`: Custom directory for model artifacts (defaults to `saved_models/`).
* `--metric <name>`: Selection metric (`fraud_f1`, `roc_auc`, `fraud_recall`, `fraud_precision`, `balanced_accuracy`).
* `--seed <int>`: Random seed for split and estimators (default: `42`).

---

### Step 3: Run Programmatic Predictions

You can make predictions from any Python script or external service using the reusable `predict_transaction` function:

```python
from app.ml.predictor import predict_transaction

# Example 1: Legitimate utility payment
legit_tx = {
    "step": 1,
    "transaction_type": "PAYMENT",
    "amount": 85.50,
    "old_balance_org": 2500.0,
    "new_balance_orig": 2414.50,
    "old_balance_dest": 0.0,
    "new_balance_dest": 0.0
}
result = predict_transaction(legit_tx)
print("Legitimate Transaction Score:")
print(f"  Class       : {result['prediction_label']}")
print(f"  Probability : {result['probability']:.4f}")
print(f"  Risk Level  : {result['risk_level']}")

# Example 2: High-risk account drain transfer
fraud_tx = {
    "step": 1,
    "transaction_type": "TRANSFER",
    "amount": 200000.0,
    "old_balance_org": 200000.0,
    "new_balance_orig": 0.0,
    "old_balance_dest": 0.0,
    "new_balance_dest": 0.0
}
fraud_result = predict_transaction(fraud_tx)
print("\nFraudulent Transaction Score:")
print(f"  Class       : {fraud_result['prediction_label']}")
print(f"  Probability : {fraud_result['probability']:.4f}")
print(f"  Risk Level  : {fraud_result['risk_level']}")
```

**Prediction Output Format:**
```json
{
  "is_fraud": false,
  "predicted_class": 0,
  "prediction_label": "Legitimate",
  "probability": 0.0,
  "confidence_score": 0.0,
  "risk_level": "Low",
  "model_name": "ExtraTrees",
  "features": {
    "amount": 85.5,
    "old_balance_org": 2500.0,
    "new_balance_orig": 2414.5,
    "balance_diff_orig": 85.5,
    "amount_ratio": 0.03418632546981208,
    "error_balance_orig": 0.0,
    "type_PAYMENT": 1.0
  },
  "model_status": "Active trained model (ExtraTrees) & Preprocessor Pipeline"
}
```

---

### Step 4: Run the Complete Test Suite (63 Tests)
```powershell
python -m unittest discover -s tests -v
```

All 63 unit and integration tests validate:
1. Basic routes, database transactions, and Web UI routes (12 tests in `test_basic.py`)
2. Ingestion schema, missing values, duplicates, and feature preprocessing (14 tests in `test_data_pipeline.py`)
3. Model training execution, artifact existence, prediction function, formatting, and compatibility (9 tests in `test_model_pipeline.py`)
4. Production REST API health, predictions, ISO 4217 currencies, validation, error handling, and CORS (13 tests in `test_api.py`)
5. Database persistence, prediction history query, filtering, sorting, pagination, and schema migration (15 tests in `test_prediction_history.py`)

---

### Step 5: Start the Flask Web Application
```powershell
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 📡 10. Production REST API Documentation

The system provides a production-ready, modular REST API (`app/routes/api_routes.py`) backed by the cached in-memory `PredictionService` (`app/ml/prediction_service.py`), eliminating model reload latency on live transactions.

### Endpoints Overview

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Diagnostic readiness check for API, DB, model, and artifacts | 200 (Healthy), 500 (Degraded) |
| `POST` | `/api/predict` | Real-time transaction fraud evaluation with ISO 4217 currency support & auto-persistence | 200 (Success), 400 (Invalid), 500 (Error) |
| `GET` | `/api/predictions` | Query paginated prediction history with multi-attribute filtering & sorting | 200 (Success), 400 (Invalid), 500 (Error) |
| `GET` | `/api/predictions/<id>` | Retrieve single prediction record by integer ID or transaction reference string | 200 (Success), 404 (Not Found), 500 (Error) |
| `GET` | `/api/stats` | Aggregated transaction KPIs from audit database | 200 (Success), 500 (Error) |
| `OPTIONS` | `/api/*` | Preflight CORS compliance checks | 204 (No Content) |

---

### `GET /api/health`
Returns system diagnostics, database connection status, ML model loading state, and individual artifact availability on disk:

```json
{
  "status": "healthy",
  "service": "Fraud Detection ML API",
  "version": "1.0.0",
  "api_running": true,
  "database": "connected",
  "ml_model_loaded": true,
  "preprocessor_loaded": true,
  "artifacts_available": true,
  "artifacts": {
    "model_file": {"path": ".../saved_models/fraud_model.joblib", "exists": true},
    "preprocessor_file": {"path": ".../saved_models/preprocessor_pipeline.joblib", "exists": true},
    "metadata_file": {"path": ".../saved_models/pipeline_metadata.json", "exists": true}
  },
  "model_details": {
    "name": "ExtraTrees",
    "version": "1.0.0",
    "algorithm": "ExtraTreesClassifier",
    "engineered_feature_count": 16
  },
  "timestamp": "2026-09-17T02:05:00Z"
}
```

---

### `POST /api/predict`
Accepts a JSON payload representing a financial transaction, validates all constraints, normalizes currency, runs feature engineering, and scores fraud risk.

#### Request JSON Schema
```json
{
  "amount": 85000.00,
  "transaction_type": "TRANSFER",
  "old_balance_org": 85000.00,
  "new_balance_orig": 0.00,
  "old_balance_dest": 0.00,
  "new_balance_dest": 85000.00,
  "currency": "INR",
  "step": 1,
  "sender_account": "AC-9988776655",
  "receiver_account": "AC-1122334455"
}
```

* **Required Fields:** `amount` (float > 0), `transaction_type` (`PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN`).
* **Multi-Currency:** `currency` accepts any 3-letter ISO 4217 code (e.g. `INR`, `USD`, `EUR`, `GBP`, `AED`, `JPY`, `CAD`, `AUD`, `SGD`, etc.). Reference rates normalize foreign values into USD for model scoring while returning both original and converted values.
* **Optional Balances:** `old_balance_org`, `new_balance_orig`, `old_balance_dest`, `new_balance_dest` (floats $\ge 0$, default `0.0`).
* **Optional Metadata:** `step` (float $\ge 1$, default `1.0`), `sender_account`, `receiver_account`, `device_type`, `location`.

#### Success Response (HTTP 200)
```json
{
  "status": "success",
  "transaction_ref": "TXN-B4F29D1A",
  "is_fraud": true,
  "predicted_class": 1,
  "prediction_label": "Fraudulent",
  "fraud_probability": 0.9967,
  "confidence_score": 99.67,
  "risk_level": "Critical",
  "currency": "INR",
  "original_amount": 85000.0,
  "normalized_amount_usd": 1017.96,
  "exchange_rate": 83.5,
  "model_info": {
    "name": "ExtraTrees",
    "version": "1.0.0",
    "algorithm": "ExtraTreesClassifier"
  },
  "model_status": "Active trained model (ExtraTrees) & Preprocessor Pipeline",
  "validation_status": "Passed",
  "timestamp": "2026-09-17T02:05:01.123456+00:00",
  "latency_ms": 78.42
}
```

#### Validation Error Response (HTTP 400)
Returned when payload fails numeric constraints, missing required fields, or invalid currency format:
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Transaction validation failed.",
  "errors": [
    "Field 'amount' must be a positive number greater than 0.",
    "Invalid currency code '123'. Must be a valid 3-letter ISO 4217 code (e.g., INR, USD, EUR, GBP, AED, JPY, CAD, AUD)."
  ],
  "timestamp": "2026-09-17T02:05:02.000000+00:00"
}
```

#### Server / Artifact Error Response (HTTP 500)
Returned with clean diagnostic information if ML artifacts are missing or unreadable without crashing the server:
```json
{
  "status": "error",
  "error_type": "ModelArtifactError",
  "message": "Machine learning prediction service is currently unavailable.",
  "details": "Model artifact file not found at saved_models/fraud_model.joblib",
  "timestamp": "2026-09-17T02:05:03.000000+00:00"
}
```

#### Security & Privacy (Safe Logging)
All account numbers are masked before persistence in SQLite and terminal logs (e.g. `******7890`). Raw account numbers and personal data are never logged or exposed.

---

## 🗄️ 11. Database & Prediction History Architecture (Prompt 5)

The application utilizes a local, production-hardened **SQLite** database managed via **Flask-SQLAlchemy ORM** (`instance/fraud_detection_dev.db`).

### Schema & Entity Design (`Transaction` / `Prediction`)
The `Transaction` model (also accessible via aliases `Prediction` and `TransactionHistory`) stores the complete operational audit trail for every scored transaction:

| Column | Type | Index | Description |
| :--- | :--- | :---: | :--- |
| `id` | Integer | Primary Key | Auto-incrementing unique record ID |
| `transaction_ref` | String(64) | Yes (Unique) | Formatted transaction reference (e.g., `TXN-A1B2C3D4`) |
| `transaction_type` | String(20) | No | `PAYMENT`, `TRANSFER`, `CASH_OUT`, `DEBIT`, `CASH_IN` |
| `amount` | Float | No | Transaction amount in original currency |
| `currency` | String(3) | Yes | ISO 4217 currency code (e.g. `INR`, `USD`, `EUR`, `GBP`) |
| `normalized_amount` | Float | No | Converted transaction amount normalized to USD |
| `exchange_rate` | Float | No | Currency conversion multiplier applied at inference |
| `old_balance_org` | Float | No | Originating balance before transaction |
| `new_balance_orig` | Float | No | Originating balance after transaction |
| `old_balance_dest` | Float | No | Recipient balance before transaction |
| `new_balance_dest` | Float | No | Recipient balance after transaction |
| `step` | Float | No | Simulation time unit (1 step = 1 hour) |
| `is_fraud` | Boolean | Yes | Binary classification outcome (`True` = Fraud, `False` = Legitimate) |
| `prediction_label` | String(32) | No | Human-readable classification (`Fraudulent` vs `Legitimate`) |
| `fraud_probability` | Float | No | Exact minority fraud probability score ($0.0 \dots 1.0$) |
| `confidence_score` | Float | No | Confidence percentage ($0.0 \dots 100.0\%$) |
| `risk_level` | String(20) | No | Categorical risk grade (`Low`, `Medium`, `High`, `Critical`) |
| `status` | String(20) | No | Transaction status (`fraudulent` or `legitimate`) |
| `model_name` | String(64) | No | Name of ML model generating inference (e.g., `ExtraTrees`) |
| `model_version` | String(20) | No | Pipeline version tag (e.g., `1.0.0`) |
| `sender_account` | String(64) | No | Masked originator account number (e.g., `******7890`) |
| `receiver_account` | String(64) | No | Masked recipient account number (e.g., `******1234`) |
| `created_at` | DateTime | Yes | UTC record creation timestamp |
| `prediction_timestamp` | DateTime | No | Exact UTC timestamp when ML scoring occurred |

### Automatic Persistence & Transaction Safety
Every incoming transaction evaluated via `POST /api/predict` is automatically recorded via `app.services.prediction_repository.create_prediction_record`:
* **Atomicity:** All database changes execute in a single unit of work (`db.session.commit()`).
* **Safe Rollbacks:** In case of database lock, disk full, or write errors, the repository triggers `db.session.rollback()` and bubbles a clean error. The API returns **HTTP 500** with an error explanation rather than falsely claiming the record was saved.
* **Privacy by Design:** Originating and destination account numbers are masked (`******7890`) prior to persistence.

---

### `GET /api/predictions`
Retrieve paginated prediction records with filtering, searching, and allow-listed sorting.

#### Query Parameters

| Parameter | Type | Default | Constraints | Description |
| :--- | :--- | :---: | :--- | :--- |
| `page` | integer | `1` | $\ge 1$ | Target pagination page number |
| `per_page` | integer | `20` | $1 \dots 100$ | Number of records returned per page |
| `status` | string | `None` | `fraud`, `safe`, `fraudulent`, `legitimate` | Filter by fraud status |
| `currency` | string | `None` | 3-letter ISO 4217 | Filter by currency code (case-insensitive) |
| `ref` | string | `None` | substring | Filter by partial or exact transaction reference |
| `start_date` | string | `None` | ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`) | Records created on or after date |
| `end_date` | string | `None` | ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`) | Records created on or before date |
| `sort_by` | string | `created_at` | `id`, `created_at`, `amount`, `risk_level`, `confidence_score`, `prediction_timestamp` | Safe allow-listed sort field |
| `sort_dir` | string | `desc` | `asc`, `desc` | Sort direction |

#### Example Request:
```powershell
curl -X GET "http://127.0.0.1:5000/api/predictions?page=1&per_page=10&status=fraud&currency=EUR&sort_by=amount&sort_dir=desc"
```

#### Example Response (HTTP 200):
```json
{
  "status": "success",
  "data": [
    {
      "id": 42,
      "transaction_ref": "TXN-FB4CD9A8",
      "transaction_type": "TRANSFER",
      "amount": 25000.0,
      "currency": "EUR",
      "normalized_amount": 27173.91,
      "exchange_rate": 0.92,
      "is_fraud": true,
      "prediction_label": "Fraudulent",
      "fraud_probability": 0.9967,
      "confidence_score": 99.67,
      "risk_level": "Critical",
      "status": "fraudulent",
      "model_name": "ExtraTrees",
      "model_version": "1.0.0",
      "sender_account": "******7890",
      "receiver_account": "******1234",
      "created_at": "2026-09-17T02:15:00.000000Z",
      "prediction_timestamp": "2026-09-17T02:15:00.000000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_records": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### `GET /api/predictions/<identifier>`
Retrieves a single prediction record by integer database `id` or string `transaction_ref`.

#### Example Request:
```powershell
curl -X GET "http://127.0.0.1:5000/api/predictions/TXN-FB4CD9A8"
# Or by integer ID:
curl -X GET "http://127.0.0.1:5000/api/predictions/42"
```

#### Success Response (HTTP 200):
```json
{
  "status": "success",
  "data": {
    "id": 42,
    "transaction_ref": "TXN-FB4CD9A8",
    "transaction_type": "TRANSFER",
    "amount": 25000.0,
    "currency": "EUR",
    "normalized_amount": 27173.91,
    "exchange_rate": 0.92,
    "old_balance_org": 25000.0,
    "new_balance_orig": 0.0,
    "old_balance_dest": 0.0,
    "new_balance_dest": 25000.0,
    "step": 1.0,
    "is_fraud": true,
    "prediction_label": "Fraudulent",
    "fraud_probability": 0.9967,
    "confidence_score": 99.67,
    "risk_level": "Critical",
    "status": "fraudulent",
    "model_name": "ExtraTrees",
    "model_version": "1.0.0",
    "sender_account": "******7890",
    "receiver_account": "******1234",
    "created_at": "2026-09-17T02:15:00.000000Z",
    "prediction_timestamp": "2026-09-17T02:15:00.000000Z"
  }
}
```

#### Not Found Response (HTTP 404):
```json
{
  "status": "error",
  "error_type": "NotFoundError",
  "message": "Prediction record with identifier 'TXN-NOTFOUND' not found.",
  "timestamp": "2026-09-17T02:15:05.000000Z"
}
```

---

## 🎓 12. Viva Voce Defense Questions & Answers

1. **Why is Accuracy an invalid metric for evaluating fraud detection models?**  
   *Answer:* Financial transactions suffer from extreme class imbalance (here, 96.5% legitimate and 3.5% fraud). A degenerate model that always predicts class `0` (legitimate) achieves a 96.5% accuracy rate while missing 100% of fraudulent attacks (Recall = 0%, F1 = 0%). Therefore, **Fraud F1-Score** (harmonic mean of Precision and Recall) and **ROC-AUC** are the mathematically valid criteria for model evaluation and selection.

2. **Why use Extra Trees (Extremely Randomized Trees) over a Standard Decision Tree?**  
   *Answer:* A single decision tree suffers from high variance and quickly overfits training noise. Extra Trees builds an ensemble of 100 decorrelated trees with random split thresholds, reducing both variance and bias on heavy-tailed financial transaction distributions.

3. **How does the system mitigate class imbalance without generating fake data via SMOTE?**  
   *Answer:* Financial transaction attributes are bound by strict accounting balance equations (e.g. $NewBalance = OldBalance \pm Amount$). Naive synthetic oversampling (SMOTE) generates interpolated synthetic data that violates accounting equations and produces unrealistic artifacts. Instead, we use **balanced class weights** ($W_{fraud} = 14.2857$), inversely penalizing minority classification mistakes without distorting real-world feature dynamics.

4. **What is Data Leakage and how is it prevented in this pipeline?**  
   *Answer:* Data leakage occurs when statistics or distributions from the test partition contaminate the training stage (e.g., computing scalers or imputation on the entire dataset). We isolate the test split using stratified sampling *before* preprocessing, and fit the `DataPreprocessorPipeline` strictly on `X_train`. `X_test` is transformed solely using parameters learned from `X_train`.

5. **Why is `RobustScaler` preferred over `StandardScaler` for transaction amounts?**  
   *Answer:* Financial transactions feature extreme power-law outliers (e.g. $10 payments vs $500,000 corporate transfers). `StandardScaler` relies on mean and standard deviation, which are skewed by extreme outliers. `RobustScaler` scales using the median and Interquartile Range (IQR = $Q_3 - Q_1$), providing outlier-resistant scaling.

6. **Why use SQLite with Flask-SQLAlchemy instead of flat files or an external database cluster?**  
   *Answer:* SQLite is a serverless, zero-configuration, ACID-compliant database that lives directly within the project's `instance/` folder, ensuring complete cross-platform portability across Windows, macOS, and Linux without external network daemon setup. Flask-SQLAlchemy provides an Object Relational Mapper (ORM) that abstracts SQL dialect differences, parameterizes queries to prevent SQL injection, and supports seamless migration to PostgreSQL or MySQL in production enterprise environments.

7. **How does the database indexing strategy optimize prediction history queries?**  
   *Answer:* B-tree indexes are placed on `transaction_ref` (unique index for $O(\log N)$ lookup by reference string), `is_fraud` and `currency` (for fast categorical filtering), and `created_at` (for time-series filtering and ordered pagination without expensive full table scans).

8. **How does the API handle database write failures safely?**  
   *Answer:* Database writes are wrapped in an atomic unit of work inside `prediction_repository.create_prediction_record`. If a failure occurs (such as disk lock or disk full), `db.session.rollback()` is immediately executed to clear corrupted session state, and the API returns **HTTP 500** with an error message, preventing inconsistent partial state or falsely informing the client that the record was audited.

---

## 🔐 13. Authentication & User Management (Prompt 8)

The application includes an enterprise-grade, secure **Authentication & Role-Based Access Control (RBAC)** system that integrates with the machine learning prediction and audit pipeline while keeping model inference and historical data fully protected.

### Security Architecture

* **Password Hashing:** Implemented using `werkzeug.security` with constant-time verification (`scrypt` / `pbkdf2:sha256`). Plaintext passwords and hashes are never exposed in API payloads, serialized models, or log streams.
* **Session Management:** Encrypted server-side sessions with `HttpOnly`, `SameSite=Lax`, and configurable `SESSION_COOKIE_SECURE` cookie attributes.
* **Database Model (`User`):** Idempotently managed in SQLite alongside the audit ledger with indexed `username` and `email` uniqueness constraints.
* **Zero Disruption Migration:** Idempotent database upgrade logic detects existing tables, safely applies schema indexes, and preserves 100% of historical transactions and analytics.

### Pre-Configured Evaluation Accounts

For immediate testing, demonstration, and Viva Voce defense, the system automatically initializes two seed accounts if the identity store is unpopulated:

| Role | Username | Email | Default Password | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin@fraudguard.local` | `AdminPassword123!` | Full system access, audit ledger, telemetry, and user management (`/admin/users`) |
| **Fraud Analyst** | `analyst` | `analyst@fraudguard.local` | `AnalystPassword123!` | Transaction evaluation (`/predict`), audit log (`/dashboard`), analytics, and detail inspection |

> **Security Note:** Default passwords can be overridden via environment variables `DEFAULT_ADMIN_PASSWORD` and `DEFAULT_ANALYST_PASSWORD`.

### Role-Based Access Control (RBAC) Matrix

| Endpoint / Page | Public | Analyst | Administrator |
| :--- | :---: | :---: | :---: |
| `GET /` (Home Landing Page) | ✅ | ✅ | ✅ |
| `GET /about` (Viva & Architecture Guide) | ✅ | ✅ | ✅ |
| `GET /api/health` (System Readiness Diagnostics) | ✅ | ✅ | ✅ |
| `GET /login`, `POST /login` (Sign In) | ✅ | ✅ | ✅ |
| `GET /register`, `POST /register` (Analyst Onboarding) | ✅ | ✅ | ✅ |
| `GET /logout` (Session Termination) | ❌ | ✅ | ✅ |
| `GET /dashboard` (Transaction Audit Ledger) | ❌ (Redirects) | ✅ | ✅ |
| `GET /predict`, `POST /predict` (ML Inference) | ❌ (Redirects) | ✅ | ✅ |
| `POST /api/predict` (Real-Time Scoring API) | ❌ (401) | ✅ | ✅ |
| `GET /api/predictions` (Paginated Query API) | ❌ (401) | ✅ | ✅ |
| `GET /api/analytics/summary` (Analytics API) | ❌ (401) | ✅ | ✅ |
| `GET /admin/users` (User Administration Portal) | ❌ (Redirects) | ❌ (403 Forbidden) | ✅ |
| `POST /admin/users/create` (Provision User) | ❌ (Redirects) | ❌ (403 Forbidden) | ✅ |
| `POST /admin/users/<id>/toggle-status` | ❌ (Redirects) | ❌ (403 Forbidden) | ✅ |

### REST Authentication Endpoints

#### 1. Current User Status
* **Endpoint:** `GET /api/auth/me`
* **Response (Authenticated):**
  ```json
  {
    "authenticated": true,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@fraudguard.local",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-09-19 01:25:00 UTC",
      "last_login": "2026-09-19 01:44:53 UTC"
    }
  }
  ```
* **Response (Unauthenticated):**
  ```json
  {
    "authenticated": false,
    "user": null
  }
  ```

#### 2. JSON API Login & Logout
* **Login:** `POST /api/auth/login` with `{"identifier": "admin", "password": "AdminPassword123!"}`
* **Logout:** `POST /api/auth/logout`

### Running the Application & Automated Tests

#### Start Flask Development Server:
```powershell
python run.py
```
Visit **http://127.0.0.1:5000** in your browser.

#### Execute Complete Test Suite (108 Automated Tests):
```powershell
python -m unittest discover tests/
```
All 108 tests cover model validation, feature pipelines, multi-currency processing, API endpoints, error handling, session management, password hashing, role-based permissions, brute-force lockout, sole-admin protection, audit trails, and security headers.

---

## 🛡️ 14. Security Operations, Audit Logging & Admin Center (Prompt 9)

Prompt 9 elevates the platform into a production-grade **Security Operations & Compliance** environment featuring comprehensive audit trail logging, account lockout defense, system telemetry, and defense-in-depth HTTP security headers.

### Key Capabilities

1. **Admin Operations & Security Command Center (`/admin`)**
   - Consolidated system telemetry: active vs. inactive users, role distribution, database transaction volume, and fraud interception rate.
   - Real-time infrastructure diagnostics: Werkzeug Scrypt password verification, HttpOnly/SameSite cookie policies, 5-attempt/15-minute brute-force shields, and Content Security Policy (CSP).
   - Live audit feed displaying recent platform security events with instant links to full historical investigation.

2. **Enterprise User Management & Identity Lifecycle (`/admin/users`)**
   - Live search by username or email, plus filtering by role (`admin`, `analyst`) and status (`active`, `inactive`).
   - Modal-based user provisioning with input validation and default analyst/admin assignment.
   - Role promotion/demotion and account activation/deactivation.
   - **Sole Active Administrator Protection:** Hardware-safe guardrails prevent deactivating or demoting the last active administrator, preventing system self-lockout.

3. **Immutable Security Audit Trail (`AuditLog`)**
   - Dedicated database model (`audit_logs`) tracking timestamp, user ID, username, event category (`AUTH`, `ADMIN`, `SECURITY`, `ACCESS`), specific action, description, IP address, user agent, outcome status (`SUCCESS`, `FAILURE`, `WARNING`), and sanitized metadata.
   - Zero exposure of sensitive secrets, passwords, or tokens in stored metadata.
   - High-performance B-tree indexes on `timestamp`, `event_type`, `user_id`, and `action`.
   - Explorer interface (`/admin/audit-logs`) with multi-attribute filtering, free-text search, and server-side pagination.

4. **Brute-Force Attack Shield & Account Lockout**
   - Tracks consecutive failed login attempts on user accounts (`failed_login_attempts`).
   - Reaching threshold (5 failed attempts) triggers automatic temporary lockout for 15 minutes (`locked_until`).
   - Locked accounts cannot authenticate even with valid credentials until the timeout expires.
   - Successful authentication resets failed attempts counter to zero.

5. **Admin Audit Logs REST API (`GET /api/admin/audit-logs`)**
   - Role-protected JSON API returning paginated security events.
   - Supports query filters: `event_type`, `status`, `search`, `start_date`, `end_date`, `page`, and `per_page`.
   - Requires valid administrator credentials (returns HTTP 401 for unauthenticated, HTTP 403 for analysts).

6. **Defense-in-Depth HTTP Security Response Headers**
   - Injected globally via `@app.after_request` middleware:
     - `Content-Security-Policy (CSP)`: Enforces strict origin restrictions, allowing required Google Fonts and CDN Chart.js.
     - `X-Content-Type-Options: nosniff`: Mitigates MIME-type sniffing vulnerabilities.
     - `X-Frame-Options: SAMEORIGIN`: Defends against clickjacking.
     - `Referrer-Policy: strict-origin-when-cross-origin`: Controls referrer leakage.
     - `X-XSS-Protection: 1; mode=block`: Legacy browser XSS filter enforcement.

### Security Audit Event Catalog

| Event Category | Action Identifier | Trigger Condition | Outcome Status |
| :--- | :--- | :--- | :---: |
| **AUTH** | `LOGIN_SUCCESS` | User successfully authenticated | `SUCCESS` |
| **AUTH** | `LOGIN_FAILED` | Incorrect password entered for existing account | `FAILURE` |
| **AUTH** | `LOGOUT` | User explicitly ended active session | `SUCCESS` |
| **AUTH** | `USER_REGISTERED` | New self-registered analyst account created | `SUCCESS` |
| **AUTH** | `ACCOUNT_LOCKED_ATTEMPT` | Login attempt blocked by active 15m lockout | `WARNING` |
| **AUTH** | `INACTIVE_ACCOUNT_ATTEMPT` | Login attempt blocked on deactivated account | `FAILURE` |
| **ADMIN** | `USER_CREATED` | Administrator provisioned new user | `SUCCESS` |
| **ADMIN** | `USER_STATUS_TOGGLED` | Administrator activated or deactivated account | `SUCCESS` |
| **ADMIN** | `ROLE_CHANGED` | Administrator changed account role (admin/analyst) | `SUCCESS` |
| **SECURITY** | `ACCOUNT_LOCKED` | 5th consecutive failed login triggered 15m lock | `WARNING` |
| **SECURITY** | `LAST_ADMIN_PROTECTED` | Attempt to demote/deactivate last admin blocked | `WARNING` |
| **SECURITY** | `UNAUTHORIZED_ACCESS` | User attempted to access unauthorized role route | `FAILURE` |

### Security Verification & Test Execution

Run the Prompt 9 dedicated audit test suite:
```powershell
python -m unittest tests/test_audit.py
```
Run the complete system test suite:
```powershell
python -m unittest discover tests/
```
Output: **121 tests passing, 0 failures, 0 errors**.

---

## 🔒 15. Testing, Reliability & Production Hardening (Prompt 10)

Prompt 10 hardens the end-to-end platform for enterprise reliability, robust exception boundaries, abuse protection, and production-grade fault tolerance.

### Key Capabilities & Reliability Engineering

1. **Centralized Enterprise Error Handling (`app/utils/errors.py`)**
   - Universal application-level error handlers for all primary HTTP status codes:
     - `400 Bad Request`
     - `401 Unauthorized`
     - `403 Forbidden`
     - `404 Not Found`
     - `405 Method Not Allowed`
     - `409 Conflict`
     - `422 Validation Error`
     - `429 Too Many Requests`
     - `500 Internal Server Error`
   - **Content Negotiation:**
     - API consumers (`/api/*`, `Accept: application/json`) receive structured, machine-readable JSON error contracts with timestamp and error categories.
     - Browser consumers receive a responsive, styled error template (`app/templates/errors/error.html`) matching the fintech design system with action shortcuts.
   - **Zero Traceback Leakage:** Strict masking prevents exposing Python exception tracebacks, database table details, or stack frames in production responses.

2. **Abuse Defense & Sliding Window Rate Limiting (`app/utils/limiter.py`)**
   - In-memory thread-safe sliding window rate limiter tracking request frequencies per IP or authenticated user.
   - Sensitive endpoints protected:
     - `/login` & `/api/auth/login`: 25 requests/min.
     - `/register`: 15 requests/min.
     - `/api/predict`: 120 evaluations/min.
     - `/admin/users/create`: 30 operations/min.
   - When exceeded, returns HTTP 429 with compliant `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Reset` response headers.
   - Automatic zero-friction bypass in automated testing environments (`TESTING=True`).

3. **Defense-in-Depth HTTP Security Response Headers**
   - Automatically injected across 100% of HTTP responses via application middleware:
     - `X-Content-Type-Options: nosniff`: Mitigates MIME-sniffing exploits.
     - `X-Frame-Options: SAMEORIGIN`: Prevents clickjacking.
     - `Referrer-Policy: strict-origin-when-cross-origin`: Controls referrer leakage.
     - `X-XSS-Protection: 1; mode=block`: Legacy browser cross-site scripting filter.
     - `Permissions-Policy: geolocation=(), microphone=(), camera=()`: Restricts sensitive browser device features.
     - `Content-Security-Policy (CSP)`: Origin whitelist for local scripts, Google Fonts, and Chart.js.

4. **Database Transaction Safety & Rollback Hardening**
   - Atomic unit of work semantics (`db.session.commit()`).
   - Exception handlers explicitly trigger `db.session.rollback()`, ensuring corrupted session state is discarded and connections are released cleanly.
   - Zero destructive schema operations; existing records, users, and audit logs are 100% preserved.

5. **Flexible Dual Authentication**
   - Seamless sign-in support using either account **Email** (`admin@fraudguard.local`) or **Username** (`admin`).
   - Unified credentials resolution across both Web UI (`/login`) and REST API (`/api/auth/login`).

6. **Google OAuth 2.0 / OpenID Connect Single Sign-On ("Continue with Google")**
   - Standards-compliant OAuth 2.0 / OpenID Connect identity federation.
   - Built with Python's standard library (`urllib`, `secrets`, `hmac`, `json`) ensuring zero extra dependencies and clean execution on Python 3.14.
   - **Account Matching & Auto-Provisioning:**
     - Verified Google accounts matching an existing local email automatically sign in to that account without duplication.
     - New Google users are automatically provisioned with the standard **`analyst`** role (never auto-granting administrative privileges) and assigned an unguessable randomized password.
     - Deactivated / inactive accounts are blocked from authentication with a safe status notification.
   - **Defense & Telemetry:** Cryptographic CSRF state validation, zero token persistence, and comprehensive event logging (`GOOGLE_LOGIN_SUCCESS`, `GOOGLE_LOGIN_FAILURE`, `GOOGLE_LOGIN_CANCELLED`) in the SQLite audit ledger.

---

## 🔐 11. Google OAuth 2.0 Setup Guide

To enable live **"Continue with Google"** authentication, real Google OAuth credentials must be configured:

### Step 1: Create / Select a Project in Google Cloud Console
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing project (e.g., `FraudGuard-AI`).

### Step 2: Configure the OAuth Consent Screen
1. Go to **APIs & Services > OAuth consent screen**.
2. Select **External** (or **Internal** if using a Google Workspace organization) and click **Create**.
3. Enter Application Information:
   - **App name:** `FraudGuard AI`
   - **User support email:** your email address
   - **Developer contact information:** your email address
4. Under **Scopes**, click **Add or Remove Scopes** and select:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
5. Save and continue.

### Step 3: Create OAuth 2.0 Client ID Credentials
1. Go to **APIs & Services > Credentials**.
2. Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
3. Choose **Application type:** `Web application`.
4. Name the client: `FraudGuard AI Web Client`.
5. Under **Authorized redirect URIs**, click **+ ADD URI** and enter:
   - For local development:
     ```text
     http://127.0.0.1:5000/auth/google/callback
     ```
   - If accessing via localhost:
     ```text
     http://localhost:5000/auth/google/callback
     ```
6. Click **CREATE** and copy your **Client ID** and **Client Secret**.

### Step 4: Configure Environment Variables
Create or edit your `.env` file in the project root:

```bash
# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
```

> **Note:** Real Google credentials are required to communicate with Google's live identity servers. If unconfigured, the application runs normally, provides traditional email/password login, and displays a friendly notice if the Google button is clicked.

### Step 5: Start the Application & Verify
1. Start the Flask server:
   ```powershell
   python run.py
   ```
2. Navigate to `http://127.0.0.1:5000/login`.
3. Click **Continue with Google** to authenticate with your Google account.

---

### Verification Commands

```powershell
# Run Google OAuth Automated Test Suite (14 tests)
python -m unittest tests/test_google_oauth.py -v

# Run Full Test Suite (135 tests)
python -m unittest discover tests/ -v

# Launch the Application
python run.py
```




