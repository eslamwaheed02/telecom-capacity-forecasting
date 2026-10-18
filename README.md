# Telecom KPI Analysis & Capacity Forecast

An end-to-end telecom capacity planning application. It analyzes historical Key Performance Indicators (KPIs), forecasts network data traffic using **XGBoost**, predicts site-level PRB (Physical Resource Block) utilization using regression with adaptive IQR outlier cleaning, and automatically recommends network upgrades.

## Key Features
- **KPI Analysis**: Descriptive statistics, regional breakdowns, and correlations for Circuit Switched (CS) and Packet Switched (PS) network layers.
- **Traffic Forecasting**: Log-growth XGBoost model with backtesting, expanding-window rolling cross-validation, and bootstrap confidence intervals.
- **PRB Modeling**: Linear regression linking data traffic to PRB utilization ($R^2 > 0.80$).
- **Upgrade Flow**: Automatic reconfiguration and upgrade classification for sites exceeding target threshold (PRB > 70%).
- **Interactive GUI**: Built-in `ipywidgets` interface for interactive filtering in Jupyter.

## Project Structure
- `Capacity_Planning_GUI.ipynb`: Interactive Jupyter Notebook with embedded GUI dashboard.
- `capacity_planning_app.py`: Command-line interface script to run the full pipeline and generate reports.
- `pipeline_outputs/`: Automatically created directory containing generated charts and Excel summaries.

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/telecom-capacity-forecasting.git
   cd telecom-capacity-forecasting