<div align="center">

# 📶 Telecom KPI Analysis, XGBoost Forecasting & Automated Capacity Planning Engine

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-v1.7%2B-orange.svg)
![Prophet](https://img.shields.io/badge/Prophet-v1.1%2B-lightgrey.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-FF6F00.svg)
![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen.svg)

**An end-to-end AI/ML network engineering framework for Circuit-Switched (CS) and Packet-Switched (PS) KPI analysis, multi-model traffic forecasting, PRB resource regression, and automated site configuration upgrade planning.**

---

</div>

## 📋 Executive Overview

Mobile network operators face rapidly growing data traffic demands. Expanding physical site infrastructure without predictive modeling leads to inefficient Capital Expenditure (CapEx), while delayed upgrades cause cell congestion and degraded Quality of Service (QoS).

This repository delivers an automated telecom capacity planning pipeline:
1. **Multi-Layer KPI Assessment**: Evaluates 2G/3G Voice metrics (CSSR, CDR, Availability) and 4G Data performance (Throughput, PRB Utilization, E-RAB Drop Rate, Handover Success Rate) across 5 geographic regions.
2. **Multi-Model Time-Series Forecasting**: Evaluates **XGBoost Regressor**, **Meta Prophet**, and **Holt-Winters Exponential Smoothing** across expanding-window backtesting folds to project 12-month traffic through December 2026.
3. **Resource Regression Modeling**: Maps payload growth to Physical Resource Block (PRB) Downlink Utilization using Ordinary Least Squares (OLS) regression after dynamic Interquartile Range ($1.5 \times \text{IQR}$) outlier cleaning ($R^2 = 0.832$).
4. **Automated Hardware Upgrade Engine**: Translates macro traffic forecasts down to site-level PRB utilization, evaluates cells against a **70% PRB congestion threshold**, and automatically steps site hardware up a 7-stage configuration ladder.

---

## ⚙️ End-to-End System Architecture

```mermaid
flowchart TD
    A[Raw Input Data: Multi-Sheet Excel] --> B[Data Cleaning & Dynamic IQR Outlier Filter]
    B --> C1[CS & PS Regional KPI Dashboards]
    B --> C2[Time-Series Feature Engineering]
    
    C2 --> D1[XGBoost 2026 Traffic Forecast]
    C2 --> D2[Baseline Models: Prophet & Holt-Winters]
    
    D1 --> E[Calculate YoY Traffic Growth Factor: +39.12%]
    E --> F[Site-Level Dec 2026 Payload Projection]
    
    F --> G[OLS Linear Regression: Traffic Payload vs PRB %]
    G --> H{Projected PRB Load > 70%?}
    
    H -- Yes --> I[Trigger Upgrade Engine: Step Up Hardware Ladder]
    H -- No --> J[Maintain Current Site Configuration]
    
    I --> K[Export Visual Visualizations & Executive Excel Report]
    J --> K
