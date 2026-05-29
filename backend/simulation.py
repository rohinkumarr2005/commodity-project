import random
import math
from backend.market_data import get_live_market_data

# Macroeconomic Scenarios shock matrices (%)
# shock = { "gold": float, "silver": float, "copper": float, "explanation": str }
SCENARIOS = {
    "inflation_increase": {
        "gold": 8.5,
        "silver": 5.0,
        "copper": 2.5,
        "explanation": "Gold acts as the premier inflation hedge. Silver captures precious momentum, while Copper experiences moderate industrial support due to rising input cost indexes."
    },
    "inflation_decrease": {
        "gold": -3.5,
        "silver": -2.0,
        "copper": 1.0,
        "explanation": "Cooling inflation reduces precious metal hedging demands. Industrial copper remains stable as economic production inputs normalize."
    },
    "geopolitical_conflict": {
        "gold": 12.0,
        "silver": 6.5,
        "copper": -4.0,
        "explanation": "Geopolitical uncertainty drives safe-haven rushes into Gold and Silver bullion. Copper faces headwinds from blocked logistics and factory freezes."
    },
    "economic_recession": {
        "gold": 9.5,
        "silver": -8.0,
        "copper": -18.0,
        "explanation": "Gold benefits from safe-haven inflows and monetary easing, while industrial demand for Silver (solar/tech) and Copper (EVs/construction) contracts heavily."
    },
    "market_crash": {
        "gold": 12.0,
        "silver": -5.0,
        "copper": -15.0,
        "explanation": "Gold stands resilient as a premier safe-haven asset, whereas industrial commodities (Silver, Copper) weaken under intense equity sell-offs and liquidations."
    },
    "interest_rate_cuts": {
        "gold": 10.5,
        "silver": 8.0,
        "copper": 6.0,
        "explanation": "Lower interest yields reduce holding costs for non-interest precious metals, sparking major rallies. Industrial metals gain from cheaper credit and expanded factory spending."
    },
    "interest_rate_hikes": {
        "gold": -7.0,
        "silver": -9.0,
        "copper": -5.0,
        "explanation": "Hawkish central banks delay cuts and raise bond yields, creating capital outflow pressure from precious bullion. High interest rates curtail building developments, slowing copper."
    }
}

def get_monte_carlo_sim(metal, days=30, runs=1000):
    """
    Runs a 30-day random walk simulation using geometric Brownian motion parameters.
    Starts from the Centralized Market Spot Price for absolute consistency.
    """
    metal_lower = metal.lower()
    
    # Query centralized market price
    market_data = get_live_market_data()
    start_price = market_data[metal_lower]["price"]
    
    # Establish daily volatility and drift coefficients per metal
    params = {
        "gold": {"drift": 0.0002, "vol": 0.012},
        "silver": {"drift": 0.0004, "vol": 0.022},
        "copper": {"drift": 0.0001, "vol": 0.018}
    }
    
    p = params.get(metal_lower, {"drift": 0.0002, "vol": 0.015})
    mu = p["drift"]
    sigma = p["vol"]
    
    random.seed(101) # Keep outputs stable but realistic
    
    final_prices = []
    sample_paths = []
    
    for run in range(runs):
        current_price = start_price
        path = [start_price]
        for day in range(days):
            epsilon = random.normalvariate(0, 1)
            price_change = current_price * (mu + sigma * epsilon)
            current_price += price_change
            path.append(round(current_price, 2))
        
        final_prices.append(current_price)
        if run < 5:
            sample_paths.append(path)
            
    final_prices.sort()
    
    worst_case = round(final_prices[int(runs * 0.10)], 2)
    average_case = round(final_prices[int(runs * 0.50)], 2)
    best_case = round(final_prices[int(runs * 0.90)], 2)
    
    return {
        "start_price": start_price,
        "worst_case": worst_case,
        "average_case": average_case,
        "best_case": best_case,
        "sample_paths": sample_paths
    }

def get_scenario_impact(scenario_name):
    """
    Fetches shock percentage changes and AI explanations for a macroeconomic scenario.
    """
    scen_id = scenario_name.lower().replace(" ", "_")
    impact = SCENARIOS.get(scen_id, {
        "gold": 0.0,
        "silver": 0.0,
        "copper": 0.0,
        "explanation": "No active macroeconomic triggers detected."
    })
    
    display_title = scenario_name.replace("_", " ").title()
    
    return {
        "scenario_id": scen_id,
        "title": display_title,
        "gold_impact": impact["gold"],
        "silver_impact": impact["silver"],
        "copper_impact": impact["copper"],
        "explanation": impact["explanation"]
    }
