import os
import sys
from flask import Flask, jsonify, request, render_template

# Ensure the parent directory of backend is in the path to allow imports of siblings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.news_service import fetch_news
from backend.sentiment import analyze_articles
from backend.decision import generate_decision
from backend.chatbot import generate_chat_response
from backend.prediction import get_predictions, get_prediction_explanation
from backend.simulation import get_monte_carlo_sim, get_scenario_impact
from backend.market_data import get_live_market_data, validate_and_sync_prices

# Establish folder paths relative to this file's location to keep paths robust
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(
    __name__, 
    template_folder=template_dir, 
    static_folder=static_dir
)

@app.route('/')
def index():
    """Serves the single page dashboard."""
    return render_template('index.html')

# =============================================================================
# NEW CENTRALIZED SOURCE OF TRUTH ENDPOINT
# =============================================================================

@app.route('/market-data', methods=['GET'])
def get_market_data():
    """Exposes centralized real-time prices, inventories, and UTC timestamps."""
    try:
        data = get_live_market_data()
        return jsonify({
            "status": "success",
            "market_data": data
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load centralized market data: {str(e)}"}), 500

# =============================================================================
# MEMBER 3 ENDPOINTS (WITH CONSISTENCY ENFORCEMENT)
# =============================================================================

@app.route('/news', methods=['GET'])
def get_news():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected. Choose Gold, Silver, or Copper."}), 400
        
    try:
        articles = fetch_news(metal)
        sentiment_summary = analyze_articles(articles)
        return jsonify({
            "status": "success",
            "metal": metal,
            "count": len(articles),
            "articles": articles
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch news: {str(e)}"}), 500

@app.route('/sentiment', methods=['GET'])
def get_sentiment():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected. Choose Gold, Silver, or Copper."}), 400
        
    try:
        articles = fetch_news(metal)
        sentiment_summary = analyze_articles(articles)
        return jsonify({
            "status": "success",
            "metal": metal,
            "sentiment": sentiment_summary
        })
    except Exception as e:
        return jsonify({"error": f"Failed to analyze sentiment: {str(e)}"}), 500

@app.route('/decision', methods=['GET'])
def get_decision():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected. Choose Gold, Silver, or Copper."}), 400
        
    try:
        # Enforce price consistency across Decision Engine
        market_data = get_live_market_data()
        truth_price = market_data[metal.lower()]["price"]
        
        articles = fetch_news(metal)
        sentiment_summary = analyze_articles(articles)
        decision = generate_decision(metal, sentiment_summary, articles)
        
        # Enforce validation and dynamic synchronization
        validate_and_sync_prices({metal.lower(): truth_price})
        
        return jsonify({
            "status": "success",
            "metal": metal,
            "decision": decision
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate decision: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    metal = data.get('metal', 'gold').strip()
    
    if not message:
        return jsonify({"error": "Message is required."}), 400
        
    try:
        response = generate_chat_response(message, metal)
        return jsonify({
            "status": "success",
            "message": message,
            "metal": metal,
            "response": response
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate chat response: {str(e)}"}), 500

# =============================================================================
# MEMBER 1 ENDPOINTS (PREDICTIONS ENHANCED WITH SINGLE SOURCE OF TRUTH)
# =============================================================================

@app.route('/predict', methods=['GET'])
def get_all_predictions():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected. Choose Gold, Silver, or Copper."}), 400
    try:
        # Enforce price consistency check
        market_data = get_live_market_data()
        truth_price = market_data[metal.lower()]["price"]
        
        preds = get_predictions(metal)
        
        # Validate that prediction prices align with centralized service
        validate_and_sync_prices({metal.lower(): preds["current_price"]})
        
        return jsonify({
            "status": "success",
            "metal": metal,
            "predictions": preds
        })
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

@app.route('/predict-next-day', methods=['GET'])
def get_prediction_nd():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal."}), 400
    try:
        preds = get_predictions(metal)
        return jsonify({
            "status": "success",
            "metal": metal,
            "next_day": preds["next_day"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/predict-7-day', methods=['GET'])
def get_prediction_sd():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal."}), 400
    try:
        preds = get_predictions(metal)
        return jsonify({
            "status": "success",
            "metal": metal,
            "seven_day": preds["seven_day"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/predict-30-day', methods=['GET'])
def get_prediction_td():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal."}), 400
    try:
        preds = get_predictions(metal)
        return jsonify({
            "status": "success",
            "metal": metal,
            "thirty_day": preds["thirty_day"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/explanation', methods=['GET'])
def get_xai_explanation():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal."}), 400
    try:
        preds = get_predictions(metal)
        trend = preds["thirty_day"]["trend"]
        explanation = get_prediction_explanation(metal, trend)
        return jsonify({
            "status": "success",
            "metal": metal,
            "explanation": explanation
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================================================
# MEMBER 2 ENDPOINTS (SIMULATION ENHANCED WITH SINGLE SOURCE OF TRUTH)
# =============================================================================

@app.route('/simulation', methods=['GET'])
def get_simulation_bounds():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected. Choose Gold, Silver, or Copper."}), 400
    try:
        sim = get_monte_carlo_sim(metal)
        
        # Enforce consistency check
        validate_and_sync_prices({metal.lower(): sim["start_price"]})
        
        return jsonify({
            "status": "success",
            "metal": metal,
            "simulation": {
                "start_price": sim["start_price"],
                "worst_case": sim["worst_case"],
                "average_case": sim["average_case"],
                "best_case": sim["best_case"]
            }
        })
    except Exception as e:
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500

@app.route('/scenario', methods=['GET'])
def get_scenario_impacts():
    scenario = request.args.get('scenario', 'inflation_increase').strip()
    try:
        impact = get_scenario_impact(scenario)
        return jsonify({
            "status": "success",
            "scenario": scenario,
            "impact": impact
        })
    except Exception as e:
        return jsonify({"error": f"Scenario analysis failed: {str(e)}"}), 500

@app.route('/monte-carlo', methods=['GET'])
def get_monte_carlo_raw():
    metal = request.args.get('metal', 'gold').strip()
    if metal.lower() not in ['gold', 'silver', 'copper']:
        return jsonify({"error": "Invalid metal selected."}), 400
    try:
        sim = get_monte_carlo_sim(metal)
        return jsonify({
            "status": "success",
            "metal": metal,
            "sample_paths": sim["sample_paths"],
            "bounds": {
                "worst": sim["worst_case"],
                "average": sim["average_case"],
                "best": sim["best_case"]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Metals Market Intelligence Dashboard Flask Server...")
    app.run(host='127.0.0.1', port=5000, debug=True)
