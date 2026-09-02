# Power BI Build Guide

Power BI Desktop isn't available in the environment this project was built in, so this folder is a
ready-to-import data package plus a step-by-step spec — not a `.pbix` file. Opening Power BI Desktop and
following this guide should take about 10-15 minutes and reproduces the same four-page structure as the
Streamlit dashboard (`../dashboard/`).

## 1. Load the data

`Home > Get Data > Text/CSV`, import every file in `data/`:

| File | Use |
|---|---|
| `kpi_summary.csv` | headline KPI cards |
| `churn_drivers.csv` | churn rate by Contract / InternetService / PaymentMethod / SeniorCitizen / Partner / Dependents / PaperlessBilling (has a `field` column to filter by) |
| `tenure_churn.csv` | churn rate by tenure bucket |
| `feature_importance.csv` | top model features |
| `policy_costs.csv` | cost-by-policy comparison |
| `threshold_table.csv` | precision/recall/F1 at each decision threshold |
| `roc_curve.csv`, `reliability.csv`, `confusion_matrix_020.csv` | model performance (appendix page) |
| `cleaned_data.csv` | full cleaned customer-level dataset, for any ad-hoc slicing |

In Power Query, set `churn_rate_pct`, `n_customers`, and similar numeric columns to **Decimal Number** /
**Whole Number** type (CSV import sometimes leaves them as text).

## 2. Page 1 — Executive Summary

- **Card visuals** (source: `kpi_summary.csv`, filter the `metric` column per card):
  - Churn rate → `churn_rate_pct` (format as %)
  - Monthly revenue at risk → `monthly_revenue_at_risk` (format as currency)
  - Annualized → `annual_revenue_at_risk`
  - Projected savings → `savings_recommended_vs_do_nothing`
- **Donut chart**: Retained (73.5%) vs. Churned (26.5%) — build from `kpi_summary.csv`'s `churn_rate_pct`, or a 2-row manual table.
- **Text box** with the headline recommendation (copy from `dashboard/app.py`'s Executive Summary section, or the notebook's conclusion) — landing the "launch a targeted campaign at threshold 0.20, ~$46,500 projected savings" message front and center.

## 3. Page 2 — Who's Churning

Source: `churn_drivers.csv` (filter `field`) and `tenure_churn.csv`.

- **Clustered bar chart**: `category` (Contract types) on axis, `churn_rate_pct` as value — filter `churn_drivers.csv` to `field = "Contract"`.
- **Bar chart**: same pattern for `field = "InternetService"` and `field = "PaymentMethod"`.
- **Bar chart**: `tenure_churn.csv`, `tenure_bucket` on axis, `churn_rate_pct` as value.
- **Bar chart**: `feature_importance.csv`, sorted descending, top 10 features.
- Add one-line text-box takeaways under each chart (see `dashboard/app.py` captions for the exact wording already written for this).

## 4. Page 3 — Financial Recommendation

Source: `policy_costs.csv` and `threshold_table.csv`.

- **Bar chart**: `policy` on axis, `total_cost` as value — color "Do nothing"/"Target everyone" red, "Recommended threshold (0.20)" green, others neutral gray (conditional formatting on the bar chart's Data colors).
- **Cards**: recommended policy cost, `savings_vs_do_nothing`, and (default cost − recommended cost) for "savings vs. untuned default".
- **Table**: `threshold_table.csv` — Policy / Threshold / Precision / Recall / F1.
- **Text box**: the cost-framing explanation ("every flagged customer gets a ~$50 offer... cost-optimal threshold is X/Y = 0.20") — copy from `dashboard/app.py`.

## 5. Page 4 — Model Performance (Appendix)

- **Line chart**: `roc_curve.csv`, `fpr` on X, `tpr` on Y.
- **Line chart**: `reliability.csv`, `predicted` on X, `observed` on Y, plus a reference diagonal line.
- **Matrix/table visual**: `confusion_matrix_020.csv`.

## Notes

- All figures here match the notebook (`../telco_churn_analysis.ipynb`) and the live Streamlit dashboard
  (https://telco-churn-executive-dashboard.streamlit.app) exactly — same model, same test set, same
  threshold — so cross-check against either if a number looks off after rebuilding a visual.
- If you'd rather not rebuild manually, DAX measures can replace the pre-aggregated CSVs (e.g. a
  `Churn Rate = DIVIDE(CALCULATE(COUNTROWS('cleaned_data'), 'cleaned_data'[Churn]="Yes"), COUNTROWS('cleaned_data'))`
  measure against `cleaned_data.csv` directly), but the flat files avoid needing to re-derive the modeling
  results (thresholds, cost policy, feature importance) inside Power BI.
