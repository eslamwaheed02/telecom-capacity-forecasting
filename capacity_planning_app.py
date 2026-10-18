"""Capacity-planning application - everything in one file.

Contents
--------
  Forecasting  : XGBoost log-growth forecaster, backtest, rolling CV (from src/forecasting.py)
  Pipeline     : load -> KPI analysis -> XGBoost forecast -> Dec-25 -> Dec-26 growth -> site traffic
                 -> IQR cleaning (clean_final.py) -> PRB linear regression (R2 > 0.8)
                 -> upgrade flow for sites with PRB > 70 %
  GUI          : ipywidgets interface (Analysis / Forecast / Both, regions, months)

Use
---
  Notebook :  launch()                  # opens the GUI
  Terminal :  python capacity_planning_app.py          # runs the pipeline and saves outputs
"""
# %% Imports
import re
import warnings
import datetime as dt
import base64
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

try:
    ROOT = Path(__file__).resolve().parent
except NameError:  # running inside a notebook
    ROOT = Path.cwd()

# Forecast settings (formerly src/config.py)
HORIZON = 12
BACKTEST_START = "2025-01-01"
# (train_start, train_end, validation_start, validation_end) - expanding window
FOLDS = [
    ("2020-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("2020-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2020-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
]
MODELS = ["XGBoost"]

# %% Settings and configuration ladder
# --------------------------------------------------------------------------- settings
DATA_FILE = ROOT / "Project Data - Traffic & KPIs.xlsx"
OUT_DIR = ROOT / "pipeline_outputs"

TRAFFIC_RAW = "Data Traffic (TB)"      # column name in the workbook (clean_final.py)
PRB_RAW = "PRB DL Utilization"
PRB_THRESHOLD = 70.0                   # % - sites above this are upgraded
MIN_R2 = 0.80                          # regression must reach this R^2
IQR_FACTOR = 1.5                       # clean_final.py default
IQR_FACTORS_TO_TRY = (1.5, 2.0, 2.5, 3.0)  # fallback widening if R^2 < MIN_R2
BASE_MONTH, TARGET_MONTH = "2025-12", "2026-12"

HIERARCHY = [
    "Normal Sites 3 Sectors",
    "Normal Sites 4 Sectors",
    "FDD M-MIMO",
    "TDD 1st Carrier",
    "TDD 2nd Carrier",
    "TDD M-MIMO",
    "Expand site",
]
UPGRADE_MAP = {HIERARCHY[i]: HIERARCHY[i + 1] for i in range(len(HIERARCHY) - 1)}
UPGRADE_MAP["Expand site"] = "Expand site"  # top of the ladder



# %% Forecasting - XGBoost (backtest, rolling cross-validation)
def _metrics(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return {
        "MAPE": float(np.mean(np.abs((actual - pred) / actual)) * 100),
        "RMSE": float(np.sqrt(mean_squared_error(actual, pred))),
        "MAE": float(mean_absolute_error(actual, pred)),
    }


def _make_xy(series: pd.Series, n_lags: int = 12):
    g = np.log(series).diff()
    df = pd.DataFrame({"g": g})
    for k in range(1, n_lags + 1):
        df[f"lag{k}"] = df["g"].shift(k)
    df["roll3"] = df["g"].shift(1).rolling(3).mean()
    df["roll6"] = df["g"].shift(1).rolling(6).mean()
    df["roll12"] = df["g"].shift(1).rolling(12).mean()
    df["month"] = df.index.month
    return df.dropna()


def forecast_xgb(train: pd.Series, horizon: int = HORIZON, n_boot: int = 60, seed: int = 0):
    from xgboost import XGBRegressor
    data = _make_xy(train)
    X, y = data.drop(columns="g"), data["g"]
    params = dict(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.9,
                  colsample_bytree=0.8, random_state=seed, objective="reg:squarederror")
    model = XGBRegressor(**params).fit(X, y)
    resid = (y - model.predict(X)).values
    rng = np.random.default_rng(seed)

    def roll(noise):
        hist = list(np.log(train.values))
        idx = list(train.index)
        out = []
        for h in range(horizon):
            gs = pd.Series(np.diff(hist))
            nxt = idx[-1] + pd.offsets.MonthBegin(1)
            row = {f"lag{k}": gs.iloc[-k] for k in range(1, 13)}
            row["roll3"], row["roll6"], row["roll12"] = gs.iloc[-3:].mean(), gs.iloc[-6:].mean(), gs.iloc[-12:].mean()
            row["month"] = nxt.month
            gpred = float(model.predict(pd.DataFrame([row])[X.columns])[0])
            if noise:
                gpred += rng.choice(resid)
            hist.append(hist[-1] + gpred)
            idx.append(nxt)
            out.append(np.exp(hist[-1]))
        return np.array(out), idx[-horizon:]

    point, dates = roll(False)
    sims = np.array([roll(True)[0] for _ in range(n_boot)])
    lo, hi = np.percentile(sims, [2.5, 97.5], axis=0)
    return pd.DataFrame({"forecast": point, "lower_95": np.minimum(lo, point),
                         "upper_95": np.maximum(hi, point)}, index=pd.DatetimeIndex(dates))


FORECASTERS = {"XGBoost": forecast_xgb}


def seasonal_naive_baseline(train: pd.Series, horizon: int = 12) -> np.ndarray:
    """Same month last year x average YoY growth of last 12 months."""
    last = train.iloc[-12:].values
    yoy = train.iloc[-12:].values / train.iloc[-24:-12].values
    return last * yoy.mean()


# ------------------------------------------------------------------ backtest
def backtest(series: pd.Series, test_start: str = BACKTEST_START):
    """Train on data before test_start, predict the next 12 months.
    Returns (metrics DataFrame, predictions DataFrame)."""
    train, test = series[series.index < test_start], series[series.index >= test_start].iloc[:12]
    preds, rows = {}, []
    for name, fn in FORECASTERS.items():
        fc = fn(train, len(test))
        preds[name] = fc["forecast"].reindex(test.index).values
        rows.append({"model": name, **_metrics(test.values, preds[name])})
    base = seasonal_naive_baseline(train)
    preds["Seasonal-naive"] = base
    rows.append({"model": "Seasonal-naive", **_metrics(test.values, base)})
    return pd.DataFrame(rows), pd.DataFrame(preds, index=test.index).assign(actual=test.values)


def rolling_cv(series: pd.Series, folds=FOLDS, return_folds: bool = False):
    """Expanding-window CV on fixed date folds (see config.FOLDS).
    Each model (incl. XGBoost) is trained on the fold's train window and scored on its validation window.
    Returns average MAPE per model as CV_MAPE; if return_folds also returns
    (per-fold metrics, per-fold validation predictions)."""
    rows, preds = [], []
    for i, (tr_start, tr_end, va_start, va_end) in enumerate(folds, start=1):
        train = series[(series.index >= tr_start) & (series.index <= tr_end)]
        test = series[(series.index >= va_start) & (series.index <= va_end)]
        for name, fn in FORECASTERS.items():
            fc = fn(train, len(test))
            p = fc["forecast"].values
            rows.append({"fold": i, "model": name, **_metrics(test.values, p)})
            preds.append(pd.DataFrame({"fold": i, "model": name, "date": test.index, "actual": test.values,
                                       "forecast": p, "lower_95": fc["lower_95"].values,
                                       "upper_95": fc["upper_95"].values}))
    detail = pd.DataFrame(rows)
    cv = detail.groupby("model")["MAPE"].mean().rename("CV_MAPE").reset_index()
    return (cv, detail, pd.concat(preds, ignore_index=True)) if return_folds else cv


def select_best(metrics: pd.DataFrame, cv: pd.DataFrame) -> str:
    """Lowest mean of holdout-MAPE and CV-MAPE among the active models (XGBoost only)."""
    m = metrics[metrics["model"].isin(MODELS)].drop(columns=["CV_MAPE"], errors="ignore").merge(cv, on="model")
    m["score"] = (m["MAPE"] + m["CV_MAPE"]) / 2
    return m.sort_values("score").iloc[0]["model"]


def fit_best_and_forecast(series: pd.Series, model_name: str, horizon: int = HORIZON):
    return FORECASTERS[model_name](series, horizon)



# %% Data loading
def load_network_traffic(path=None) -> pd.Series:
    """Monthly network traffic (TB/day), month-start index 2020-01..2025-12."""
    df = pd.read_excel(path or DATA_FILE, sheet_name="Network Traffic")
    df.columns = ["Date", "Traffic"]
    df["Date"] = pd.to_datetime(df["Date"])
    idx = pd.date_range("2020-01-01", periods=len(df), freq="MS")  # rebuild a continuous month-start index
    return pd.Series(df["Traffic"].astype(float).values, index=idx, name="traffic_tb_daily")



# %% Step 1 - Load data
def load_data(path: Path = DATA_FILE) -> dict:
    """Raw sheets (headers stripped) plus the network-level monthly series."""
    sheets = {}
    for name in ["PS KPIs", "CS KPIs", "Sites Configurations"]:
        df = pd.read_excel(path, sheet_name=name)
        df.columns = [str(c).strip() for c in df.columns]
        sheets[name] = df
    cfg = sheets["Sites Configurations"].rename(columns={"Confgurations": "Configuration"})
    cfg["Configuration"] = cfg["Configuration"].astype(str).str.strip()
    sheets["Sites Configurations"] = cfg
    net = load_network_traffic(path)
    return {"ps": sheets["PS KPIs"], "cs": sheets["CS KPIs"], "config": cfg, "network": net}



# %% Step 2 - KPI analysis
# Code below is taken from KPI_Analysis_and_Forecast_v2 (1).ipynb (sections S2, S3, A1, A2),
# stripped of widgets so it can run as a script.
CS_KPIS = ["Availability", "CDR", "CSSR", "CS Traffic - Total", "ICM"]
PS_KPIS = ["Data Traffic (GB)", "Data CSSR", "Throughput (Mbps)", "ERAB DR", "HO SR", "PRB DL Utilization"]
PERCENT_KPIS = ["Availability", "CDR", "CSSR", "Data CSSR", "ERAB DR", "HO SR", "PRB DL Utilization"]
THROUGHPUT, TRAFFIC, PRB = "Throughput (Mbps)", "Data Traffic (GB)", "PRB DL Utilization"
HIGHER_IS_BETTER = {"Availability": True, "CDR": False, "CSSR": True, "Data CSSR": True,
                    THROUGHPUT: True, "ERAB DR": False, "HO SR": True, "PRB DL Utilization": False}


def clean_header(value):
    return " ".join(str(value).replace("\xa0", " ").split())


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", clean_header(value).lower())


ALIASES = {header_key(c): c for c in ["Site ID", "Region", "Y-M", "Configuration", "Effective Date"] + CS_KPIS + PS_KPIS}
ALIASES.update({"site": "Site ID", "siteid": "Site ID", "month": "Y-M", "date": "Y-M", "yearmonth": "Y-M",
                "area": "Region", "throughput": THROUGHPUT, "datatraffic": TRAFFIC,
                "datatraffictb": TRAFFIC,  # legacy workbook header; values are already GB
                "prb": "PRB DL Utilization"})


def canonical_header(value):
    key = header_key(value)
    return "Configuration" if key.startswith("conf") else ALIASES.get(key, clean_header(value))


def parse_month(value):
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (dt.date, dt.datetime, pd.Timestamp, np.datetime64)):
        stamp = pd.Timestamp(value)
    else:
        text = str(value).strip()
        stamp = pd.NaT
        for fmt in ["%Y-%m", "%Y/%m", "%Y%m", "%Y-%m-%d", "%Y/%m/%d", "%b-%Y", "%B-%Y", "%b %Y", "%B %Y"]:
            try:
                stamp = pd.Timestamp(dt.datetime.strptime(text, fmt))
                break
            except ValueError:
                pass
    if pd.isna(stamp) or not 2000 <= stamp.year <= 2100:
        return pd.NaT
    return stamp.to_period("M").to_timestamp()


def normalize_kpi_sheet(raw: pd.DataFrame, role: str) -> pd.DataFrame:
    """Notebook S3 policy: exact duplicates removed, conflicting site-months excluded,
    invalid KPI values -> NaN, zeros retained, no imputation."""
    frame = raw.copy()
    frame.columns = [canonical_header(c) for c in frame.columns]
    metrics = [k for k in (PS_KPIS if role == "PS" else CS_KPIS) if k in frame]
    frame["Site ID"] = frame["Site ID"].astype("string").str.strip()
    frame["Region"] = frame["Region"].astype("string").str.strip().str.upper()
    frame["Month"] = frame["Y-M"].map(parse_month)
    for col in metrics:
        numeric = pd.to_numeric(frame[col].astype("string").str.replace("%", "", regex=False).str.strip(),
                                errors="coerce").astype(float)
        invalid = (numeric < 0) | (~np.isfinite(numeric) & numeric.notna())
        if col in PERCENT_KPIS:
            invalid |= numeric > 100
        frame[col] = numeric.mask(invalid)
    frame = frame.dropna(subset=["Site ID", "Region", "Month"])
    frame = frame.loc[~frame.duplicated(["Site ID", "Month"] + metrics)]
    frame = frame.loc[~frame.duplicated(["Site ID", "Month"], keep=False)]
    frame["Y-M"] = frame["Month"].dt.strftime("%Y-%m")
    return frame[["Site ID", "Region", "Y-M", "Month"] + metrics].reset_index(drop=True)


def descriptive_statistics(frame, kpis):
    rows = []
    for k in kpis:
        s = frame[k].dropna()
        rows.append({"KPI": k, "Observations": len(s), "Sites": frame.loc[s.index, "Site ID"].nunique(),
                     "Mean": s.mean(), "Median": s.median(), "Min": s.min(), "Max": s.max(), "Std": s.std()})
    return pd.DataFrame(rows)


def region_summary(frame, kpi):
    return frame.groupby("Region")[kpi].agg(Observations="count", Mean="mean", Median="median",
                                            Min="min", Max="max", Std="std").reset_index()


def month_summary(frame, kpi):
    return frame.groupby("Month")[kpi].agg(Observations="count", Mean="mean", Median="median",
                                           Min="min", Max="max", Std="std").reset_index()


def site_summary(frame, kpi, min_months=3):
    valid = frame.dropna(subset=[kpi])
    s = valid.groupby(["Site ID", "Region"]).agg(Months=("Month", "nunique"), Mean=(kpi, "mean"),
                                                 Median=(kpi, "median"), Min=(kpi, "min"),
                                                 Max=(kpi, "max")).reset_index()
    ascending = HIGHER_IS_BETTER.get(kpi) is not False
    return s[s.Months >= min_months].sort_values("Mean", ascending=ascending)


def relationship(frame, x, y):
    from scipy import stats
    paired = frame[[x, y]].dropna()
    if len(paired) < 3 or paired[x].nunique() < 2 or paired[y].nunique() < 2:
        return {"X": x, "Y": y, "N": len(paired), "Note": "Insufficient pairs or constant input"}
    fit = stats.linregress(paired[x], paired[y])
    return {"X": x, "Y": y, "N": len(paired), "Pearson r": fit.rvalue,
            "Spearman rho": stats.spearmanr(paired[x], paired[y]).statistic, "R2": fit.rvalue ** 2,
            "Slope": fit.slope, "Intercept": fit.intercept,
            "Note": "Association, not causal evidence"}


def throughput_problem_sites(frame, threshold=5.0):
    valid = frame.dropna(subset=[THROUGHPUT]).copy()
    valid["Below"] = valid[THROUGHPUT] < threshold
    valid["Zero"] = valid[THROUGHPUT].eq(0)
    r = valid.groupby(["Site ID", "Region"]).agg(**{
        "Valid Months": ("Month", "nunique"), "Low Months": ("Below", "sum"), "Zero Months": ("Zero", "sum"),
        "Mean Throughput": (THROUGHPUT, "mean"), "Minimum Throughput": (THROUGHPUT, "min")}).reset_index()
    r["Low Months %"] = 100 * r["Low Months"] / r["Valid Months"]
    r["Persistent"] = (r["Valid Months"] >= 3) & (r["Low Months %"] >= 50)
    r["Threshold Mbps"] = threshold
    return r.sort_values(["Low Months %", "Mean Throughput"], ascending=[False, True])


def ps_multi_problem(frame, threshold=5.0):
    s = frame.groupby(["Site ID", "Region"])[[THROUGHPUT, PRB]].mean().reset_index()
    limit = s[PRB].quantile(0.9)
    s["High PRB Screening"] = s[PRB] >= limit
    return s[(s[THROUGHPUT] < threshold) & s["High PRB Screening"]]


def cs_problem_sites(frame):
    cols = [k for k in ["Availability", "CDR", "CSSR"] if k in frame]
    s = frame.groupby(["Site ID", "Region"])[cols].mean().reset_index()
    for k in cols:
        limit = s[k].quantile(0.9 if k == "CDR" else 0.1)
        s[k + " Screening"] = s[k] >= limit if k == "CDR" else s[k] <= limit
    s["Issue Count"] = s[[k + " Screening" for k in cols]].sum(axis=1)
    return s.sort_values("Issue Count", ascending=False)


def kpi_analysis(data: dict, threshold: float = 5.0) -> dict:
    """Historical (2025) KPI analysis tables for PS and CS data + configuration inventory."""
    ps = normalize_kpi_sheet(data["ps"], "PS")
    cs = normalize_kpi_sheet(data["cs"], "CS")
    tables = {}
    for role, frame, kpis in [("PS", ps, [k for k in PS_KPIS if k in ps]), ("CS", cs, [k for k in CS_KPIS if k in cs])]:
        tables[f"{role} Statistics"] = descriptive_statistics(frame, kpis)
        tables[f"{role} Regional Summary"] = pd.concat([region_summary(frame, k).assign(KPI=k) for k in kpis],
                                                       ignore_index=True)
        tables[f"{role} Monthly Summary"] = pd.concat([month_summary(frame, k).assign(KPI=k) for k in kpis],
                                                      ignore_index=True)
        tables[f"{role} Correlations"] = pd.DataFrame(
            [relationship(frame, x, y) for i, x in enumerate(kpis) for y in kpis[i + 1:]])
    tables["PS Site Rankings"] = pd.concat([site_summary(ps, k).assign(KPI=k) for k in [TRAFFIC, THROUGHPUT, PRB]],
                                           ignore_index=True)
    hist = throughput_problem_sites(ps, threshold)
    tables["Throughput Problem Sites"] = hist[hist["Low Months"] > 0]
    tables["PS Multi Problem"] = ps_multi_problem(ps, threshold)
    tables["CS Problem Sites"] = cs_problem_sites(cs)
    cfg = data["config"]
    inv = cfg.groupby("Configuration").agg(**{"Unique Sites": ("Site ID", "nunique")}).reset_index()
    inv["Sites %"] = 100 * inv["Unique Sites"] / cfg["Site ID"].nunique()
    tables["Configuration Inventory"] = inv
    tables["_ps_clean"], tables["_cs_clean"] = ps, cs
    return tables



# %% Step 3 - XGBoost network forecast
def forecast_network_traffic(net: pd.Series, run_validation: bool = True) -> dict:
    """XGBoost log-growth forecaster from src/forecasting.py: 12 months of 2026."""
    result = {}
    if run_validation:
        result["backtest_metrics"], result["backtest_preds"] = backtest(net)
        result["cv_metrics"], result["cv_detail"], _ = rolling_cv(net, return_folds=True)
    result["forecast"] = fit_best_and_forecast(net, "XGBoost")
    return result



# %% Step 4 - Dec 2025 to Dec 2026 growth factor
def december_growth_factor(net: pd.Series, forecast: pd.DataFrame) -> dict:
    dec25 = float(net.loc[pd.Timestamp("2025-12-01")])
    dec26 = float(forecast.loc[pd.Timestamp("2026-12-01"), "forecast"])
    return {"dec_2025": dec25, "dec_2026": dec26, "factor": dec26 / dec25, "increase_pct": (dec26 / dec25 - 1) * 100}



# %% Step 5 - Site traffic December 2026
def project_site_traffic(ps_raw: pd.DataFrame, factor: float) -> pd.DataFrame:
    """One row per site with a valid Dec-2025 reading; Dec-2026 traffic = Dec-2025 x factor."""
    kpis = ["Data CSSR", "Throughput (Mbps)", "ERAB DR", "HO SR", PRB_RAW]
    dec = ps_raw[ps_raw["Y-M"] == BASE_MONTH].copy()
    n_all = len(dec)
    dec = dec.drop_duplicates("Site ID")
    zero = (dec[kpis].fillna(0) == 0).all(axis=1)  # site down / no data
    dec = dec[~zero & dec[TRAFFIC_RAW].notna()].copy()
    out = dec[["Site ID", "Region", TRAFFIC_RAW, PRB_RAW]].rename(
        columns={TRAFFIC_RAW: "Traffic_Dec2025", PRB_RAW: "PRB_Dec2025"})
    out["Traffic_Dec2026"] = out["Traffic_Dec2025"] * factor
    out.attrs["dropped"] = {"rows_dec_2025": n_all, "no_data_or_duplicate": n_all - len(out)}
    return out.reset_index(drop=True)



# %% Step 6 - Data cleaning (clean_final.py)
def clean_ps_data(ps_raw: pd.DataFrame, factor: float = IQR_FACTOR):
    """Identical logic to clean_final.py: baseline OLS line -> residuals -> 1.5 x IQR filter."""
    df_ps = ps_raw.copy()
    X, y = df_ps[TRAFFIC_RAW], df_ps[PRB_RAW]
    slope, intercept = np.polyfit(X, y, 1)
    residuals = y - (slope * X + intercept)
    q1, q3 = residuals.quantile(0.25), residuals.quantile(0.75)
    iqr = q3 - q1
    mask = (residuals >= q1 - factor * iqr) & (residuals <= q3 + factor * iqr)
    return df_ps[mask].copy(), df_ps[~mask].copy()



# %% Step 7 - PRB linear regression
def fit_prb_model(ps_raw: pd.DataFrame, min_r2: float = MIN_R2):
    """Clean (IQR) then fit PRB = slope * traffic + intercept. If R^2 < min_r2 the IQR factor
    is widened step by step (clean_final.py note: factor 2.0 gives R^2 ~ 0.80)."""
    last = None
    for factor in IQR_FACTORS_TO_TRY:
        clean, removed = clean_ps_data(ps_raw, factor)
        X, y = clean[TRAFFIC_RAW], clean[PRB_RAW]
        r = X.corr(y)
        slope, intercept = np.polyfit(X, y, 1)
        last = {"iqr_factor": factor, "n_initial": len(ps_raw), "n_clean": len(clean),
                "n_outliers": len(removed), "r": float(r), "r2": float(r ** 2),
                "slope": float(slope), "intercept": float(intercept), "clean": clean, "removed": removed}
        if last["r2"] >= min_r2:
            return last
    raise RuntimeError(f"R^2 never reached {min_r2}; best was {last['r2']:.4f} (factor {last['iqr_factor']})")


def predict_prb(traffic: pd.Series, model: dict) -> pd.Series:
    return (model["slope"] * traffic + model["intercept"]).clip(lower=0, upper=100)



# %% Step 8 - Upgrade flow
def apply_upgrade_flow(sites: pd.DataFrame, config: pd.DataFrame, threshold: float = PRB_THRESHOLD) -> pd.DataFrame:
    """Sites with projected Dec-2026 PRB > threshold move one step up HIERARCHY."""
    out = sites.merge(config[["Site ID", "Configuration"]], on="Site ID", how="left")
    out["Configuration"] = out["Configuration"].fillna("Unknown")
    out["Upgrade Needed"] = out["PRB_Dec2026"] > threshold
    out["New Configuration"] = [UPGRADE_MAP.get(c, c) if need else c
                                for c, need in zip(out["Configuration"], out["Upgrade Needed"])]
    out["Action"] = np.where(~out["Upgrade Needed"], "No change",
                    np.where(out["Configuration"].isin(HIERARCHY),
                             np.where(out["New Configuration"] == "Expand site", "Expand site", "Reconfigure"),
                             "Verify configuration"))
    return out



# %% Plots
def plot_forecast(net, forecast):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(net.index, net.values, label="Actual", color="black")
    ax.plot(forecast.index, forecast["forecast"], "--", color="tab:red", label="XGBoost forecast 2026")
    ax.fill_between(forecast.index, forecast["lower_95"], forecast["upper_95"], color="tab:red", alpha=.15)
    ax.set_ylabel("TB / day"); ax.set_title("Network traffic: history and XGBoost forecast"); ax.legend()
    fig.tight_layout()
    return fig


def plot_regression(model):
    import matplotlib.pyplot as plt
    c, r = model["clean"], model["removed"]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(r[TRAFFIC_RAW], r[PRB_RAW], s=6, color="lightgrey", label="Outliers removed")
    ax.scatter(c[TRAFFIC_RAW], c[PRB_RAW], s=6, alpha=.4, label="Cleaned data")
    xs = np.linspace(0, c[TRAFFIC_RAW].max(), 50)
    ax.plot(xs, model["slope"] * xs + model["intercept"], color="red",
            label=f"PRB = {model['slope']:.3f}*T + {model['intercept']:.2f}  (R2={model['r2']:.3f})")
    ax.set_xlabel("Data traffic"); ax.set_ylabel("PRB DL utilization (%)"); ax.legend()
    ax.set_title("PRB vs traffic - linear regression"); fig.tight_layout()
    return fig


def plot_upgrades(result):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].hist(result["PRB_Dec2026"], bins=40, color="tab:blue", alpha=.8)
    axes[0].axvline(PRB_THRESHOLD, color="red", ls="--", label=f"{PRB_THRESHOLD:.0f}% threshold")
    axes[0].set_title("Projected PRB utilisation, Dec 2026"); axes[0].set_xlabel("%"); axes[0].legend()
    t = result[result["Upgrade Needed"]].groupby(["Configuration", "New Configuration"]).size()
    t = t.rename(lambda x: x).reset_index(name="n")
    labels = [f"{a}\n-> {b}" for a, b in zip(t["Configuration"], t["New Configuration"])]
    axes[1].barh(labels, t["n"], color="tab:orange"); axes[1].set_title("Upgrades by step"); axes[1].set_xlabel("Sites")
    fig.tight_layout()
    return fig



