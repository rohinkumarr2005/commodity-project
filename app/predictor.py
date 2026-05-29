"""
Predictor Module — Member 1: Prediction + Explainable AI
=========================================================
Fetches historical commodity data via yfinance, trains scikit-learn
Linear Regression models for 1-day / 7-day / 30-day price forecasts,
and produces detailed Explainable AI (XAI) metrics.

Commodities: Gold (GC=F) · Silver (SI=F) · Copper (HG=F)
"""

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List

# ──────────────────────────────────────────────────────────
# Commodity Registry
# ──────────────────────────────────────────────────────────
COMMODITIES: Dict[str, Dict[str, str]] = {
    "gold":   {"symbol": "GC=F", "name": "Gold",   "unit": "USD/oz"},
    "silver": {"symbol": "SI=F", "name": "Silver", "unit": "USD/oz"},
    "copper": {"symbol": "HG=F", "name": "Copper", "unit": "USD/lb"},
}


def list_commodities() -> List[Dict[str, str]]:
    """Return supported commodities for the frontend selector."""
    return [
        {"key": k, "symbol": v["symbol"], "name": v["name"], "unit": v["unit"]}
        for k, v in COMMODITIES.items()
    ]


def _resolve(commodity_key: str):
    """Resolve a key like 'gold' → (symbol, display_name, unit)."""
    key = commodity_key.strip().lower()
    if key in COMMODITIES:
        c = COMMODITIES[key]
        return c["symbol"], c["name"], c["unit"]
    # allow raw ticker as fallback
    return commodity_key.strip().upper(), commodity_key.strip().upper(), "USD"


