## 📊 1. Network KPI Analysis (CS & PS Layers)

| Circuit-Switched (CS) KPIs Analysis | Packet-Switched (PS) KPIs Analysis |
| :---: | :---: |
| <img src="images/cs.png" alt="CS KPI Analysis Dashboard" width="100%"/> | <img src="images/ps.jpg" alt="PS KPI Analysis Dashboard" width="100%"/> |

---

## 📈 2. PRB Utilization Modeling (Linear Regression)

<div align="center">
  <img src="images/linear_regression.png" alt="PRB vs Traffic Linear Regression" width="85%"/>
</div>

$$\text{PRB Downlink Utilization (\%)} = 1.277 \times \text{Traffic (GB)} + 5.99 \quad (R^2 = 0.832)$$

---

## 🔮 3. Time-Series Traffic Forecasting Models

### A. XGBoost Regressor (Selected Primary Model)

| 2026 Traffic Forecast | Expanding-Window Cross-Validation |
| :---: | :---: |
| <img src="images/xgboost_forecast_2026.jpg" alt="XGBoost 2026 Forecast" width="100%"/> | <img src="images/xgboost_validation.jpg" alt="XGBoost Cross Validation" width="100%"/> |

---

### B. Prophet Model

| Prophet 2026 Forecast | Prophet 2025 Holdout Validation |
| :---: | :---: |
| <img src="images/prophet_2026_forecast.png" alt="Prophet 2026 Forecast" width="100%"/> | <img src="images/prophet_2025_validation.jpg" alt="Prophet 2025 Validation" width="100%"/> |

---

### C. Holt-Winters Exponential Smoothing

| Holt-Winters 2026 Forecast | Holt-Winters 2025 Holdout Validation |
| :---: | :---: |
| <img src="images/holtwinter_2026_forecasting.png" alt="Holt-Winters 2026 Forecast" width="100%"/> | <img src="images/holtwinter_2025_validation.png" alt="Holt-Winters 2025 Validation" width="100%"/> |