# %% Run the full pipeline (terminal / notebook)
def run(verbose: bool = True, save: bool = True, run_validation: bool = True) -> dict:
    OUT_DIR.mkdir(exist_ok=True)
    say = print if verbose else (lambda *a, **k: None)

    say("== 1. Load data ==")
    data = load_data()
    say(f"PS rows {len(data['ps'])}, CS rows {len(data['cs'])}, sites in config {len(data['config'])}, "
        f"network months {len(data['network'])}")

    say("== 2. KPI analysis ==")
    kpi = kpi_analysis(data)
    say(kpi["PS Statistics"].round(2).to_string(index=False))

    say("== 3. XGBoost network forecast ==")
    fc = forecast_network_traffic(data["network"], run_validation)
    if run_validation:
        say(fc["backtest_metrics"].round(2).to_string(index=False))
        say("Rolling-CV MAPE:", fc["cv_metrics"].round(2).to_dict("records"))

    say("== 4. Dec-2025 -> Dec-2026 growth ==")
    g = december_growth_factor(data["network"], fc["forecast"])
    say(f"Dec 2025 {g['dec_2025']:.0f}  ->  Dec 2026 {g['dec_2026']:.1f} TB/day  "
        f"(+{g['increase_pct']:.2f}%, factor {g['factor']:.4f})")

    say("== 5. Site traffic Dec-2026 ==")
    sites = project_site_traffic(data["ps"], g["factor"])
    say(f"{len(sites)} sites with valid Dec-2025 data  ({sites.attrs['dropped']})")

    say("== 6-7. Clean data + PRB regression ==")
    model = fit_prb_model(data["ps"])
    say(f"IQR factor {model['iqr_factor']}: kept {model['n_clean']}/{model['n_initial']} "
        f"(removed {model['n_outliers']}); r={model['r']:.4f}  R2={model['r2']:.4f}")
    say(f"PRB = {model['slope']:.4f} * Traffic + {model['intercept']:.4f}")
    assert model["r2"] > MIN_R2, "R2 must be above 0.8"
    sites["PRB_Dec2026"] = predict_prb(sites["Traffic_Dec2026"], model)

    say(f"== 8. Upgrade flow (PRB > {PRB_THRESHOLD:.0f}%) ==")
    result = apply_upgrade_flow(sites, data["config"])
    steps = (result[result["Upgrade Needed"]].groupby(["Configuration", "New Configuration", "Action"])
             .size().reset_index(name="Sites"))
    say(f"{int(result['Upgrade Needed'].sum())} of {len(result)} sites exceed {PRB_THRESHOLD:.0f}% PRB")
    say(steps.to_string(index=False))

    summary = pd.DataFrame([
        ("Dec 2025 network traffic (TB/day)", g["dec_2025"]), ("Dec 2026 forecast (TB/day)", g["dec_2026"]),
        ("Growth factor", g["factor"]), ("Increase (%)", g["increase_pct"]),
        ("Sites analysed", len(result)), ("Regression R2", model["r2"]), ("Regression slope", model["slope"]),
        ("Regression intercept", model["intercept"]), ("IQR factor used", model["iqr_factor"]),
        ("Cleaned / initial observations", f"{model['n_clean']} / {model['n_initial']}"),
        ("Sites with PRB > 70%", int(result["Upgrade Needed"].sum())),
        ("  of which Expand site", int((result["Action"] == "Expand site").sum())),
    ], columns=["Metric", "Value"])
    summary["Value"] = summary["Value"].astype(str)

    out = dict(data=data, kpi=kpi, forecast=fc, growth=g, sites=sites, model=model, result=result,
               steps=steps, summary=summary)

    if save:
        net = data["network"]
        for name, fig in [("network_forecast", plot_forecast(net, fc["forecast"])),
                          ("prb_regression", plot_regression(model)), ("upgrades", plot_upgrades(result))]:
            fig.savefig(OUT_DIR / f"{name}.png", dpi=130)
        import matplotlib.pyplot as plt
        plt.close("all")
        xlsx = OUT_DIR / "capacity_plan_dec2026.xlsx"
        try:
            with open(xlsx, "ab"):
                pass
        except PermissionError:  # file is open in Excel: write a timestamped copy instead
            xlsx = OUT_DIR / f"capacity_plan_dec2026_{dt.datetime.now():%H%M%S}.xlsx"
        with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
            summary.to_excel(xw, sheet_name="Summary", index=False)
            fc["forecast"].reset_index(names="date").to_excel(xw, sheet_name="XGBoost Forecast 2026", index=False)
            result.to_excel(xw, sheet_name="Site Plan Dec2026", index=False)
            result[result["Upgrade Needed"]].sort_values("PRB_Dec2026", ascending=False).to_excel(
                xw, sheet_name="Sites Upgraded", index=False)
            steps.to_excel(xw, sheet_name="Upgrade Steps", index=False)
            pd.DataFrame([{k: v for k, v in model.items() if k not in ("clean", "removed")}]).to_excel(
                xw, sheet_name="Regression", index=False)
            model["clean"].to_excel(xw, sheet_name="PS Cleaned", index=False)
            for k, v in kpi.items():
                if not k.startswith("_"):
                    v.to_excel(xw, sheet_name=("KPI " + k)[:31], index=False)
        say(f"Saved results to {OUT_DIR}")
    return out


