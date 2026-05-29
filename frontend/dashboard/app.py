import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import sys
import os
# Adjust python path to allow importing from backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.prediction.predict import fetch_commodity_data, add_technical_indicators, run_monte_carlo_sim, calculate_risk_metrics, get_news_sentiment, apply_scenarios, get_volatility_stats, get_seasonal_factor, get_correlation_coefficient, run_backtest
from backend.prediction.models_engine import get_ensemble_prediction, get_shap_explanations
from backend.insight_panel.insight_generator import CommodityAnalystEngine
import time
import shap
import matplotlib.pyplot as plt
from pypfopt import EfficientFrontier, risk_models, expected_returns

# Page Config
st.set_page_config(page_title="FinPredict Pro | Indian Commodity Intelligence", layout="wide", page_icon="📈")

# Custom CSS for Glassmorphism & Aesthetics
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    .metric-card { 
        background-color: rgba(22, 27, 34, 0.7); 
        border: 1px solid rgba(48, 54, 61, 0.5); 
        border-radius: 12px; 
        padding: 20px;
        backdrop-filter: blur(8px);
    }
    .chat-bubble {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        backdrop-filter: blur(10px);
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .gold-accent { border-left: 4px solid #FFD700; }
    .silver-accent { border-left: 4px solid #C0C0C0; }
    .copper-accent { border-left: 4px solid #B87333; }
    .stChatFloatingInputContainer { background-color: transparent !important; }
</style>
""", unsafe_allow_html=True)

# Analyst Engine Initialization
analyst = CommodityAnalystEngine({
    'fetch_data': fetch_commodity_data,
    'add_indicators': add_technical_indicators,
    'predict': get_ensemble_prediction,
    'run_sim': run_monte_carlo_sim,
    'get_vol': get_volatility_stats,
    'get_news': get_news_sentiment,
    'get_seasonal': get_seasonal_factor,
    'get_corr': get_correlation_coefficient
})

# State Management
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar
st.sidebar.title("🛠️ Decision Controls")
commodity = st.sidebar.selectbox("Select Commodity", ["Gold (GC=F)", "Silver (SI=F)", "Copper (HG=F)"])
sym = commodity.split("(")[1].replace(")", "")
currency = "INR" # Simplified for this specific requirement

st.sidebar.subheader("Scenario Intensity")
inf_shock = st.sidebar.slider("Inflation Shock (%)", 0, 5, 0)
geo_risk = st.sidebar.slider("Geopolitical Risk", 0, 10, 0)
dxy_strength = st.sidebar.slider("DXY Strength", -5, 5, 0)

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🇮🇳 FinPredict Pro")
    st.caption(f"Real-time Intelligence System for Indian Commodity Markets | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    if st.button("🔄 Refresh Data"):
        st.rerun()

# Row 1: Live Price Cards
df = fetch_commodity_data(sym)
df = add_technical_indicators(df)

if not df.empty:
    curr_p = df['Close'].iloc[-1]
    prev_p = df['Close'].iloc[-2]
    diff = curr_p - prev_p
    pct = (diff / prev_p) * 100
    
    cols = st.columns(4)
    cols[0].metric("Live Price", f"₹{curr_p:,.2f}", f"{pct:,.2f}%")
    cols[1].metric("RSI (14)", f"{df['RSI'].iloc[-1]:,.2f}", "Overbought" if df['RSI'].iloc[-1] > 70 else ("Oversold" if df['RSI'].iloc[-1] < 30 else "Neutral"))
    cols[2].metric("52W High", f"₹{df['High'].tail(252).max():,.0f}")
    cols[3].metric("52W Low", f"₹{df['Low'].tail(252).min():,.0f}")

    # Row 2: Prediction Ensemble
    st.divider()
    st.subheader("🔮 Ensemble Forecasting (LSTM + XGBoost + ARIMA)")
    
    ensemble, upper, lower = get_ensemble_prediction(df)
    
    # Scenario Adjustment
    ensemble = apply_scenarios(ensemble, {'inflation': inf_shock, 'war': geo_risk})
    
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=df.index[-60:], y=df['Close'].tail(60), name="Historical", line=dict(color='#58a6ff')))
    
    future_dates = [df.index[-1] + datetime.timedelta(days=i) for i in range(1, 31)]
    fig_pred.add_trace(go.Scatter(x=future_dates, y=ensemble, name="Ensemble Forecast", line=dict(color='#f1c40f', width=3)))
    fig_pred.add_trace(go.Scatter(x=future_dates, y=upper, fill=None, mode='lines', line_color='rgba(241,196,15,0.2)', name='95% Conf'))
    fig_pred.add_trace(go.Scatter(x=future_dates, y=lower, fill='tonexty', mode='lines', line_color='rgba(241,196,15,0.2)', name='95% Conf'))
    
    fig_pred.update_layout(height=400, template="plotly_dark", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_pred, width='stretch')

    # Row 3: Monte Carlo Fan Chart
    st.divider()
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("🎲 Monte Carlo Path Probability (10,000 Sims)")
        vol = df['Close'].pct_change().std() * 100
        paths = run_monte_carlo_sim(curr_p, vol)
        
        fig_mc = go.Figure()
        for i in range(100): # Plot 100 sample paths
            fig_mc.add_trace(go.Scatter(x=list(range(30)), y=paths[:, i], line=dict(width=0.5, color='rgba(88,166,255,0.1)'), showlegend=False))
        
        # Percentiles
        p5 = np.percentile(paths, 5, axis=1)
        p50 = np.percentile(paths, 50, axis=1)
        p95 = np.percentile(paths, 95, axis=1)
        
        fig_mc.add_trace(go.Scatter(x=list(range(30)), y=p50, name="Median (50th)", line=dict(color='#58a6ff', width=2)))
        fig_mc.add_trace(go.Scatter(x=list(range(30)), y=p95, name="95th Pctl", line=dict(dash='dash', color='#238636')))
        fig_mc.add_trace(go.Scatter(x=list(range(30)), y=p5, name="5th Pctl", line=dict(dash='dash', color='#da3633')))
        
        fig_mc.update_layout(height=400, template="plotly_dark")
        st.plotly_chart(fig_mc, width='stretch')
    
    with c2:
        st.subheader("🛡️ Risk Metrics (VaR)")
        var_val, cvar_val = calculate_risk_metrics(paths[-1], curr_p)
        st.info(f"**Value at Risk (95%):** {var_val:,.2f}%")
        st.warning(f"**Conditional VaR (CVaR):** {cvar_val:,.2f}%")
        st.write("VaR indicates that there is a 5% chance of prices dropping by more than the stated percentage over 30 days.")

    # Row 4: News Sentiment
    st.divider()
    st.subheader("📰 Market Intelligence & Sentiment")
    news = get_news_sentiment(commodity.split(" ")[0])
    
    n_cols = st.columns(3)
    for i, item in enumerate(news):
        with n_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <h5>{item['title']}</h5>
                <p>Topic: <b>{item['topic']}</b></p>
                <span style="color: {'#238636' if item['sentiment_label'] == 'Bullish' else '#da3633'}">{item['sentiment_label']}</span>
            </div>
            """, unsafe_allow_html=True)

    # Row 5: SHAP XAI Explainability
    st.divider()
    st.subheader("🧬 Explainable AI (SHAP Feature Attribution)")
    try:
        explainer, shap_vals, X_sample = get_shap_explanations(df)
        col_xai1, col_xai2 = st.columns(2)
        with col_xai1:
            st.write("**Feature Contribution (Lag Factors)**")
            fig_shap, ax = plt.subplots()
            shap.summary_plot(shap_vals, X_sample, show=False, plot_type="bar")
            st.pyplot(fig_shap)
        with col_xai2:
            st.write("**XAI Signal Logic**")
            st.info("The summary plot shows how past 'Lag' prices (Days 1-5) contribute to the current forecast. Higher lag values typically hold the strongest predictive weight in MCX momentum.")
    except Exception as e:
        st.warning(f"SHAP Engine initializing... {e}")

    # Row 6: Portfolio Optimization
    st.divider()
    st.subheader("📈 Portfolio Optimizer (Mean-Variance)")
    try:
        # Mocking multi-asset returns for optimization display
        assets = ['Gold', 'Silver', 'Copper']
        mu = np.array([0.12, 0.15, 0.10])
        S = np.array([[0.04, 0.02, 0.01], [0.02, 0.09, 0.03], [0.01, 0.03, 0.16]])
        
        ef = EfficientFrontier(mu, S)
        weights = ef.max_sharpe()
        perf = ef.portfolio_performance(verbose=False)
        
        c_opt1, c_opt2 = st.columns(2)
        with c_opt1:
            fig_pie = go.Figure(data=[go.Pie(labels=assets, values=[weights[0], weights[1], weights[2]], hole=.3)])
            fig_pie.update_layout(title="Optimal Allocation", template="plotly_dark")
            st.plotly_chart(fig_pie, width='stretch')
        with c_opt2:
            st.write("**Performance Targets**")
            st.success(f"Expected Annual Return: {perf[0]*100:.2f}%")
            st.info(f"Annual Volatility: {perf[1]*100:.2f}%")
            st.warning(f"Sharpe Ratio: {perf[2]:.2f}")
    except:
        st.info("Calculate cross-commodity correlation to unlock optimization.")

    # Row 8: Backtesting & Export
    st.divider()
    col_back1, col_back2 = st.columns([2, 1])
    with col_back1:
        st.subheader("🧪 Strategy Backtesting (Historical)")
        cum_ret, sharpe = run_backtest(df)
        fig_back = go.Figure()
        fig_back.add_trace(go.Scatter(x=cum_ret.index, y=cum_ret, name="Strategy Performance", line=dict(color='#238636')))
        fig_back.update_layout(height=300, template="plotly_dark", title=f"Backtest Sharpe Ratio: {sharpe:.2f}")
        st.plotly_chart(fig_back, width='stretch')
    
    with col_back2:
        st.subheader("📤 Data Intelligence Export")
        st.write("Download full historical analysis and forecasting metadata.")
        csv_data = df.to_csv().encode('utf-8')
        st.download_button("📥 Download Analysis (CSV)", csv_data, f"{sym}_analysis.csv", "text/csv")
        st.button("📄 Generate PDF Report (Pro Only)", disabled=True)

    # Row 7: AI ANALYST CHATBOT
    st.divider()
    st.markdown("### 🕵️‍♂️ Senior AI Commodity Analyst | 🟢 Online")
    
    chat_asset = st.radio("Focus Commodity:", ["Gold (GC=F)", "Silver (SI=F)", "Copper (HG=F)"], horizontal=True)
    
    # Premium Quick Questions
    qq_cols = st.columns(6)
    q_data = [
        ("💰 Price", "What is gold rate today?"),
        ("📈 Trend", "Will gold increase tomorrow?"),
        ("📊 Avg Ret", "Avg increase rate of gold, silver, copper?"),
        ("🪙 Invest", "Should I buy gold now?"),
        ("⚔️ War", "What happens if war breaks out?"),
        ("🥈 vs", "Gold vs silver which is better?")
    ]
    selected_qq = None
    for i, (label, q) in enumerate(q_data):
        if qq_cols[i].button(label, use_container_width=True, key=f"qq_{i}"):
            selected_qq = q

    # Chat Area (Glassmorphism Styled Card Display)
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_history:
            role_class = "gold-accent" if "GOLD" in msg['content'].upper() else ("silver-accent" if "SILVER" in msg['content'].upper() else "copper-accent")
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    st.markdown(f'<div class="chat-bubble {role_class}">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.write(msg["content"])
            
    input_text = st.chat_input("Ask about predictions, risk, or seasonality...")
    prompt = selected_qq if selected_qq else input_text
    
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.spinner("🧠 Analyst is thinking through 7 dimensions..."):
                time.sleep(1) # Simulate deep analysis
                response = analyst.generate_response(chat_asset, prompt)
            
            with st.chat_message("assistant"):
                role_class = "gold-accent" if "GOLD" in response.upper() else ("silver-accent" if "SILVER" in response.upper() else "copper-accent")
                st.markdown(f'<div class="chat-bubble {role_class}">{response}</div>', unsafe_allow_html=True)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            # Memory cleanup (Last 10 exchanges = 20 messages)
            if len(st.session_state.chat_history) > 20:
                st.session_state.chat_history = st.session_state.chat_history[-20:]
                
    st.markdown("<p style='text-align: center; color: #888;'>Data updates every 60 seconds | institutional Grade Intelligence</p>", unsafe_allow_html=True)

else:
    st.error("Unable to load market data. Please check your internet connection or API limits.")
