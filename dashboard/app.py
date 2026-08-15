import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent
ART = HERE / "artifacts"

st.set_page_config(page_title="Telco Churn — Executive Dashboard", layout="wide", page_icon="📉")

PRIMARY = "#2E5EAA"
DANGER = "#D64545"
NEUTRAL = "#8C9BAB"
GOOD = "#2E9E5B"


@st.cache_data
def load_artifacts():
    with open(ART / "summary.json") as f:
        summary = json.load(f)
    return {
        "summary": summary,
        "drivers": pd.read_csv(ART / "churn_drivers.csv"),
        "tenure": pd.read_csv(ART / "tenure_churn.csv"),
        "thresholds": pd.read_csv(ART / "threshold_table.csv"),
        "roc": pd.read_csv(ART / "roc_curve.csv"),
        "cm": pd.read_csv(ART / "confusion_matrix_020.csv", index_col=0),
        "reliability": pd.read_csv(ART / "reliability.csv"),
        "fi": pd.read_csv(ART / "feature_importance.csv", index_col=0),
        "policy": pd.read_csv(ART / "policy_costs.csv"),
    }


data = load_artifacts()
s = data["summary"]

st.sidebar.title("📉 Telco Churn")
page = st.sidebar.radio(
    "Section",
    ["Executive Summary", "Who's Churning", "Financial Recommendation", "Model Performance (Appendix)"],
)
st.sidebar.markdown("---")
st.sidebar.caption(
    f"{s['n_customers']:,} customers · {s['churn_rate_pct']}% churn rate\n\n"
    f"Model: {s['model_name']} (ROC-AUC {s['roc_auc']})"
)

