import pandas as pd
import numpy as np
import plotly.graph_objects as go
from langchain.memory import ConversationBufferMemory
import datetime
import base64

class CommodityAnalystEngine:
    def __init__(self, data_modules):
        """
        data_modules: dict containing:
        - fetch_data, add_indicators, predict, run_sim, get_vol, get_news, get_seasonal, get_corr
        """
        self.dm = data_modules
        self.memory = ConversationBufferMemory(k=10)
        
    def _identify_intent(self, query):
        q = query.lower()
        if any(w in q for w in ["rate", "price", "today"]) and not any(w in q for w in ["increase", "tomorrow", "forecast", "will"]):
            return "price"
        if any(w in q for w in ["tomorrow", "increase", "decrease", "will", "next month", "forecast", "outlook"]):
            return "prediction"
        if any(w in q for w in ["avg", "average", "return", "increase rate"]):
            return "averages"
        if any(w in q for w in ["better", "compare", "vs", "instead"]):
            return "comparison"
        if any(w in q for w in ["buy", "invest", "entry", "now"]):
            return "investment"
        if any(w in q for w in ["war", "inflation", "crash", "scenario", "conflict"]):
            return "scenario"
        if "why" in q:
            return "explanation"
        if any(w in q for w in ["chance", "probability", "risk", "risky"]):
            return "risk"
        if any(w in q for w in ["allocate", "portfolio", "diversify"]):
            return "portfolio"
        return "general"

    def _get_dimension_context(self, commodity):
        comm_name = commodity.split(" ")[0]
        sym = commodity.split("(")[1].replace(")", "")
        df = self.dm['fetch_data'](sym)
        df = self.dm['add_indicators'](df)
        
        curr_p = df['Close'].iloc[-1]
        prev_p = df['Close'].iloc[-2]
        change = ((curr_p - prev_p)/prev_p)*100
        rsi = df['RSI'].iloc[-1]
        ma50 = df['MA50'].iloc[-1]
        ma200 = df['MA200'].iloc[-1]
        
        ensemble, upper, lower = self.dm['predict'](df)
        paths = self.dm['run_sim'](curr_p, df['Close'].pct_change().std()*100)
        vol_stats = self.dm['get_vol'](df)
        news = self.dm['get_news'](comm_name)
        seasonal = self.dm['get_seasonal'](comm_name)
        
        return {
            "name": comm_name, "symbol": sym, "price": curr_p, "change": change, "rsi": rsi,
            "ma50": ma50, "ma200": ma200, "forecast": {"base": ensemble[-1], "up": upper[-1], "low": lower[-1]},
            "sim": {"p5": np.percentile(paths[-1], 5), "p50": np.percentile(paths[-1], 50), "p95": np.percentile(paths[-1], 95)},
            "vol": vol_stats, "news": news, "seasonal": seasonal, "df": df
        }

    def generate_response(self, commodity, query):
        intent = self._identify_intent(query)
        ctx = self._get_dimension_context(commodity)
        
        # Element 1: Opening Summary
        summary = self._gen_summary(intent, ctx, query)
        
        # Element 2: Current Snapshot
        snapshot = f"📈 **CURRENT:** ₹{ctx['price']:,.2f} ({ctx['change']:+.2f}%) | **RSI:** {ctx['rsi']:.1f} | **Sentiment:** {ctx['news'][0]['sentiment_label']}"
        
        # Element 3: Detailed Analysis (Selected from 7 dimensions)
        analysis = self._gen_analysis(intent, ctx)
        
        # Element 4: Scenario Outlook
        outlook = self._gen_outlook(intent, ctx)
        
        # Element 5: Actionable Recommendation
        action = self._gen_action(intent, ctx)
        
        # Element 6: Risk Note
        risk = "⚠️ **RISK NOTE:** High volatility in USD/INR or sudden US Fed policy shifts could trigger a 3-5% correction. Set stop-loss orders accordingly."
        
        # Element 7: Follow-up
        followup = f"🔮 **FOLLOW-UP:** Would you like to compare {ctx['name']} with {('Silver' if 'Gold' in ctx['name'] else 'Gold')} or see a detailed 6-month forecast?"

        report = f"""### 🏛️ {ctx['name'].upper()} ANALYST INTELLIGENCE

{summary}

{snapshot}

**🔍 STRATEGIC ANALYSIS:**
{analysis}

**📊 SCENARIO SPECTRUM:**
{outlook}

{action}

{risk}

{followup}
"""
        return report

    def _gen_summary(self, intent, ctx, query):
        if intent == "price": return f"Direct Answer: The current rate for {ctx['name']} is ₹{ctx['price']:,.2f}. Markets are currently showing a {('Bullish' if ctx['change'] > 0 else 'Bearish')} bias in the intraday session."
        if intent == "prediction": return f"Strategic Outlook: Based on ensemble models, {ctx['name']} has a high probability of trading between ₹{ctx['forecast']['low']:,.0f} and ₹{ctx['forecast']['up']:,.0f} in the near term."
        if intent == "investment": return f"Investment Verdict: Current levels represent a {('favorable entry' if ctx['rsi'] < 50 else 'cautious accumulation')} zone for {ctx['name']} based on technical indicators and seasonal factors."
        return f"Analyzing your query on {ctx['name']} through our 7-dimension financial intelligence engine..."

    def _gen_analysis(self, intent, ctx):
        points = [
            f"**Technical:** Trading {('above' if ctx['price'] > ctx['ma50'] else 'below')} the 50-day moving average. RSI of {ctx['rsi']:.1f} indicates {('neutral' if 30<ctx['rsi']<70 else 'overextended')} momentum.",
            f"**Market Drivers:** Prices are reacting to {ctx['news'][0]['topic'].lower()}. News sentiment is {ctx['news'][0]['sentiment_label'].lower()}.",
            f"**Indian Context:** {ctx['seasonal']} is providing {('liquidity support' if 'demand' in ctx['seasonal'].lower() else 'a neutral floor')} for domestic MCX prices."
        ]
        if intent == "averages":
            points.append(f"**Performance:** Avg monthly return stands at {ctx['vol']['monthly_avg_ret']:+.1f}%, with a localized annual trend of {ctx['vol']['yearly_avg_ret']:+.1f}%.")
        return "\n".join([f"- {p}" for p in points])

    def _gen_outlook(self, intent, ctx):
        return f"""
- **Bull Case (35%):** Target ₹{ctx['forecast']['up']:,.0f} driven by Safe-Haven spike.
- **Base Case (50%):** Target ₹{ctx['forecast']['base']:,.0f} maintaining core trend.
- **Bear Case (15%):** Target ₹{ctx['forecast']['low']:,.0f} if US Dollar strengthens significantly."""

    def _gen_action(self, intent, ctx):
        if ctx['rsi'] < 45: 
            return f"**💡 ACTION:** STRONG BUY - Staggered entry at ₹{ctx['price']:,.0f}. Load 60% of position now."
        if ctx['rsi'] > 65:
            return "**💡 ACTION:** WAIT - Market is overextended. Look for entry at support near ₹" + f"{ctx['ma50']:,.0f}."
        return "**💡 ACTION:** ACCUMULATE - Buy on intraday dips. Range ₹" + f"{ctx['price']*0.98:,.0f} - {ctx['price']:,.0f} is ideal."
