<div align="center">

# 📶 Telecom KPI Analysis, XGBoost Forecasting & Automated Capacity Planning Engine

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-v1.7%2B-orange.svg)
![Prophet](https://img.shields.io/badge/Prophet-v1.1%2B-lightgrey.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-FF6F00.svg)
![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen.svg)

**An end-to-end AI/ML framework for Circuit-Switched (CS) & Packet-Switched (PS) KPI assessment, multi-model traffic forecasting, PRB resource regression modeling, and automated site-level hardware upgrade recommendation.**

---

</div>

## 📋 Executive Overview

Mobile network operators face exponentially growing data demand. Expanding infrastructure blindly leads to wasted Capital Expenditure (CapEx), while delayed expansion causes network congestion and degraded Quality of Service (QoS). 

This project delivers a complete, automated end-to-end Telecom Capacity Planning & Optimization pipeline:
1. **Network Health Assessment**: Monitors 2G/3G CS Voice metrics (CSSR, CDR, Availability) and 4G PS Data metrics (Throughput, PRB Utilization, E-RAB Drop Rate, Handover Success Rate) across 5 geographical regions.
2. **Multi-Model Traffic Forecasting**: Compares **XGBoost Regressor**, **Meta Prophet**, and **Holt-Winters Exponential Smoothing** using expanding-window backtesting to forecast 12-month network traffic through December 2026.
3. **Resource Utilization Modeling**: Fits Ordinary Least Squares (OLS) regression between Traffic (GB) and PRB DL Utilization (%) after automated Interquartile Range ($1.5 \times \text{IQR}$) residual outlier rejection ($R^2 = 0.832$).
4. **Rule-Based Capacity Upgrade Engine**: Projects 2026 traffic to individual site cells, checks against a **70% PRB utilization threshold**, and automatically steps site configurations up a 7-stage hardware upgrade ladder.

---

## ⚙️ End-to-End System Architecture

```mermaid
flowchart TD
    A[Raw Input Data: Excel Workbook] --> B[Data Cleaning & Dynamic IQR Outlier Filter]
    B --> C1[CS & PS KPI Performance Dashboards]
    B --> C2[Time-Series Feature Engineering]
    
    C2 --> D1[XGBoost 2026 Traffic Forecast]
    C2 --> D2[Baseline Models: Prophet & Holt-Winters]
    
    D1 --> E[Calculate YoY Growth Factor: +39.12%]
    E --> F[Site-Level Dec 2026 Traffic Projection]
    
    F --> G[OLS Linear Regression: Traffic vs PRB %]
    G --> H{Projected PRB > 70%?}
    
    H -- Yes --> I[Trigger Upgrade Engine: Step Up Configuration Ladder]
    H -- No --> J[Maintain Current Hardware Layout]
    
    I --> K[Export Visual Visualizations & Multi-Tab Excel Report]
    J --> K
