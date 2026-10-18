<div align="center">

# 📶 Telecom KPI Analysis, XGBoost Forecasting & Capacity Planning

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-v1.7%2B-orange.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-FF6F00.svg)
![Status](https://img.shields.io/badge/status-Production--Ready-brightgreen.svg)

**An end-to-end AI/ML network planning application for Circuit-Switched (CS) and Packet-Switched (PS) KPI analysis, time-series data forecasting, PRB utilization modeling, and automated site upgrade decisions.**

---

</div>

## 📋 Table of Contents
- [Executive Overview](#-executive-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Analytical Pipeline & Benchmark Results](#-analytical-pipeline--benchmark-results)
- [Repository Structure](#-repository-structure)
- [Dataset Specifications](#-dataset-specifications)
- [Installation & Setup](#-installation--setup)
- [Usage Guide](#-usage-guide)
- [Outputs & Generated Reports](#-outputs--generated-reports)
- [License](#-license)

---

## 🚀 Executive Overview

Mobile network traffic growth requires precise forward-looking capacity planning to prevent congestion while optimizing capital expenditure (CapEx). This project implements a full-stack telemetry and machine learning pipeline:

1. **Traffic Forecasting**: Predicts network-wide daily traffic 12 months ahead (through December 2026) using an autoregressive **XGBoost Regressor** validated against Prophet, Holt-Winters, and Seasonal Naive baselines.
2. **Resource Modeling**: Fits Ordinary Least Squares (OLS) linear regression mapping traffic payload to Physical Resource Block (PRB) Downlink Utilization after automated Interquartile Range ($1.5 \times \text{IQR}$) residual cleaning.
3. **Upgrade Decision Engine**: Evaluates individual site loads against a 70% PRB threshold and automatically schedules targeted hardware reconfigurations or physical site expansions along a predefined configuration hierarchy.

---

## ✨ Key Features

- **Multi-Layer KPI Assessment**: Evaluates Circuit-Switched voice metrics (CSSR, CDR, Availability) and Packet-Switched data metrics (Data Traffic, Throughput, PRB Utilization, E-RAB DR, HO SR) across 5 geographic regions.
- **Leak-Free Expanding-Window Validation**: Backtested over 3 historical test folds (2023, 2024, 2025) with hyperparameter tuning to ensure zero target leakage.
- **Automated Outlier Rejection**: Applies dynamic residual IQR filtering to purge corrupted measurements, achieving $R^2 = 0.8324$.
- **Rule-Based Capacity Engine**: Automatically advances high-utilization cells along a 7-stage configuration ladder.
- **Dual Runtime Interface**: Supports automated background CLI execution (`capacity_planning_app.py`) and an interactive widget GUI in Jupyter (`Capacity_Planning_GUI.ipynb`).

---

## ⚙️ System Architecture

```mermaid
flowchart TD
    A[Raw Input Data: Excel Workbook] --> B[Data Cleaning & IQR Outlier Filter]
    B --> C1[CS & PS KPI Analytics Dashboard]
    B --> C2[Time-Series Feature Engineering]
    
    C2 --> D1[XGBoost 2026 Traffic Forecast]
    C2 --> D2[Baseline Models: Prophet / Holt-Winters]
    
    D1 --> E[Calculate YoY Growth Factor: +39.12%]
    E --> F[Site-Level Dec 2026 Traffic Projection]
    
    F --> G[Linear Regression: Traffic vs PRB %]
    G --> H{Projected PRB > 70%?}
    
    H -- Yes --> I[Trigger Upgrade Engine: Ladder Step Up]
    H -- No --> J[Maintain Current Site Configuration]
    
    I --> K[Export PNG Visuals & Multi-Tab Excel Report]
    J --> K