# ============================================================== Executive Summary
if page == "Executive Summary":
    st.title("Customer Churn — Executive Summary")
    st.caption("IBM Telco Customer Churn dataset · 7,043 customers")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Churn rate", f"{s['churn_rate_pct']}%", help="Share of customers who have churned")
    c2.metric("Monthly revenue at risk", f"${s['monthly_revenue_at_risk']:,.0f}",
              help="Sum of MonthlyCharges for customers who already churned")
    c3.metric("Annualized", f"${s['annual_revenue_at_risk']:,.0f}")
    c4.metric("Projected savings (test sample)", f"${s['savings_recommended_vs_do_nothing']:,.0f}",
              help=f"Modeled savings on the {s['n_test']:,}-customer test sample from running a targeted "
                   "retention campaign at the recommended threshold vs. doing nothing")

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("The headline")
        st.markdown(f"""
- **1 in 4 customers churns** ({s['churn_rate_pct']}%) — well above what's sustainable for a subscription business.
- Churn is **not random**: it concentrates heavily in customers on month-to-month contracts, in their first
  year, on fiber internet, and paying by electronic check (see *Who's Churning*).
- A predictive model (**{s['model_name']}**, ROC-AUC **{s['roc_auc']}**) can flag at-risk customers before
  they leave, catching **{s['recall_at_020']*100:.0f}% of churners** when tuned for this business case.
- Acting on those flags with a targeted retention offer — instead of doing nothing, or blanket-targeting
  everyone — is projected to save **\${s['savings_recommended_vs_do_nothing']:,.0f}** on a
  {s['n_test']:,}-customer sample (see *Financial Recommendation*).
        """)

    with col2:
        fig = go.Figure(go.Pie(
            labels=["Retained", "Churned"],
            values=[100 - s["churn_rate_pct"], s["churn_rate_pct"]],
            hole=0.6,
            marker_colors=[PRIMARY, DANGER],
            textinfo="label+percent",
        ))
        fig.update_layout(title="Customer base", height=320, margin=dict(t=50, b=0, l=0, r=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recommendation")
    st.success(
        f"**Launch a targeted retention campaign** using the model's churn scores, offering an incentive to "
        f"any customer scoring above **0.20** probability of churning. At realistic offer economics "
        f"(~\\$50 incentive protecting ~\\$250 of at-risk revenue), this policy is projected to save "
        f"**\\${s['savings_recommended_vs_do_nothing']:,.0f}** vs. no intervention, and "
        f"**\\${s['savings_recommended_vs_default']:,.0f}** more than the model's untuned default cutoff — "
        f"on this {s['n_test']:,}-customer holdout alone."
    )

# ============================================================== Who's Churning
elif page == "Who's Churning":
    st.title("Who's Churning — and Why")
    st.caption("Churn rate by segment, IBM Telco dataset (7,043 customers)")

    drivers = data["drivers"]
    tenure = data["tenure"]

    col1, col2 = st.columns(2)

    with col1:
        contract = drivers[drivers["field"] == "Contract"].sort_values("churn_rate_pct", ascending=False)
        fig = px.bar(contract, x="category", y="churn_rate_pct", text="churn_rate_pct",
                     color="churn_rate_pct", color_continuous_scale=["#C7D6EC", DANGER])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(title="Churn rate by contract type", yaxis_title="Churn rate (%)",
                           xaxis_title="", coloraxis_showscale=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Month-to-month customers churn at 5-15x the rate of annual-contract customers.")

    with col2:
        fig = px.bar(tenure, x="tenure_bucket", y="churn_rate_pct", text="churn_rate_pct",
                     color="churn_rate_pct", color_continuous_scale=["#C7D6EC", DANGER])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(title="Churn rate by tenure (months)", yaxis_title="Churn rate (%)",
                           xaxis_title="Tenure (months)", coloraxis_showscale=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Nearly half of customers in their first year churn — retention risk is front-loaded.")

    col3, col4 = st.columns(2)

    with col3:
        internet = drivers[drivers["field"] == "InternetService"].sort_values("churn_rate_pct", ascending=False)
        fig = px.bar(internet, x="category", y="churn_rate_pct", text="churn_rate_pct",
                     color="churn_rate_pct", color_continuous_scale=["#C7D6EC", DANGER])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(title="Churn rate by internet service", yaxis_title="Churn rate (%)",
                           xaxis_title="", coloraxis_showscale=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fiber optic customers churn the most, despite paying the highest bills — a service-quality signal worth investigating.")

    with col4:
        payment = drivers[drivers["field"] == "PaymentMethod"].sort_values("churn_rate_pct", ascending=False)
        fig = px.bar(payment, x="category", y="churn_rate_pct", text="churn_rate_pct",
                     color="churn_rate_pct", color_continuous_scale=["#C7D6EC", DANGER])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(title="Churn rate by payment method", yaxis_title="Churn rate (%)",
                           xaxis_title="", coloraxis_showscale=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Electronic check payers churn 2-3x more than automatic-payment customers — a friction/commitment signal.")

    st.markdown("---")
    st.subheader("What drives the model's predictions")
    fi = data["fi"].sort_values("importance").tail(10)
    fig = px.bar(fi, x="importance", y=fi.index, orientation="h", color_discrete_sequence=[PRIMARY])
    fig.update_layout(title="Top 10 features the model relies on", height=420, yaxis_title="", xaxis_title="Relative importance")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================== Financial Recommendation
elif page == "Financial Recommendation":
    st.title("Financial Recommendation")
    st.caption("Cost-based decision threshold, grounded in retention-campaign economics")

    st.markdown(f"""
**The setup:** every customer flagged by the model gets a retention offer costing about **\\${s['cost_offer']}**
(e.g. a one-month bill credit). If we correctly catch a churner, we assume the offer keeps them — avoiding a
loss of about **\\${s['cost_lost']}** in near-term revenue. Missing a churner (not flagging them) costs the
full **\\${s['cost_lost']}**. Under this economics, the cost-minimizing decision rule works out to flagging
anyone the model scores above **0.20** probability of churning.
    """)

    policy = data["policy"].copy()
    policy["label"] = policy["policy"]
    fig = go.Figure(go.Bar(
        x=policy["total_cost"], y=policy["label"], orientation="h",
        marker_color=[DANGER if p in ("Do nothing", "Target everyone") else GOOD if "0.20" in p else NEUTRAL
                      for p in policy["policy"]],
        text=[f"${v:,.0f}" for v in policy["total_cost"]], textposition="outside",
    ))
    fig.update_layout(title=f"Total campaign cost by policy (test set, n={s['n_test']:,} customers)",
                       xaxis_title="Total cost ($)", height=380, margin=dict(l=180))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Recommended policy cost", f"${policy.loc[policy['policy'].str.contains('0.20'), 'total_cost'].iloc[0]:,.0f}")
    c2.metric("Savings vs. doing nothing", f"${s['savings_recommended_vs_do_nothing']:,.0f}")
    c3.metric("Savings vs. untuned default", f"${s['savings_recommended_vs_default']:,.0f}")

    st.markdown("---")
    st.subheader("What this threshold means in practice")
    thresholds = data["thresholds"]
    thresholds_display = thresholds.copy()
    thresholds_display["policy"] = thresholds_display["policy"]
    for col in ["precision", "recall", "f1"]:
        thresholds_display[col] = (thresholds_display[col] * 100).round(1).astype(str) + "%"
    thresholds_display["threshold"] = thresholds_display["threshold"].round(2)
    st.dataframe(
        thresholds_display.rename(columns={
            "policy": "Policy", "threshold": "Threshold", "precision": "Precision",
            "recall": "Recall (churners caught)", "f1": "F1",
        }),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        f"At the recommended threshold (0.20), the model catches **{s['recall_at_020']*100:.0f}%** of actual "
        f"churners, at **{s['precision_at_020']*100:.0f}%** precision — meaning roughly "
        f"1 in {round(1/s['precision_at_020'])} customers targeted actually would have churned. That's the "
        f"intended tradeoff: cheap offers make it worth casting a somewhat wide net to avoid missing revenue-at-risk customers."
    )

    st.subheader("Recommended next steps")
    st.markdown("""
1. **Pilot the campaign** on the top-scoring 20-30% of active customers (by predicted churn probability) for one billing cycle, with a control group held out to measure actual offer effectiveness.
2. **Prioritize by segment**: month-to-month contracts and customers under 12 months tenure first — that's where both churn risk and total customer volume are highest.
3. **Investigate the fiber-optic and electronic-check signals** — these look like service quality / payment friction issues, not just demographics, and may be fixable independent of any retention offer.
4. **Re-validate offer economics** (the \$50/\$250 assumption) with actual finance/marketing numbers before scaling the campaign — the recommended threshold moves directly with that ratio.
    """)

# ============================================================== Model Performance (Appendix)
else:
    st.title("Model Performance — Technical Appendix")
    st.caption(f"Model: {s['model_name']} · trained on {s['n_customers'] - s['n_test']:,} customers, evaluated on {s['n_test']:,} held out")

    col1, col2 = st.columns(2)

    with col1:
        roc = data["roc"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name=f"Model (AUC={s['roc_auc']})",
                                  line=dict(color=PRIMARY, width=3)))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random guess",
                                  line=dict(color=NEUTRAL, dash="dash")))
        fig.update_layout(title="ROC curve", xaxis_title="False Positive Rate", yaxis_title="True Positive Rate", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        rel = data["reliability"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rel["predicted"], y=rel["observed"], mode="lines+markers",
                                  name="Model", line=dict(color=PRIMARY, width=3)))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfectly calibrated",
                                  line=dict(color=NEUTRAL, dash="dash")))
        fig.update_layout(title="Reliability diagram (calibration)", xaxis_title="Predicted probability",
                           yaxis_title="Observed churn rate", height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Confusion matrix at recommended threshold (0.20)")
    cm = data["cm"]
    fig = px.imshow(cm.values, text_auto=True, x=cm.columns, y=cm.index, color_continuous_scale="Blues")
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Full methodology — data cleaning, model comparison (Logistic Regression / Random Forest / "
        "Gradient Boosting / XGBoost), threshold tuning, cost-based optimization, and calibration checks — "
        "is documented in the accompanying Jupyter notebook, telco_churn_analysis.ipynb."
    )
