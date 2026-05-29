from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import yfinance as yf
import os
import sys
from datetime import datetime, timedelta

# Adjust python path to allow importing from backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.prediction.predict import (
    fetch_commodity_data,
    add_technical_indicators,
    run_monte_carlo_sim,
    calculate_risk_metrics,
    get_news_sentiment,
    apply_scenarios,
    get_volatility_stats,
    get_seasonal_factor,
    get_correlation_coefficient,
    run_backtest
)
from backend.prediction.models_engine import get_ensemble_prediction
from backend.insight_panel.insight_generator import CommodityAnalystEngine, get_metal_context

app = Flask(__name__)

COMMODITIES = {
    'gold': 'GC=F',
    'silver': 'SI=F',
    'copper': 'HG=F'
}

SCENARIOS = {
    'none': {'gold': 1.0, 'silver': 1.0, 'copper': 1.0, 'desc': 'Normal market conditions.'},
    'inflation': {'gold': 1.05, 'silver': 1.03, 'copper': 1.02, 'desc': 'High inflation typically drives investors to Gold as a hedge.'},
    'war': {'gold': 1.10, 'silver': 1.05, 'copper': 0.95, 'desc': 'Geopolitical tension spikes Gold but can hurt industrial demand for Copper.'},
    'crash': {'gold': 1.15, 'silver': 0.90, 'copper': 0.85, 'desc': 'Market crashes cause a flight to safety (Gold) while industrial metals plummet.'}
}

# Analyst Engine Initialization
analyst = CommodityAnalystEngine()

def get_exchange_rate():
    try:
        usd_inr = yf.Ticker("USDINR=X")
        data = usd_inr.history(period="1d")
        if not data.empty:
            return round(float(data['Close'].iloc[-1]), 4)
    except:
        pass
    return 83.50

def get_indian_market_data():
    rate = get_exchange_rate()
    data = {'rate': rate}
    
    for name, symbol in COMMODITIES.items():
        try:
            df = fetch_commodity_data(symbol)
            if not df.empty:
                curr_usd = float(df['Close'].iloc[-1])
                prev_usd = float(df['Close'].iloc[-2]) if len(df) > 1 else float(df['Open'].iloc[-1])
                
                # Conversion logic to INR
                if name == 'gold':
                    curr_inr = (curr_usd * rate) / 31.1035 * 10
                    prev_inr = (prev_usd * rate) / 31.1035 * 10
                    unit = "₹ per 10g"
                    sub_unit = f"1g: ₹{round(curr_inr / 10, 2):,}"
                elif name == 'silver':
                    curr_inr = (curr_usd * rate) / 31.1035 * 1000
                    prev_inr = (prev_usd * rate) / 31.1035 * 1000
                    unit = "₹ per kg"
                    sub_unit = f"1g: ₹{round(curr_inr / 1000, 2):,}"
                else: # copper
                    curr_inr = (curr_usd * rate) * 2.20462
                    prev_inr = (prev_usd * rate) * 2.20462
                    unit = "₹ per kg"
                    sub_unit = f"1 lb: ₹{round(curr_usd * rate, 2):,}"

                data[name] = {
                    'price_inr': round(curr_inr, 2),
                    'price_usd': round(curr_usd, 2),
                    'unit': unit,
                    'sub_unit': sub_unit,
                    'percent_change': round(((curr_inr - prev_inr) / prev_inr) * 100, 2),
                }
            else:
                data[name] = {'price_inr': 'N/A', 'price_usd': 'N/A', 'percent_change': 0.0, 'unit': '', 'sub_unit': ''}
        except Exception as e:
            print(f"Error fetching market data for {name}: {e}")
            data[name] = {'price_inr': 'N/A', 'price_usd': 'N/A', 'percent_change': 0.0, 'unit': '', 'sub_unit': ''}
    return data

@app.route('/')
def index():
    market_data = get_indian_market_data()
    return render_template('index.html', data=market_data)

@app.route('/prices')
def prices_api():
    return jsonify(get_indian_market_data())

