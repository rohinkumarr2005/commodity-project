import pandas as pd
import numpy as np
import yfinance as yf
import ta
from textblob import TextBlob
import datetime
import time

def fetch_commodity_data(symbol, period='2y'):
    """Fetch data from yfinance with fallback."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            # Fallback or retry
            time.sleep(1)
            df = ticker.history(period=period)
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()

def add_technical_indicators(df):
    """Add RSI, MACD, Bollinger Bands, and MAs."""
    if len(df) < 200: return df
    
    # Moving Averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'])
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    
    return df

def run_monte_carlo_sim(current_price, volatility, days=30, iterations=10000):
    """Geometric Brownian Motion for 10,000 simulations."""
    dt = 1/252  # Daily steps
    mu = 0.05   # Assumed drift
    sigma = volatility / 100
    
    # Generate log returns
    returns = np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * np.random.standard_normal((days, iterations)))
    
    # Price paths
    price_paths = np.zeros_like(returns)
    price_paths[0] = current_price * returns[0]
    for t in range(1, days):
        price_paths[t] = price_paths[t-1] * returns[t]
        
    return price_paths

def calculate_risk_metrics(final_prices, current_price):
    """Calculate VaR and CVaR at 95% confidence."""
    returns = (final_prices - current_price) / current_price
    var_95 = np.percentile(returns, 5)
    cvar_95 = returns[returns <= var_95].mean()
    return abs(var_95 * 100), abs(cvar_95 * 100)

def get_news_sentiment(commodity_name):
    """Simple sentiment analysis (Fallback for FinBERT in shared environment)."""
    # In a real environment, use NewsAPI and Transformers
    # Mock news for demonstration as requested
    mock_news = [
        {"title": f"{commodity_name.capitalize()} prices surge amid inflation fears", "sentiment": 0.6, "topic": "Inflation"},
        {"title": f"Supply chain disruptions impact {commodity_name} output", "sentiment": -0.4, "topic": "Supply Chain"},
        {"title": f"Central bank decisions weigh on {commodity_name} demand", "sentiment": -0.1, "topic": "Central Bank"}
    ]
    for item in mock_news:
        item['sentiment_label'] = "Bullish" if item['sentiment'] > 0.1 else ("Bearish" if item['sentiment'] < -0.1 else "Neutral")
    return mock_news

def apply_scenarios(base_forecast, scenarios):
    """Apply scenario shocks to the forecast."""
    adj_forecast = base_forecast.copy()
    if scenarios.get('inflation'):
        adj_forecast *= (1 + scenarios['inflation'] * 0.02)
    if scenarios.get('war'):
        adj_forecast *= (1 + scenarios['war'] * 0.05)
    return adj_forecast

def run_backtest(df):
    """Backtest a simple trend-following strategy."""
    data = df.copy()
    data['SMA20'] = data['Close'].rolling(20).mean()
    data['Signal'] = 0
    data.loc[data['Close'] > data['SMA20'], 'Signal'] = 1
    data['Returns'] = data['Close'].pct_change()
    data['Strategy_Returns'] = data['Signal'].shift(1) * data['Returns']
    
    cum_ret = (1 + data['Strategy_Returns']).cumprod()
    sharpe = np.sqrt(252) * data['Strategy_Returns'].mean() / data['Strategy_Returns'].std()
    return cum_ret, sharpe

def export_to_csv(df):
    """Convert dataframe to CSV for download."""
    return df.to_csv(index=True).encode('utf-8')

def get_volatility_stats(df):
    """Calculates daily, monthly, and annual volatility/returns."""
    daily_ret = df['Close'].pct_change().dropna()
    return {
        "daily_avg_ret": daily_ret.mean() * 100,
        "daily_vol": daily_ret.std() * 100,
        "monthly_avg_ret": daily_ret.mean() * 21 * 100,
        "yearly_avg_ret": daily_ret.mean() * 252 * 100
    }

def get_seasonal_factor(commodity_name):
    """Returns the current seasonal impact for the Indian market."""
    month = datetime.datetime.now().month
    if month in [10, 11]: return "Peak Diwali demand (+3-5% historically)"
    if month in [4, 5]: return "Akshaya Tritiya seasonal demand spike"
    if month in [12, 1, 2]: return "Wedding season liquidity support"
    return "Neutral seasonal phase"

def get_correlation_coefficient(c1, c2):
    """Placeholder for cross-commodity correlation benchmarks."""
    corrs = {
        ("Gold", "Silver"): 0.82,
        ("Gold", "Copper"): 0.45,
        ("Silver", "Copper"): 0.55
    }
    return corrs.get((c1, c2), 0.5) or corrs.get((c2, c1), 0.5)
