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
telecom-capacity-forecasting/
├── Capacity_Planning_GUI.ipynb   # Interactive Jupyter Notebook dashboard GUI
├── capacity_planning_app.py      # Automated CLI pipeline execution script
├── requirements.txt              # Environment dependencies
├── README.md                     # Project documentation
├── images/                       # Local image assets directory
│   ├── cs.png
│   ├── ps.jpg
│   ├── linear_regression.png
│   ├── xgboost_forecast_2026.jpg
│   ├── xgboost_validation.jpg
│   ├── prophet 2023 validation.jpg
│   ├── prophet 2024 validation.jpg
│   ├── prophet_2025_validation.jpg
│   ├── prophet_2026_forecast.png
│   ├── holtwinter_2026_forecasting.png
│   └── holtwinter_2025_validation.png
└── pipeline_outputs/             # Automatically generated at runtime
    ├── network_forecast.png
    ├── prb_regression.png
    ├── upgrades.png
    └── capacity_plan_dec2026.xlsx # Multi-sheet executive Excel report
    # 1. Clone repository
git clone [https://github.com/hatemhamid/Telecom-kpi-analysis-and-capacity-planning.git](https://github.com/hatemhamid/Telecom-kpi-analysis-and-capacity-planning.git)
cd Telecom-kpi-analysis-and-capacity-planning

# 2. Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
# Option 1: Run complete background pipeline via CLI
python capacity_planning_app.py

# Option 2: Launch interactive GUI in Jupyter Notebook
jupyter notebook Capacity_Planning_GUI.ipynb
<ElicitationsGroup>
  <Elicitation prompt="How to add GitHub project badges or workflow status tags?" title="Add workflow badges?"/>
  <Elicitation prompt="Generate an MIT LICENSE file content for this repository." title="Generate LICENSE file?"/>
</ElicitationsGroup>