@app.route('/predict', methods=['POST'])
def predict():
    req_data = request.get_json()
    commodity = req_data.get('commodity').lower()
    scenario = req_data.get('scenario', 'none')
    
    try:
        open_p = float(req_data.get('open'))
        high_p = float(req_data.get('high'))
        volume = float(req_data.get('volume'))
        low_p = float(req_data.get('low')) if req_data.get('low') else open_p * 0.995
        
        if not (low_p <= open_p <= high_p):
            return jsonify({'error': 'Validation Error: Ensure Low <= Open <= High.'}), 400
    except Exception as e:
        return jsonify({'error': f'Invalid inputs: {str(e)}'}), 400
    
    try:
        rate = get_exchange_rate()
        symbol = COMMODITIES[commodity]
        df = fetch_commodity_data(symbol)
        df = add_technical_indicators(df)
        
        if df.empty:
            return jsonify({'error': 'No historical data found to run models.'}), 404
        
        # Base Prediction using the ensemble models
        ensemble, upper, lower = get_ensemble_prediction(df)
        
        # Stagger predictions for 1d, 7d, 30d
        res = {
            'Target_Next': round(float(ensemble[0]), 2),
            'Target_7d': round(float(ensemble[6]), 2),
            'Target_30d': round(float(ensemble[29]), 2)
        }
        
        # Scenario Adjustment
        multiplier = SCENARIOS.get(scenario, {}).get(commodity, 1.0)
        for k in res:
            res[k] = round(res[k] * multiplier, 2)
        
        # Monte Carlo Path Simulations
        curr_price = df['Close'].iloc[-1]
        vol = df['Close'].pct_change().std() * 100
        paths = run_monte_carlo_sim(curr_price, vol)
        
        mc = {
            'best': round(float(np.percentile(paths[-1], 95)), 2),
            'worst': round(float(np.percentile(paths[-1], 5)), 2),
            'likely': round(float(np.percentile(paths[-1], 50)), 2)
        }
        
        # XAI Explanation (Mocked/Attributions using trend metrics)
        factors = []
        if volume > df['Volume'].mean():
            factors.append("High trading volume indicates strong interest.")
        if open_p > df['Close'].rolling(30).mean().iloc[-1]:
            factors.append("Price is currently above the 30-day moving average (Bullish Trend).")
        if vol > 1.5:
            factors.append("Elevated daily volatility detected in this session.")
        if not factors:
            factors.append("Model is following baseline historical momentum.")
            
        # Decision Recommendation
        signal = "BUY" if res['Target_7d'] > open_p * 1.02 else ("SELL" if res['Target_7d'] < open_p * 0.98 else "HOLD")
        risk = "High" if vol > 3 else ("Medium" if vol > 1.5 else "Low")

        return jsonify({
            'commodity': commodity.capitalize(),
            'current_price': round(curr_price, 2),
            'prediction': res['Target_Next'],
            'forecast_7d': res['Target_7d'],
            'forecast_30d': res['Target_30d'],
            'monte_carlo': mc,
            'xai': factors,
            'decision': {'signal': signal, 'risk': risk},
            'scenario_applied': SCENARIOS[scenario]['desc']
        })
    except Exception as e:
        return jsonify({'error': f"Prediction failed: {str(e)}"}), 500

@app.route('/recommendation')
def recommendation():
    market_data = get_indian_market_data()
    results = []
    for c in COMMODITIES:
        if market_data[c]['price_inr'] != 'N/A':
            results.append({'name': c.capitalize(), 'growth': market_data[c]['percent_change']})
    if not results:
        return jsonify({'error': 'No data'}), 404
    best = max(results, key=lambda x: x['growth'])
    return jsonify({'recommendation': best, 'all_results': results})

@app.route('/news')
def news_route():
    metal = request.args.get('metal', 'gold')
    ctx = get_metal_context(metal)
    return jsonify(ctx['articles'])

@app.route('/sentiment')
def sentiment_route():
    metal = request.args.get('metal', 'gold')
    ctx = get_metal_context(metal)
    return jsonify(ctx['sentiment'])

@app.route('/decision')
def decision_route():
    metal = request.args.get('metal', 'gold')
    ctx = get_metal_context(metal)
    return jsonify(ctx['decision'])

@app.route('/insight')
def insight_route():
    metal = request.args.get('metal', 'gold')
    ctx = get_metal_context(metal)
    return jsonify({'summary': ctx['decision']['explanation']})

@app.route('/chat', methods=['POST'])
def chat():
    req_data = request.get_json()
    user_msg = req_data.get('message', '')
    response_msg = analyst.generate_response("Gold", user_msg)
    return jsonify({'response': response_msg})

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
