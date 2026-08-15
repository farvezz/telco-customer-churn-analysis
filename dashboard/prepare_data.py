"""Precompute all artifacts the Streamlit dashboard needs, so the dashboard itself
just loads data instead of retraining a model on every rerun.

Mirrors the cleaning / modeling / cost-optimization steps in telco_churn_analysis.ipynb.
Run this once (or whenever the source CSV / methodology changes):

    python prepare_data.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, brier_score_loss, confusion_matrix, f1_score,
    precision_score, precision_recall_curve, recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).parent
DATA_CSV = HERE.parent / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
OUT = HERE / "artifacts"
OUT.mkdir(exist_ok=True)

RANDOM_STATE = 42

# ---------------------------------------------------------------- Load & clean
df = pd.read_csv(DATA_CSV)

df_clean = df.copy()
df_clean["TotalCharges"] = pd.to_numeric(df_clean["TotalCharges"], errors="coerce").fillna(0)
df_clean = df_clean.drop(columns=["customerID"])
service_cols = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                 "TechSupport", "StreamingTV", "StreamingMovies", "MultipleLines"]
for c in service_cols:
    df_clean[c] = df_clean[c].replace({"No internet service": "No", "No phone service": "No"})
df_clean["SeniorCitizen"] = df_clean["SeniorCitizen"].astype(int)

df_clean.to_csv(OUT / "cleaned_data.csv", index=False)

# ---------------------------------------------------------------- Churn-driver breakdowns (for EDA charts)
def churn_rate_by(field):
    out = df_clean.groupby(field)["Churn"].apply(lambda s: (s == "Yes").mean() * 100).round(1)
    counts = df_clean.groupby(field).size()
    return pd.DataFrame({"churn_rate_pct": out, "n_customers": counts}).reset_index().rename(columns={field: "category"}).assign(field=field)

driver_fields = ["Contract", "InternetService", "PaymentMethod", "SeniorCitizen", "Partner", "Dependents", "PaperlessBilling"]
driver_df = pd.concat([churn_rate_by(f) for f in driver_fields], ignore_index=True)
driver_df.to_csv(OUT / "churn_drivers.csv", index=False)

bins = [-1, 12, 24, 48, 60, 72]
labels = ["0-12", "13-24", "25-48", "49-60", "61-72"]
df_clean["tenure_bucket"] = pd.cut(df_clean["tenure"], bins=bins, labels=labels)
tenure_df = df_clean.groupby("tenure_bucket", observed=True)["Churn"].apply(lambda s: (s == "Yes").mean() * 100).round(1).reset_index()
tenure_df.columns = ["tenure_bucket", "churn_rate_pct"]
tenure_df["n_customers"] = df_clean.groupby("tenure_bucket", observed=True).size().values
tenure_df.to_csv(OUT / "tenure_churn.csv", index=False)

# ---------------------------------------------------------------- Model
X = df_clean.drop(columns=["Churn", "tenure_bucket"])
y = (df_clean["Churn"] == "Yes").astype(int)

categorical_cols = X.select_dtypes(include="object").columns.tolist()
numeric_cols = [c for c in X.select_dtypes(exclude="object").columns if c != "SeniorCitizen"]
categorical_cols = categorical_cols + ["SeniorCitizen"]

preprocessor = ColumnTransformer(transformers=[
    ("num", StandardScaler(), numeric_cols),
    ("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), categorical_cols),
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
)

model = GradientBoostingClassifier(random_state=RANDOM_STATE)
best_pipe = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
best_pipe.fit(X_train, y_train)

y_test_proba = best_pipe.predict_proba(X_test)[:, 1]
y_test_pred_default = (y_test_proba >= 0.5).astype(int)

metrics_default = {
    "accuracy": accuracy_score(y_test, y_test_pred_default),
    "precision": precision_score(y_test, y_test_pred_default),
    "recall": recall_score(y_test, y_test_pred_default),
    "f1": f1_score(y_test, y_test_pred_default),
    "roc_auc": roc_auc_score(y_test, y_test_proba),
    "brier": brier_score_loss(y_test, y_test_proba),
}

# F2-optimal threshold via out-of-fold CV on training set (no test-set leakage)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
oof_proba = cross_val_predict(clone(best_pipe), X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1)[:, 1]
precisions, recalls, thresholds = precision_recall_curve(y_train, oof_proba)
precisions, recalls = precisions[:-1], recalls[:-1]
f2_scores = (1 + 2**2) * (precisions * recalls) / (2**2 * precisions + recalls + 1e-12)
f2_threshold = float(thresholds[np.argmax(f2_scores)])

# Threshold comparison table
def metrics_at(threshold):
    pred = (y_test_proba >= threshold).astype(int)
    return {
        "threshold": threshold,
        "precision": precision_score(y_test, pred),
        "recall": recall_score(y_test, pred),
        "f1": f1_score(y_test, pred),
    }

threshold_table = pd.DataFrame([
    {"policy": "Default (0.50)", **metrics_at(0.5)},
    {"policy": "Recall-focused (0.13)", **metrics_at(f2_threshold)},
    {"policy": "Recommended (0.20)", **metrics_at(0.20)},
])
threshold_table.to_csv(OUT / "threshold_table.csv", index=False)

# ROC curve points
fpr, tpr, _ = roc_curve(y_test, y_test_proba)
pd.DataFrame({"fpr": fpr, "tpr": tpr}).to_csv(OUT / "roc_curve.csv", index=False)

# Confusion matrix at recommended threshold
cm = confusion_matrix(y_test, (y_test_proba >= 0.20).astype(int))
pd.DataFrame(cm, index=["Actual: No churn", "Actual: Churn"], columns=["Pred: No churn", "Pred: Churn"]).to_csv(
    OUT / "confusion_matrix_020.csv"
)

# Reliability diagram
prob_true, prob_pred = calibration_curve(y_test, y_test_proba, n_bins=10, strategy="uniform")
pd.DataFrame({"predicted": prob_pred, "observed": prob_true}).to_csv(OUT / "reliability.csv", index=False)

# Feature importance
feature_names = best_pipe.named_steps["preprocessor"].get_feature_names_out()
importances = best_pipe.named_steps["model"].feature_importances_
fi = pd.Series(importances, index=feature_names).sort_values(ascending=False).head(12)
fi.to_csv(OUT / "feature_importance.csv", header=["importance"])

# ---------------------------------------------------------------- Financial / cost-based policy comparison
avg_monthly = df_clean["MonthlyCharges"].mean()
COST_OFFER, COST_LOST = 50, 250  # X, Y -- see notebook section 10 for derivation (Y = 5x X -> threshold 0.20)


def total_cost(threshold, cost_offer, cost_lost):
    pred = (y_test_proba >= threshold).astype(int)
    y_true = y_test.values
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    return cost_offer * (tp + fp) + cost_lost * fn


n_test = len(y_test)
n_churners = int(y_test.sum())
policy_costs = {
    "Do nothing": COST_LOST * n_churners,
    "Target everyone": COST_OFFER * n_test,
    "Default threshold (0.50)": total_cost(0.5, COST_OFFER, COST_LOST),
    "Recommended threshold (0.20)": total_cost(0.20, COST_OFFER, COST_LOST),
}
policy_df = pd.DataFrame.from_dict(policy_costs, orient="index", columns=["total_cost"])
policy_df["savings_vs_do_nothing"] = policy_df.loc["Do nothing", "total_cost"] - policy_df["total_cost"]
policy_df = policy_df.reset_index().rename(columns={"index": "policy"})
policy_df.to_csv(OUT / "policy_costs.csv", index=False)

# ---------------------------------------------------------------- Headline numbers
summary = {
    "n_customers": int(len(df_clean)),
    "churn_rate_pct": round(float((df_clean["Churn"] == "Yes").mean() * 100), 2),
    "avg_monthly_charge": round(float(avg_monthly), 2),
    "monthly_revenue_at_risk": round(float(df_clean.loc[df_clean["Churn"] == "Yes", "MonthlyCharges"].sum()), 2),
    "annual_revenue_at_risk": round(float(df_clean.loc[df_clean["Churn"] == "Yes", "MonthlyCharges"].sum() * 12), 2),
    "model_name": "Gradient Boosting",
    "roc_auc": round(metrics_default["roc_auc"], 3),
    "recall_at_020": round(float(metrics_at(0.20)["recall"]), 3),
    "precision_at_020": round(float(metrics_at(0.20)["precision"]), 3),
    "cost_offer": COST_OFFER,
    "cost_lost": COST_LOST,
    "n_test": n_test,
    "n_test_churners": n_churners,
    "savings_recommended_vs_do_nothing": float(
        policy_df.loc[policy_df["policy"] == "Recommended threshold (0.20)", "savings_vs_do_nothing"].iloc[0]
    ),
    "savings_recommended_vs_default": float(
        policy_df.loc[policy_df["policy"] == "Default threshold (0.50)", "total_cost"].iloc[0]
        - policy_df.loc[policy_df["policy"] == "Recommended threshold (0.20)", "total_cost"].iloc[0]
    ),
}
with open(OUT / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("Artifacts written to", OUT)
print(json.dumps(summary, indent=2))
