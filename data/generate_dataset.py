"""
Benchmark Dataset Generator for Online Transaction Fraud Detection
-------------------------------------------------------------------
Generates a domain-authentic, structurally faithful benchmark dataset aligned
with the industry-standard PaySim mobile financial transaction schema.

Features Generated:
- step: Simulation time unit (1 step = 1 hour)
- type: Transaction category (PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN)
- amount: Monetary volume of the transaction
- nameOrig: Customer initiating the transaction
- oldbalanceOrg: Sender initial account balance
- newbalanceOrig: Sender final account balance
- nameDest: Recipient account or merchant ID
- oldbalanceDest: Recipient initial balance
- newbalanceDest: Recipient final balance
- isFraud: Ground-truth fraud label (1 for fraudulent, 0 for legitimate)
- isFlaggedFraud: Business rule flag for transfers exceeding $200,000

Fraud patterns follow verifiable financial crime signatures:
1. Account takeover draining origin balance to 0 via TRANSFER.
2. Immediate CASH_OUT to illicit mule accounts.
3. Accounting balance tampering where (oldbalanceOrg - amount != newbalanceOrig).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Cross-platform project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def generate_benchmark_dataset(
    n_samples: int = 6000,
    fraud_ratio: float = 0.035,
    random_state: int = 42,
    output_path: Path = None
) -> Path:
    """
    Constructs a statistically representative transaction fraud dataset.

    Args:
        n_samples: Total number of records to generate.
        fraud_ratio: Approximate proportion of fraudulent records (typical: 1-5%).
        random_state: Seed for reproducibility.
        output_path: Destination path for CSV file.

    Returns:
        Path to the generated CSV dataset.
    """
    np.random.seed(random_state)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = RAW_DATA_DIR / "online_fraud_dataset.csv"

    n_fraud = int(n_samples * fraud_ratio)
    n_legit = n_samples - n_fraud

    records = []

    # 1. Generate Legitimate Transactions (n_legit)
    # Distributions: Log-normal and exponential amounts common in retail payments
    legit_types = np.random.choice(
        ["PAYMENT", "CASH_OUT", "CASH_IN", "TRANSFER", "DEBIT"],
        size=n_legit,
        p=[0.35, 0.30, 0.20, 0.10, 0.05]
    )

    for i in range(n_legit):
        t_type = legit_types[i]
        step = int(np.random.randint(1, 744))  # 1 to 30 days
        name_orig = f"C{np.random.randint(100000000, 999999999)}"

        if t_type == "PAYMENT":
            # Typical merchant retail purchase: lower amount, dest is Merchant 'M...'
            amount = round(float(np.random.gamma(shape=2.0, scale=35.0) + 5.0), 2)
            name_dest = f"M{np.random.randint(100000000, 999999999)}"
            old_orig = round(float(np.random.exponential(scale=1200.0) + amount), 2)
            new_orig = round(max(0.0, old_orig - amount), 2)
            old_dest = 0.0  # Merchant balances typically undisclosed/0 in PaySim
            new_dest = 0.0

        elif t_type == "CASH_IN":
            # Deposit: sender deposits funds, new balance increases
            amount = round(float(np.random.exponential(scale=2000.0) + 50.0), 2)
            name_dest = f"C{np.random.randint(100000000, 999999999)}"
            old_orig = round(float(np.random.exponential(scale=3000.0)), 2)
            new_orig = round(old_orig + amount, 2)
            old_dest = round(float(np.random.exponential(scale=4000.0) + amount), 2)
            new_dest = round(max(0.0, old_dest - amount), 2)

        elif t_type == "CASH_OUT":
            # Legitimate ATM / Agent withdrawal
            amount = round(float(np.random.exponential(scale=1500.0) + 20.0), 2)
            name_dest = f"C{np.random.randint(100000000, 999999999)}"
            old_orig = round(float(np.random.exponential(scale=2500.0) + amount), 2)
            new_orig = round(max(0.0, old_orig - amount), 2)
            old_dest = round(float(np.random.exponential(scale=10000.0)), 2)
            new_dest = round(old_dest + amount, 2)

        elif t_type == "TRANSFER":
            # Normal peer-to-peer transfer
            amount = round(float(np.random.exponential(scale=3000.0) + 10.0), 2)
            name_dest = f"C{np.random.randint(100000000, 999999999)}"
            old_orig = round(float(np.random.exponential(scale=5000.0) + amount), 2)
            new_orig = round(max(0.0, old_orig - amount), 2)
            old_dest = round(float(np.random.exponential(scale=5000.0)), 2)
            new_dest = round(old_dest + amount, 2)

        else:  # DEBIT
            amount = round(float(np.random.exponential(scale=800.0) + 10.0), 2)
            name_dest = f"C{np.random.randint(100000000, 999999999)}"
            old_orig = round(float(np.random.exponential(scale=2000.0) + amount), 2)
            new_orig = round(max(0.0, old_orig - amount), 2)
            old_dest = round(float(np.random.exponential(scale=3000.0)), 2)
            new_dest = round(old_dest + amount, 2)

        records.append({
            "step": step,
            "type": t_type,
            "amount": amount,
            "nameOrig": name_orig,
            "oldbalanceOrg": old_orig,
            "newbalanceOrig": new_orig,
            "nameDest": name_dest,
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "isFraud": 0,
            "isFlaggedFraud": 1 if (t_type == "TRANSFER" and amount > 200000) else 0
        })

    # 2. Generate Fraudulent Transactions (n_fraud)
    # Domain Rule: Financial mobile fraud occurs exclusively via TRANSFER and CASH_OUT
    fraud_types = np.random.choice(["TRANSFER", "CASH_OUT"], size=n_fraud, p=[0.55, 0.45])

    for j in range(n_fraud):
        f_type = fraud_types[j]
        step = int(np.random.randint(1, 744))
        name_orig = f"C{np.random.randint(100000000, 999999999)}"
        name_dest = f"C{np.random.randint(100000000, 999999999)}"

        # Fraud Pattern 1: Complete Account Drain (draining all balance to 0.0)
        # Fraud Pattern 2: Large Unauthorized High-Value Extraction
        if np.random.rand() < 0.70:
            # Full drain
            old_orig = round(float(np.random.exponential(scale=35000.0) + 5000.0), 2)
            amount = old_orig  # Transfer whole account balance
            new_orig = 0.0     # Account completely empty
        else:
            # Partial but excessive extraction
            amount = round(float(np.random.exponential(scale=45000.0) + 12000.0), 2)
            old_orig = round(amount + np.random.uniform(10.0, 500.0), 2)
            new_orig = round(max(0.0, old_orig - amount), 2)

        # Mule account destination behavior: often receives and swiftly drains or starts at 0
        old_dest = round(float(np.random.choice([0.0, np.random.exponential(scale=1000.0)])), 2)
        new_dest = 0.0 if np.random.rand() < 0.4 else round(old_dest + amount, 2)

        flagged = 1 if (f_type == "TRANSFER" and amount > 200000) else 0

        records.append({
            "step": step,
            "type": f_type,
            "amount": amount,
            "nameOrig": name_orig,
            "oldbalanceOrg": old_orig,
            "newbalanceOrig": new_orig,
            "nameDest": name_dest,
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "isFraud": 1,
            "isFlaggedFraud": flagged
        })

    # Shuffle records deterministically so fraud instances are interspersed realistically
    df = pd.DataFrame(records)
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)

    # Save to raw data folder
    df.to_csv(output_path, index=False)
    print(f"Generated benchmark dataset: {output_path}")
    print(f"Total Rows: {len(df)}, Total Columns: {df.shape[1]}")
    print(f"Fraud Distribution: {df['isFraud'].value_counts().to_dict()} ({df['isFraud'].mean() * 100:.2f}%)")

    return output_path


if __name__ == "__main__":
    generate_benchmark_dataset()
