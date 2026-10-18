# Telecom KPI Analysis, XGBoost Forecasting & Capacity Planning

An end-to-end Python telecom application and interactive Jupyter GUI dashboard[cite: 5]. The project analyzes Circuit-Switched (CS) voice and Packet-Switched (PS) data Key Performance Indicators (KPIs), forecasts network-level traffic growth using **XGBoost**, models site-level Physical Resource Block (PRB) utilization with linear regression and adaptive IQR outlier cleaning, and automatically triggers hierarchical site capacity upgrades[cite: 5, 7].

---

## 📌 Key Features

- **Multi-Layer KPI Analysis**: Analyzes CS KPIs (Availability, Call Drop Rate - CDR, Call Setup Success Rate - CSSR) and PS KPIs (Data Traffic, Throughput, PRB DL Utilization, E-RAB Drop Rate, Handover Success Rate) across regions and time horizons[cite: 5, 7].
- **XGBoost Time-Series Forecasting**: Log-growth XGBoost forecaster evaluated using expanding-window rolling cross-validation and backtesting against Holt-Winters, Prophet, and Seasonal-Naive baselines[cite: 5, 7]. Includes 95% bootstrap confidence intervals[cite: 5, 7].
- **PRB Utilization Modeling**: Linear regression mapping traffic payload (GB) to PRB utilization (%) after OLS residual filtering via Interquartile Range ($1.5 \times \text{IQR}$), achieving $R^2 > 0.80$[cite: 5, 7].
- **Automated Upgrade Decision Engine**: Reconfiguration and expansion flow for sites exceeding a 70% PRB downlink threshold, mapping site transitions through a predefined hardware hierarchy[cite: 5, 7].
- **Dual Execution Modes**: Interactive `ipywidgets` dashboard for Jupyter Notebooks alongside a standalone command-line Python script that generates visual figures and multi-tab Excel reports[cite: 5].

---

## 📊 Analytical Model & Pipeline Summary

$$\text{PRB Utilization (\%)} = 1.2768 \times \text{Traffic (GB)} + 5.9872 \quad (R^2 = 0.8324)$$
[cite: 7]

1. **Traffic Growth**: Dec 2025 baseline ($2,000 \text{ TB/day}$) $\rightarrow$ Dec 2026 forecast ($2,780.34 \text{ TB/day}$), representing a **+39.12% YoY increase** (Growth Factor: $1.3912$)[cite: 7].
2. **Action Threshold**: PRB Downlink Utilization $> 70\%$[cite: 5, 7].
3. **Upgrade Hierarchy Ladder**:
   $$\text{Normal 3 Sectors} \rightarrow \text{Normal 4 Sectors} \rightarrow \text{FDD M-MIMO} \rightarrow \text{TDD 1st Carrier} \rightarrow \text{TDD 2nd Carrier} \rightarrow \text{TDD M-MIMO} \rightarrow \text{Expand Site}$$
[cite: 5, 7]
4. **Capacity Recommendations**: Identifies **52 saturated sites** exceeding threshold (43 reconfigurations, 9 physical site expansions)[cite: 7].

---

## 📁 Repository Structure

```text
telecom-capacity-forecasting/
├── Capacity_Planning_GUI.ipynb  # Interactive Jupyter Notebook with ipywidgets GUI
├── capacity_planning_app.py     # Standalone Python script for pipeline execution
├── requirements.txt             # Python environment dependencies
├── .gitignore                   # Ignores venv, raw excel datasets, and output folders
├── README.md                    # Project documentation
└── pipeline_outputs/            # Output directory generated at runtime
    ├── network_forecast.png     # Historical vs 2026 XGBoost forecast plot
    ├── prb_regression.png       # OLS linear regression scatter plot with IQR outliers
    ├── upgrades.png             # PRB distribution histogram & upgrade step breakdown
    └── capacity_plan_dec2026.xlsx # Multi-tab executive report
```[cite: 5]

---

## ⚙️ Installation & Setup

### 1. Clone Repository
```bash
git clone [https://github.com/](https://github.com/)<your-username>/telecom-capacity-forecasting.git
cd telecom-capacity-forecasting