# %% GUI (ipywidgets)
import ipywidgets as widgets
from IPython.display import display

_CACHE = {}


def _fig_html(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return '<img style="max-width:100%;height:auto" src="data:image/png;base64,' + \
           base64.b64encode(buf.getvalue()).decode() + '">'


def _table(df, limit=None, index=False):
    if df is None or len(df) == 0:
        return "<p><i>No records for this selection.</i></p>"
    shown = df if limit is None else df.head(limit)
    html = shown.to_html(index=index, border=0, na_rep="-", float_format=lambda v: f"{v:,.2f}")
    note = f"<p><small>Showing {len(shown):,} of {len(df):,} rows.</small></p>" if limit and len(df) > limit else ""
    return f'<div style="overflow-x:auto;max-height:420px;overflow-y:auto">{html}</div>{note}'


def _h(title):
    return f"<h3 style='margin-top:18px;border-bottom:1px solid #ccc'>{title}</h3>"


def _data():
    if "data" not in _CACHE:
        _CACHE["data"] = load_data()
        _CACHE["ps"] = normalize_kpi_sheet(_CACHE["data"]["ps"], "PS")
        _CACHE["cs"] = normalize_kpi_sheet(_CACHE["data"]["cs"], "CS")
    return _CACHE


def _forecast_all():
    """Heavy steps run once and are cached (XGBoost bootstrap takes about a minute)."""
    c = _data()
    if "plan" not in c:
        d = c["data"]
        fc = forecast_network_traffic(d["network"], run_validation=True)
        g = december_growth_factor(d["network"], fc["forecast"])
        sites = project_site_traffic(d["ps"], g["factor"])
        model = fit_prb_model(d["ps"])
        sites["PRB_Dec2026"] = predict_prb(sites["Traffic_Dec2026"], model)
        c["plan"] = dict(fc=fc, g=g, model=model, result=apply_upgrade_flow(sites, d["config"]))
    return c["plan"]


# ----------------------------------------------------------------------------- analysis
def analysis_html(regions, months):
    c = _data()
    out = []
    for role, frame, kpis in [("PS", c["ps"], PS_KPIS), ("CS", c["cs"], CS_KPIS)]:
        f = frame
        if regions:
            f = f[f["Region"].isin(regions)]
        if months:
            f = f[f["Y-M"].isin(months)]
        out.append(_h(f"{role} KPI analysis ({len(f):,} rows, {f['Site ID'].nunique():,} sites)"))
        if f.empty:
            out.append("<p><i>No data for this selection.</i></p>")
            continue
        kpis = [k for k in kpis if k in f]
        out.append("<b>Statistics</b>" + _table(descriptive_statistics(f, kpis)))
        out.append("<b>Regional summary - mean per KPI</b>" +
                   _table(f.groupby("Region")[kpis].mean().reset_index()))
        out.append("<b>Monthly summary - mean per KPI</b>" +
                   _table(f.groupby("Y-M")[kpis].mean().reset_index()))
        key = [TRAFFIC, THROUGHPUT, PRB] if role == "PS" else ["Availability", "CDR", "CSSR"]
        fig, axes = plt.subplots(1, len(key), figsize=(5 * len(key), 3.4))
        for ax, k in zip(np.atleast_1d(axes), key):
            f.pivot_table(index="Month", columns="Region", values=k, aggfunc="mean").plot(ax=ax, marker="o")
            ax.set_title(k + " (monthly regional mean)", fontsize=10); ax.tick_params(axis="x", rotation=45)
        fig.tight_layout(); out.append(_fig_html(fig))
        if role == "PS":
            prob = throughput_problem_sites(f)
            out.append("<b>Throughput problem sites (below 5 Mbps in any month)</b>" +
                       _table(prob[prob["Low Months"] > 0].round(2), 50))
            out.append("<b>PS correlations</b>" + _table(pd.DataFrame(
                [relationship(f, x, y) for i, x in enumerate(kpis) for y in kpis[i + 1:]]), 50))
        else:
            out.append("<b>CS problem sites (screening, top issues)</b>" + _table(cs_problem_sites(f), 30))
    return "".join(out)


# ----------------------------------------------------------------------------- forecast
def forecast_html(regions):
    d, plan = _data()["data"], _forecast_all()
    fc, g, model, res = plan["fc"], plan["g"], plan["model"], plan["result"]
    net = d["network"]
    out = []

    # 1. validation
    out.append(_h("1. Model validation (XGBoost)"))
    bt = fc["backtest_metrics"].copy()
    out.append("<b>Backtest: trained to Dec 2024, predicted 2025</b>" + _table(bt))
    out.append("<b>Rolling cross-validation (3 expanding folds)</b>" + _table(fc["cv_detail"]))
    p = fc["backtest_preds"]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(net.index, net.values, color="grey", label="Actual")
    ax.plot(p.index, p["XGBoost"], "--s", color="tab:red", label="XGBoost backtest 2025")
    ax.plot(p.index, p["Seasonal-naive"], ":", color="tab:green", label="Seasonal-naive")
    ax.set_ylabel("TB/day"); ax.set_title("Validation on 2025"); ax.legend()
    fig.tight_layout(); out.append(_fig_html(fig))

    # 2. forecast
    out.append(_h("2. Forecasted network traffic 2026"))
    fig = plot_forecast(net, fc["forecast"]); out.append(_fig_html(fig))
    f = fc["forecast"].reset_index(names="Month")
    f["Month"] = f["Month"].dt.strftime("%Y-%m")
    out.append(_table(f))

    # 3. growth
    out.append(_h("3. Growth December 2025 to December 2026"))
    out.append(f"<p style='font-size:20px'><b>+{g['increase_pct']:.2f}%</b> &nbsp; "
               f"({g['dec_2025']:,.0f} to {g['dec_2026']:,.1f} TB/day, factor {g['factor']:.4f})</p>")

    # 4. Dec 2026 statistics
    sel = res[res["Region"].isin(regions)] if regions else res
    scope = ", ".join(regions) if regions else "all regions"
    out.append(_h(f"4. December 2026 statistics ({len(sel):,} sites; {scope})"))
    stats = pd.DataFrame({
        "Statistic": ["Sites", "Mean", "Median", "Min", "Max", "Std"],
        "Traffic Dec 2025": [len(sel)] + [getattr(sel["Traffic_Dec2025"], m)() for m in ["mean", "median", "min", "max", "std"]],
        "Traffic Dec 2026": [len(sel)] + [getattr(sel["Traffic_Dec2026"], m)() for m in ["mean", "median", "min", "max", "std"]]})
    out.append(_table(stats))
    out.append("<b>By region</b>" + _table(sel.groupby("Region").agg(
        Sites=("Site ID", "count"), Traffic_Dec2025=("Traffic_Dec2025", "mean"),
        Traffic_Dec2026=("Traffic_Dec2026", "mean")).reset_index()))

    # 5. PRB
    out.append(_h("5. PRB utilization December 2026"))
    out.append(f"<p>Linear regression after IQR cleaning: <b>PRB = {model['slope']:.4f} x Traffic + {model['intercept']:.4f}</b>"
               f" &nbsp; R&sup2; = <b>{model['r2']:.4f}</b> (kept {model['n_clean']:,} of {model['n_initial']:,} rows).</p>")
    fig = plot_regression(model); out.append(_fig_html(fig))
    out.append("<b>PRB statistics (selected regions)</b>" + _table(pd.DataFrame({
        "Statistic": ["Mean", "Median", "Min", "Max", "Std", f"Sites above {PRB_THRESHOLD:.0f}%"],
        "PRB Dec 2025": [sel["PRB_Dec2025"].mean(), sel["PRB_Dec2025"].median(), sel["PRB_Dec2025"].min(),
                         sel["PRB_Dec2025"].max(), sel["PRB_Dec2025"].std(), int((sel["PRB_Dec2025"] > PRB_THRESHOLD).sum())],
        "PRB Dec 2026": [sel["PRB_Dec2026"].mean(), sel["PRB_Dec2026"].median(), sel["PRB_Dec2026"].min(),
                         sel["PRB_Dec2026"].max(), sel["PRB_Dec2026"].std(), int(sel["Upgrade Needed"].sum())]})))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.hist(sel["PRB_Dec2026"], bins=40, alpha=.8)
    ax.axvline(PRB_THRESHOLD, color="red", ls="--", label=f"{PRB_THRESHOLD:.0f}% threshold")
    ax.set_xlabel("PRB DL utilization (%)"); ax.set_title("Dec 2026 distribution"); ax.legend()
    fig.tight_layout(); out.append(_fig_html(fig))

    # 6. sites to upgrade
    up = sel[sel["Upgrade Needed"]].sort_values("PRB_Dec2026", ascending=False)
    out.append(_h(f"6. Sites to reconfigure or expand ({len(up):,})"))
    out.append("<p>Flow: Normal 3 Sectors &rarr; Normal 4 Sectors &rarr; FDD M-MIMO &rarr; TDD 1st Carrier "
               "&rarr; TDD 2nd Carrier &rarr; TDD M-MIMO &rarr; Expand site</p>")
    table = up[["Site ID", "Region", "Traffic_Dec2026", "PRB_Dec2026", "Configuration", "New Configuration", "Action"]]
    table = table.rename(columns={"Traffic_Dec2026": "Traffic Dec 2026", "PRB_Dec2026": "PRB Dec 2026 (%)",
                                  "Configuration": "Current configuration", "New Configuration": "Recommended configuration"})
    out.append(_table(table))
    return "".join(out)


# ----------------------------------------------------------------------------- GUI
def launch():
    c = _data()
    regions_all = sorted(set(c["ps"]["Region"]) | set(c["cs"]["Region"]))
    months_all = sorted(set(c["ps"]["Y-M"]) | set(c["cs"]["Y-M"]))

    mode = widgets.RadioButtons(options=["Analysis", "Forecast", "Both"], value="Both", description="Run:",
                                layout=widgets.Layout(width="200px"))
    regions = widgets.SelectMultiple(options=regions_all, value=(), rows=8, description="Regions:",
                                     layout=widgets.Layout(width="260px"))
    months = widgets.SelectMultiple(options=months_all, value=(), rows=8, description="Months:",
                                    layout=widgets.Layout(width="260px"))
    hint = widgets.HTML("<small>Nothing selected = all regions / all months. Months apply to the analysis; "
                        "the forecast always compares December 2025 with December 2026.</small>")
    run = widgets.Button(description="Run", button_style="primary", icon="play")
    status = widgets.HTML()
    result = widgets.HTML()

    def toggle(_=None):
        analysis = mode.value in ("Analysis", "Both")
        months.disabled = not analysis
    mode.observe(toggle, "value"); toggle()

    def on_run(_):
        run.disabled = True
        try:
            parts = []
            sel_r, sel_m = list(regions.value), list(months.value)
            if mode.value in ("Analysis", "Both"):
                status.value = "Running analysis..."
                parts.append("<h2>KPI analysis</h2>" + analysis_html(sel_r, sel_m))
            if mode.value in ("Forecast", "Both"):
                status.value = ("Running forecast (first run takes about a minute: XGBoost validation and "
                                "bootstrap)..." if "plan" not in _CACHE else "Building forecast report...")
                parts.append("<h2>Forecast</h2>" + forecast_html(sel_r))
            result.value = "".join(parts)
            status.value = "<span style='color:green'>Done.</span>"
        except Exception as exc:  # show the error in the GUI instead of a traceback
            status.value = f"<span style='color:red'>Error: {exc}</span>"
        finally:
            run.disabled = False
    run.on_click(on_run)

    ui = widgets.VBox([
        widgets.HTML("<h2>Telecom KPI analysis and capacity forecast</h2>"),
        widgets.HBox([mode, regions, months]), hint, widgets.HBox([run, status]), result])
    display(ui)
    return ui


if __name__ == "__main__":
    run()
