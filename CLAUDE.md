# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This directory currently contains only the raw dataset — there is no code, notebooks, scripts, or environment/dependency files yet:

- `WA_Fn-UseC_-Telco-Customer-Churn.csv` — IBM's Telco Customer Churn dataset. 21 columns: `customerID`, demographics (`gender`, `SeniorCitizen`, `Partner`, `Dependents`), account/service info (`tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`), billing (`MonthlyCharges`, `TotalCharges`), and the target label `Churn` (Yes/No).

There are no build, lint, or test commands to document, and no architecture to describe yet since no analysis code exists.

Re-run `/init` once code (e.g. a notebook, training scripts, or an app) is added, so this file can be updated with real commands and structure.