# ──────────────────────────────────────────────────────────
# Core engine
# ──────────────────────────────────────────────────────────
def fetch_and_predict(commodity_key: str) -> Dict[str, Any]:
    """
    End-to-end pipeline:
      1. Fetch 5-year historical OHLCV via yfinance
      2. Engineer features (SMA, volatility, volume ratio)
      3. Train three Linear Regression models (T+1, T+7, T+30)
      4. Predict next-day, 7-day, 30-day prices
      5. Compute Explainable AI metrics & natural-language summary
      6. Return structured JSON-ready dict
    """
    symbol, display_name, unit = _resolve(commodity_key)

    # ── 1. Fetch Data ────────────────────────────────────
    try:
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period="5y")
    except Exception as e:
        raise ValueError(f"Failed to fetch data for '{display_name}' ({symbol}): {e}")

    if df.empty or len(df) < 60:
        raise ValueError(
            f"'{display_name}' ({symbol}) returned insufficient data "
            f"(need ≥60 trading days, got {len(df)})."
        )

    df = df.reset_index()
    df.columns = [
        c.capitalize() if c.lower() in ("date", "open", "high", "low", "close", "volume")
        else c
        for c in df.columns
    ]
    df = df.ffill().bfill()

    # ── 2. Feature Engineering ───────────────────────────
    df["SMA_10"]       = df["Close"].rolling(10).mean()
    df["SMA_30"]       = df["Close"].rolling(30).mean()
    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"]   = df["Daily_Return"].rolling(10).std()
    df["Volume_MA10"]  = df["Volume"].rolling(10).mean()
    df["Volume_Ratio"] = df["Volume"] / (df["Volume_MA10"] + 1e-8)

    df_clean = df.dropna().copy()
    if len(df_clean) < 35:
        raise ValueError("Not enough data after feature engineering.")

    feature_cols = ["Close", "SMA_10", "SMA_30", "Volume_Ratio", "Volatility"]

    # ── 3. Train Models ──────────────────────────────────
    models:  Dict[int, LinearRegression] = {}
    scalers: Dict[int, StandardScaler]   = {}

    for horizon in (1, 7, 30):
        tmp = df_clean.copy()
        tmp["Target"] = tmp["Close"].shift(-horizon)
        tmp = tmp.dropna()

        X = tmp[feature_cols].values
        y = tmp["Target"].values

        sc = StandardScaler()
        X_sc = sc.fit_transform(X)

        lr = LinearRegression()
        lr.fit(X_sc, y)

        models[horizon]  = lr
        scalers[horizon] = sc

    # ── 4. Predict ───────────────────────────────────────
    latest      = df_clean.iloc[-1]
    latest_X    = latest[feature_cols].values.reshape(1, -1)
    cur_price   = float(latest["Close"])
    latest_date = latest["Date"]
    date_str    = latest_date.strftime("%Y-%m-%d") if isinstance(latest_date, pd.Timestamp) else str(latest_date)

    forecasts: Dict[int, dict] = {}
    for h in (1, 7, 30):
        pred = max(float(models[h].predict(scalers[h].transform(latest_X))[0]), 0.01)
        pct  = ((pred - cur_price) / cur_price) * 100
        forecasts[h] = {
            "predicted_price": round(pred, 2),
            "percent_change":  round(pct, 2),
            "direction":       "UP" if pct >= 0 else "DOWN",
        }

    # ── 5. Explainable AI ────────────────────────────────
    coefs       = models[1].coef_
    scaled_vals = scalers[1].transform(latest_X)[0]
    contribs    = scaled_vals * coefs

    factor_names = [
        "Current Close", "Trend (10 SMA)", "Trend Support (30 SMA)",
        "Volume Momentum", "Volatility Risk",
    ]
    xai_factors = [
        {
            "name":                    name,
            "raw_value":               round(float(rv), 2 if name == "Current Close" else 4),
            "scaled_value":            round(float(sv), 4),
            "model_coefficient":       round(float(co), 4),
            "prediction_contribution": round(float(ct), 4),
            "influence":               "Bullish" if ct >= 0 else "Bearish",
        }
        for name, rv, sv, co, ct in zip(
            factor_names, latest_X[0], scaled_vals, coefs, contribs
        )
    ]

    # High-level factor states
    short_ma  = float(latest["SMA_10"])
    long_ma   = float(latest["SMA_30"])
    trend_st  = "UP" if short_ma >= long_ma else "DOWN"
    trend_pct = ((short_ma - long_ma) / long_ma) * 100

    vr        = float(latest["Volume_Ratio"])
    vol_st    = "UP" if vr >= 1.05 else ("DOWN" if vr <= 0.95 else "NEUTRAL")

    cur_vol   = float(latest["Volatility"])
    avg_vol   = float(df_clean["Volatility"].mean())
    vola_st   = "HIGH" if cur_vol > avg_vol * 1.1 else ("LOW" if cur_vol < avg_vol * 0.9 else "NORMAL")

    # Natural-language XAI bullets
    p1 = forecasts[1]["percent_change"]
    d  = "upward" if p1 >= 0 else "downward"
    bullets = []

    if trend_st == "UP":
        bullets.append(
            f"A strong short-term upward trend is active — the 10-day SMA ({short_ma:.2f}) "
            f"sits {trend_pct:.1f}% above the 30-day SMA ({long_ma:.2f}), providing "
            f"bullish support for {display_name}."
        )
    else:
        bullets.append(
            f"{display_name} is under short-term downward pressure — the 10-day SMA "
            f"({short_ma:.2f}) is {abs(trend_pct):.1f}% below the 30-day SMA ({long_ma:.2f})."
        )

    if vol_st == "UP":
        bullets.append(
            f"Trading volume is surging at {vr:.1f}x the 10-day average, signaling "
            f"strong market conviction."
        )
    elif vol_st == "DOWN":
        bullets.append(
            f"Volume is thin ({vr:.1f}x average), indicating weak liquidity and "
            f"reduced confidence in price direction."
        )
    else:
        bullets.append("Trading volume is stable and in-line with the 10-day average.")

    if vola_st == "HIGH":
        bullets.append(
            f"Market volatility is elevated ({cur_vol*100:.2f}% daily deviation vs "
            f"{avg_vol*100:.2f}% average), increasing risk premiums for {display_name}."
        )
    elif vola_st == "LOW":
        bullets.append(
            f"Volatility is compressed ({cur_vol*100:.2f}% daily deviation), "
            f"signaling a stable environment that benefits the current trend."
        )
    else:
        bullets.append(f"Volatility is within normal historical ranges ({cur_vol*100:.2f}% deviation).")

    xai_summary = (
        f"The AI Model predicts a {abs(p1):.2f}% {d} move for {display_name} "
        f"tomorrow. " + " ".join(bullets)
    )

    # ── 6. Chart History (last 60 days) ──────────────────
    chart_history = []
    for _, r in df_clean.tail(60).iterrows():
        dt = r["Date"]
        chart_history.append({
            "date":   dt.strftime("%Y-%m-%d") if isinstance(dt, pd.Timestamp) else str(dt),
            "price":  round(float(r["Close"]), 2),
            "volume": int(r["Volume"]),
        })

    # ── 7. Response ──────────────────────────────────────
    return {
        "ticker":         symbol,
        "commodity_key":  commodity_key.strip().lower(),
        "commodity_name": display_name,
        "unit":           unit,
        "current_price":  round(cur_price, 2),
        "latest_date":    date_str,
        "predictions":    forecasts,
        "xai": {
            "summary":    xai_summary,
            "trend":      {"state": trend_st,  "short_ma": round(short_ma, 2), "long_ma": round(long_ma, 2), "difference_pct": round(trend_pct, 2)},
            "volume":     {"state": vol_st,    "ratio": round(vr, 2)},
            "volatility": {"state": vola_st,   "current": round(cur_vol, 5), "average": round(avg_vol, 5)},
            "factors":    xai_factors,
        },
        "history": chart_history,
    }
