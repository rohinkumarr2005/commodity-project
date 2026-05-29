"""
FastAPI Application — Member 1: Prediction + Explainable AI
============================================================
Serves the Prediction API and the static frontend dashboard.
"""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.predictor import fetch_and_predict, list_commodities

app = FastAPI(
    title="Commodity Intelligence — Prediction & XAI Engine",
    description="Member 1 module: Linear Regression predictions and Explainable AI for Gold, Silver, and Copper.",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/commodities")
def get_commodities():
    """Return the list of supported commodities."""
    return list_commodities()


@app.get("/api/predict")
def get_prediction(
    commodity: str = Query(
        "gold",
        min_length=1,
        max_length=20,
        description="Commodity key (gold, silver, copper) or raw yfinance symbol",
    ),
):
    """
    Fetch data, train models, predict prices, and return XAI analysis
    for the requested commodity.
    """
    try:
        data = fetch_and_predict(commodity)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# Mount the static directory (index.html, styles.css, app.js)
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
