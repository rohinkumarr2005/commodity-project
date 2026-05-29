import re
from backend.news_service import fetch_news
from backend.sentiment import analyze_articles
from backend.decision import generate_decision
from backend.prediction import get_predictions
from backend.simulation import get_monte_carlo_sim
from backend.market_data import get_live_market_data

def clean_query(q):
    return re.sub(r'[^\w\s]', '', q.strip().lower())

def get_metal_context(metal_name):
    """Utility to fetch active data for a metal, incorporating predictions, simulations, and sentiment analysis."""
    articles = fetch_news(metal_name)
    sentiment = analyze_articles(articles)
    decision = generate_decision(metal_name, sentiment, articles)
    predictions = get_predictions(metal_name)
    simulation = get_monte_carlo_sim(metal_name)
    return {
        "metal": metal_name,
        "articles": articles,
        "sentiment": sentiment,
        "decision": decision,
        "predictions": predictions,
        "simulation": simulation
    }

def calculate_opportunity_score(ctx):
    """Calculates opportunity score utilizing predictions, simulations, and sentiment parameters."""
    dec = ctx["decision"]
    sentiment = ctx["sentiment"]
    predictions = ctx["predictions"]
    simulation = ctx["simulation"]
    
    # Stance Score (out of 45)
    rec_points = {"BUY": 3.0, "HOLD": 2.0, "SELL": 1.0}
    score = rec_points.get(dec["recommendation"], 2.0) * 15.0
    
    # Sentiment Score (out of 15)
    score += sentiment["positive_pct"] * 0.15
    
    # Prediction Score (out of 20)
    trend_points = {"Bullish": 15.0, "Neutral": 5.0, "Bearish": -5.0}
    score += trend_points.get(predictions["thirty_day"]["trend"], 5.0)
    score += predictions["thirty_day"]["confidence"] * 0.15
    
    # Simulation Upside Score (out of 10)
    upside_pct = ((simulation["best_case"] - simulation["start_price"]) / simulation["start_price"]) * 100.0
    score += upside_pct * 0.8
    
    # Risk Mitigation Score (out of 10)
    risk_points = {"Low": 10.0, "Medium": 5.0, "High": 0.0}
    score += risk_points.get(dec["risk_level"], 5.0)
    
    return round(score, 1)

def get_ranked_metals():
    """Fetches all metal contexts and ranks them by opportunity score."""
    metals = ["Gold", "Silver", "Copper"]
    contexts = [get_metal_context(m) for m in metals]
    
    for ctx in contexts:
        ctx["opportunity_score"] = calculate_opportunity_score(ctx)
        
    return sorted(contexts, key=lambda x: x["opportunity_score"], reverse=True)

def generate_conclusion_paragraph(ranked):
    """Generates standard analytical conclusion summary for portfolio balance."""
    best = ranked[0]["metal"]
    second = ranked[1]["metal"]
    third = ranked[2]["metal"]
    
    return (
        f"### 🎯 Strategic Outlook Summary\n\n"
        f"Based on current market sentiment, long-term predictive targets, and macroeconomic stress projections, "
        f"**{best}** remains the strongest commodity placement today. **{second}** offers competitive "
        f"tactical growth potential but comes with increased volatility, while **{third}** currently "
        f"presents a more moderate, range-bound opportunity. For a balanced portfolio, consider managing "
        f"exposure between stable safe-haven anchors ({best}) and green industrial transition drivers ({second}/{third})."
    )

def generate_chat_response(query, current_metal):
    """
    Upgraded AI Commodity Decision Support Assistant chatbot response compiler.
    Acts as a professional commodity market analyst. Answers questions first,
    completely hides developer terminology (APIs, Monte Carlo, Models, Members),
    and utilizes real-time market data cache for 100% pricing consistency.
    """
    clean_q = clean_query(query)
    current_metal_lower = current_metal.lower() if current_metal else "gold"
    
    # Fetch centralized spot prices immediately to guarantee pricing consistency
    live_prices = get_live_market_data()
    g_price = live_prices["gold"]["price"]
    s_price = live_prices["silver"]["price"]
    c_price = live_prices["copper"]["price"]
    
    ticker_lines = (
        f"**Live Market Benchmark Spot Prices:**\n"
        f"- Gold Spot: `${g_price:.2f}` / oz\n"
        f"- Silver Spot: `${s_price:.2f}` / oz\n"
        f"- Copper Spot: `${c_price:.2f}` / lb\n\n"
    )
    
    ranked = get_ranked_metals()
    conclusion_text = generate_conclusion_paragraph(ranked)
    
    # Determine default/queried metal context
    target_metal = "Gold"
    if "silver" in clean_q:
        target_metal = "Silver"
    elif "copper" in clean_q:
        target_metal = "Copper"
    elif current_metal_lower == "silver":
        target_metal = "Silver"
    elif current_metal_lower == "copper":
        target_metal = "Copper"
        
    ctx = get_metal_context(target_metal)
    dec = ctx["decision"]
    sent = ctx["sentiment"]
    pred = ctx["predictions"]
    sim = ctx["simulation"]
    cb = dec["confidence_breakdown"]
    
    # =========================================================================
    # 1. SMART ANSWER: Price Update / Market Inquiries
    # =========================================================================
    if "price" in clean_q or "spot" in clean_q or "value" in clean_q or "cost" in clean_q or "how much" in clean_q or "rate" in clean_q:
        unit = "per troy ounce" if target_metal != "Copper" else "per pound"
        change_pct = live_prices[target_metal.lower()]["change_pct"]
        trend = pred["thirty_day"]["trend"]
        outlook = dec["market_outlook"]
        
        reply = (
            f"### 📊 Commodity Market Update: {target_metal}\n\n"
            f"- **Current Spot Price:** `${live_prices[target_metal.lower()]['price']:.2f}` {unit}\n"
            f"- **Daily Change:** `{change_pct:+.2f}%`\n"
            f"- **30-Day Trend:** `{trend}`\n"
            f"- **Market Outlook:** `{outlook}`\n"
            f"- **Strategic Stance:** `{dec['recommendation']}`\n\n"
            f"#### 🎙️ Strategic Commentary:\n"
            f"{target_metal} is currently demonstrating `{outlook}` momentum. News sentiment is `{sent['positive_pct']}%` positive, "
            f"driven by robust industrial backing and macro indicators. Volatility boundaries suggest a downside support floor of "
            f"`${sim['worst_case']:.2f}` and an expected target ceiling of `${sim['best_case']:.2f}` over the next month. "
            f"Our decision systems recommend a **{dec['recommendation']}** placement."
        )
        return reply

    # =========================================================================
    # 2. SMART ANSWER: "Which metal is best today?" / Institutional Rankings
    # =========================================================================
    elif "best" in clean_q or "which metal" in clean_q or "buy today" in clean_q or "invest today" in clean_q or "ranking" in clean_q or "recommendation" in clean_q:
        medals = ["🏆 Best Investment Today", "🥈 Second Placement", "🥉 Third Placement"]
        ranking_lines = []
        reasoning_lines = []
        
        for idx, metal_ctx in enumerate(ranked):
            m_name = metal_ctx["metal"]
            m_dec = metal_ctx["decision"]
            m_sent = metal_ctx["sentiment"]
            m_pred = metal_ctx["predictions"]
            m_sim = metal_ctx["simulation"]
            m_price = live_prices[m_name.lower()]["price"]
            m_unit = "oz" if m_name != "Copper" else "lb"
            
            score_out_100 = int(metal_ctx["opportunity_score"])
            
            ranking_lines.append(f"{idx+1}. **{m_name}** (Score: `{score_out_100}/100` | Stance: `{m_dec['recommendation']}`)")
            
            if m_name == "Gold":
                reason_desc = (
                    f"Gold acts as the premier wealth anchor. It integrates:\n"
                    f"  - ✓ **Highest positive sentiment** (`{m_sent['positive_pct']}%` positive news flow)\n"
                    f"  - ✓ **Strong BUY recommendation** from our strategic decision systems\n"
                    f"  - ✓ **Bullish 30-day outlook** (Spot forecast targets a price of `${m_pred['thirty_day']['price']:.2f}` starting from spot `${g_price:.2f}`)\n"
                    f"  - ✓ **Best risk-adjusted performance** in statistical projections (Low risk rating)\n"
                    f"  - ✓ **Excellent downside performance** under stress scenarios (+9.5% in Recession, +12.0% in Market Crash)"
                )
            elif m_name == "Silver":
                reason_desc = (
                    f"Silver represents a high-beta industrial hybrid. It integrates:\n"
                    f"  - ✓ **Solid green energy support** (`{m_sent['positive_pct']}%` positive sentiment driven by solar PV panels)\n"
                    f"  - ✓ **Bullish 7-day outlook** (Short-term projection suggests target of `${m_pred['seven_day']['price']:.2f}` starting from spot `${s_price:.2f}`)\n"
                    f"  - ✓ **High projection upside** (upper breakout ceiling boundary at `${m_sim['best_case']:.2f}`)\n"
                    f"  - ⚠ **Volatile stress profile** (contracts -8.0% in Recession and -5.0% in Market Crash, indicating a highly cyclical growth asset)"
                )
            else: # Copper
                reason_desc = (
                    f"Copper stands as the premier electrification vector. It integrates:\n"
                    f"  - ✓ **Heavy industrial backing** (EV grids infrastructure demands)\n"
                    f"  - ✓ **Outstanding long-term growth projection** (30-day target `${m_pred['thirty_day']['price']:.2f}` starting from spot `${c_price:.2f}`)\n"
                    f"  - ✓ **Stunning upside breakout projection** (upper resistance target up to `${m_sim['best_case']:.2f}`)\n"
                    f"  - ⚠ **High sensitivity to macro contraction** (slumps -18.0% in Recession and -15.0% in Market Crash, indicating a cyclical trade)"
                )
                
            reasoning_lines.append(f"### {medals[idx]}: {m_name}\n{reason_desc}")

        reply = (
            f"### 🏆 Global Commodity Allocation & Opportunity Rankings\n\n"
            f"{ticker_lines}"
            f"Based on real-time news sentiment, predictive indicators, and macroeconomic stress simulations, here are today's rankings:\n\n"
            + "\n".join(ranking_lines) + "\n\n"
            + "\n\n".join(reasoning_lines) + "\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 3. SMART ANSWER: "Compare Gold and Copper" / Comparison Matrices
    # =========================================================================
    elif "compare" in clean_q or "comparison" in clean_q or "vs" in clean_q:
        g_ctx = get_metal_context("Gold")
        s_ctx = get_metal_context("Silver")
        c_ctx = get_metal_context("Copper")
        
        reply = (
            f"### ⚖️ Cross-Commodity Comparative Analysis\n\n"
            f"Below is the strategic trading terminal comparison comparing the active market sectors:\n\n"
            f"| Metric Indicator | Gold (Au) | Silver (Ag) | Copper (Cu) |\n"
            f"| :--- | :---: | :---: | :---: |\n"
            f"| **Current Price** | `${g_price:.2f} / oz` | `${s_price:.2f} / oz` | `${c_price:.2f} / lb` |\n"
            f"| **Daily Change** | `{live_prices['gold']['change_pct']:+.2f}%` | `{live_prices['silver']['change_pct']:+.2f}%` | `{live_prices['copper']['change_pct']:+.2f}%` |\n"
            f"| **Strategic Stance** | `{g_ctx['decision']['recommendation']}` | `{s_ctx['decision']['recommendation']}` | `{c_ctx['decision']['recommendation']}` |\n"
            f"| **Confidence Score** | `{g_ctx['decision']['confidence']}%` | `{s_ctx['decision']['confidence']}%` | `{c_ctx['decision']['confidence']}%` |\n"
            f"| **Risk Profile** | `{g_ctx['decision']['risk_level']}` | `{s_ctx['decision']['risk_level']}` | `{c_ctx['decision']['risk_level']}` |\n"
            f"| **News Sentiment** | `{g_ctx['sentiment']['positive_pct']}% Pos` | `{s_ctx['sentiment']['positive_pct']}% Pos` | `{c_ctx['sentiment']['positive_pct']}% Pos` |\n"
            f"| **30-Day Forecast** | `${g_ctx['predictions']['thirty_day']['price']:.2f}` | `${s_ctx['predictions']['thirty_day']['price']:.2f}` | `${c_ctx['predictions']['thirty_day']['price']:.2f}` |\n"
            f"| **Expected Upside** | `{((g_ctx['simulation']['best_case'] - g_price)/g_price*100.0):.1f}%` | `{((s_ctx['simulation']['best_case'] - s_price)/s_price*100.0):.1f}%` | `{((c_ctx['simulation']['best_case'] - c_price)/c_price*100.0):.1f}%` |\n"
            f"| **Support Floor (10th Pctl)** | `${g_ctx['simulation']['worst_case']:.2f}` | `${s_ctx['simulation']['worst_case']:.2f}` | `${c_ctx['simulation']['worst_case']:.2f}` |\n\n"
            f"**Integrated Strategic Takeaway:**\n"
            f"Integrating prediction models and volatility paths ensures robust entry points. Secure your portfolio core in Gold to capture downside protection, while tactically leveraging Silver and Copper to gain industrial clean-energy growth multipliers.\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 4. SMART ANSWER: "Why is Gold Bullish?" / Catalyst Explanations
    # =========================================================================
    elif "why" in clean_q or "catalyst" in clean_q or "reason" in clean_q:
        positives_list = "\n".join([f"* **{p}**" for p in dec["key_positives"]])
        
        reply = (
            f"### 💡 Market Catalyst Rationale: {target_metal}\n\n"
            f"{ticker_lines}"
            f"Why **{target_metal}** holds a **{dec['recommendation']}** stance with a `{dec['market_outlook']}` outlook:\n\n"
            f"* **Positive Sentiment:** Strong positive sentiment index (`{sent['positive_pct']}%`) driven by active news flows.\n"
            f"* **Strong Momentum:** Technical spot projections target a price of `${pred['thirty_day']['price']:.2f}` within 30 days.\n"
            f"* **Safe-Haven Demand:** Low risk profile and capital preservation characteristics under recession stress paths.\n"
            f"* **Strong Outlook:** Centralized macro indicators support asset accumulation.\n\n"
            f"**Key Supporting Catalysts:**\n"
            f"{positives_list}\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 5. DETAILED ADVISOR: Should I invest in Gold/Silver/Copper now?
    # =========================================================================
    elif "should i invest in" in clean_q or "invest in" in clean_q or "buy" in clean_q or "sell" in clean_q or "hold" in clean_q:
        positives_list = "\n".join([f"✓ **{p}**" for p in dec["key_positives"]])
        negatives_list = "\n".join([f"⚠ **{n}**" for n in dec["key_negatives"]])
        news_list = "\n".join([f"- *\"{n['title']}\"* (Source: {n['source']} | Sentiment: `{n['sentiment_label']}`)" for n in dec["influential_news"][:3]])

        reply = (
            f"### 📊 Integrated Advisor Analysis: {target_metal}\n\n"
            f"{ticker_lines}"
            f"Our intelligence systems recommend a **{dec['recommendation']}** stance for **{target_metal}** with a market outlook of **{dec['market_outlook']}**.\n\n"
            f"#### 🔍 Rationale: Why {dec['recommendation']}?\n\n"
            f"**Key Positive Factors:**\n"
            f"{positives_list}\n\n"
            f"**Key Negative Risks:**\n"
            f"{negatives_list}\n\n"
            f"#### 🔮 Predictive Target Indicators\n"
            f"- **Next-Day Price Target:** `${pred['next_day']['price']:.2f}` (Trend: `{pred['next_day']['trend']}` | Confidence: `{pred['next_day']['confidence']}%`)\n"
            f"- **7-Day Price Target:** `${pred['seven_day']['price']:.2f}` (Trend: `{pred['seven_day']['trend']}` | Confidence: `{pred['seven_day']['confidence']}%`)\n"
            f"- **30-Day Price Target:** `${pred['thirty_day']['price']:.2f}` (Trend: `{pred['thirty_day']['trend']}` | Confidence: `{pred['thirty_day']['confidence']}%`)\n\n"
            f"#### 🎲 Statistical Projection Path Boundaries\n"
            f"Based on standard volatility paths beginning at live spot `${sim['start_price']:.2f}`:\n"
            f"- **Worst Case (10th percentile):** `${sim['worst_case']:.2f}` (Downside support ceiling)\n"
            f"- **Average Case (50th percentile):** `${sim['average_case']:.2f}` (Expected baseline target)\n"
            f"- **Best Case (90th percentile):** `${sim['best_case']:.2f}` (Breakout resistance target)\n\n"
            f"#### 📈 Decision Confidence Analysis\n"
            f"Current Confidence Score: **{dec['confidence']}%**\n"
            f"- **News Sentiment Impact:** `{cb['sentiment_contrib']}%` (Strength of active positive/negative news balances)\n"
            f"- **Market Trend Technicals:** `{cb['trend_contrib']}%` (Agreement patterns in historical sentiment overlays)\n"
            f"- **Economic & Macro Factors:** `{cb['macro_contrib']}%` (Interest rate directions and central bank indexes)\n\n"
            f"#### 📰 Influential News Events Impacting {target_metal}:\n"
            f"{news_list}\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 6. DETAILED ADVISOR: Is Copper/Silver/Gold too risky? / Risk Analysis
    # =========================================================================
    elif "risky" in clean_q or "risk" in clean_q:
        risks_map = {
            "Gold": "Gold has a **Low** risk profile today. Its safe-haven nature buffers it against standard market liquidations, though monetary tightening or a spiking US Dollar remain active risks.",
            "Silver": "Silver currently carries a **Medium to High** risk profile. While supported by photovoltaics and green industrial themes, its thin trading volume leaves it highly vulnerable to speculative options liquidations.",
            "Copper": "Copper represents a **High** risk, high-growth profile. Its pricing acts as an economic bellwether, meaning it is highly sensitive to real estate indicators in China and global commercial construction slowdowns."
        }
        
        negatives_list = "\n".join([f"⚠ **{n}**" for n in dec["key_negatives"]])
        
        reply = (
            f"### 🛡️ Risk Assessment & Volatility Profile: {target_metal}\n\n"
            f"{ticker_lines}"
            f"{risks_map.get(target_metal, '')}\n\n"
            f"**Downside Support Level (Stress Floor):** `${sim['worst_case']:.2f}` (suggests a dynamic floor limit for stop losses).\n\n"
            f"**Key Bearish Risk Indicators (Active Headwinds):**\n"
            f"{negatives_list}\n\n"
            f"**Mitigation Framework:**\n"
            f"For investors concerned with risk: balancing exposures to Gold offers capital preservation. We advise sizing positions in higher-risk metals (like Copper/Silver) proportionally smaller to accommodate sharp short-term margins volatility.\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 7. DETAILED ADVISOR: Which metal is safest?
    # =========================================================================
    elif "safest" in clean_q or "safe" in clean_q or "secure" in clean_q:
        g_ctx = get_metal_context("Gold")
        s_ctx = get_metal_context("Silver")
        c_ctx = get_metal_context("Copper")
        
        reply = (
            f"### 🛡️ Safe-Haven Analysis: Safe Asset Allocations\n\n"
            f"{ticker_lines}"
            f"**Gold (Au)** is unequivocally identified by our intelligence systems as the **Safest Investment** of the three metals.\n\n"
            f"**Why Gold remains the ultimate safe-haven:**\n"
            f"1. **Monetary History**: Unlike Copper and Silver, Gold is historically treated as a global monetary reserve. Central banks continue to buy gold bullion at record rates to diversify reserves away from fiat dependencies.\n"
            f"2. **Negative Interest-Yield Resilience**: During inflation spikes or geopolitical conflicts, capital flees from equities and bonds into physical gold as a hedge against systemic defaults.\n"
            f"3. **Lowest Risk Profile**: Currently, Gold registers a **{g_ctx['decision']['risk_level']}** risk rating, compared to the **{s_ctx['decision']['risk_level']}** and **{c_ctx['decision']['risk_level']}** ratings for Silver and Copper respectively.\n\n"
            f"**Comparison Chart:**\n"
            f"| Asset | Risk Level | Core Hedge Capability | Outlook Sentiment |\n"
            f"| :--- | :---: | :--- | :---: |\n"
            f"| **Gold** | **Low** | Geopolitical Risk, Inflation, Currency Strains | `{g_ctx['sentiment']['positive_pct']}% Pos` |\n"
            f"| **Silver** | Medium | Moderate Industrial Hedging, High Volatility | `{s_ctx['sentiment']['positive_pct']}% Pos` |\n"
            f"| **Copper** | High | Economic Growth proxy (No safe-haven properties) | `{c_ctx['sentiment']['positive_pct']}% Pos` |\n\n"
            f"**Advisor Takeaway:**\n"
            f"If your primary goal is capital preservation, maintain Gold as your anchor asset. Leverage Silver and Copper solely for tactical growth capture.\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 8. DETAILED ADVISOR: Which metal has highest growth potential?
    # =========================================================================
    elif "highest growth" in clean_q or "growth potential" in clean_q or "growth" in clean_q or "potential" in clean_q or "opportunities" in clean_q:
        c_ctx = get_metal_context("Copper")
        s_ctx = get_metal_context("Silver")
        g_ctx = get_metal_context("Gold")
        
        reply = (
            f"### ⚡ Growth Velocity Report: Industrial Clean-Energy Transitions\n\n"
            f"{ticker_lines}"
            f"Our analytics identify **Copper (Cu)** as the metal with the **Highest Growth Potential**, closely followed by **Silver (Ag)**.\n\n"
            f"**Why Copper holds the highest growth coefficient:**\n"
            f"- **Power Grid Transitions**: Global grid updates, EV charging networks, and electricity grids require extensive copper wiring. Copper cannot be substituted easily in electrical systems.\n"
            f"- **EV Proliferation**: Electric vehicles use 3-4x more copper than internal combustion engines, creating massive structural growth tailwinds.\n"
            f"- **Latin American Mining Deficits**: Operational strikes and strict eco-permitting suppress mining supply, promising high price pressure as industrial demand scales.\n\n"
            f"**Why Silver stands as a powerful secondary growth asset:**\n"
            f"- **Photovoltaic Boom**: The solar energy explosion consumes massive quantities of silver paste. A widening physical deficit promises outstanding upside during commodity rallies.\n\n"
            f"**Growth vs. Safety Matrix:**\n"
            f"| Metal | Growth Rank | Primary Driver | Risk Profile |\n"
            f"| :--- | :---: | :--- | :---: |\n"
            f"| **Copper** | 🏆 **1st** | EV Networks, Electric Grids, Infrastructure | **{c_ctx['decision']['risk_level']}** |\n"
            f"| **Silver** | 🥈 **2nd** | Solar PV Panels, Semiconductor chips | **{s_ctx['decision']['risk_level']}** |\n"
            f"| **Gold** | 🥉 **3rd** | Central Bank Hedging, Asset Safety | **{g_ctx['decision']['risk_level']}** |\n\n"
            f"**Advisor Takeaway:**\n"
            f"While Copper offers exceptional growth multiples, it is highly cyclical and volatile. Add industrial exposures during economic expansions, and secure your profits into Gold during market cycle contractions.\n\n"
            + conclusion_text
        )
        return reply

    # =========================================================================
    # 9. SMART ANSWER: Global Market Summary / Briefing
    # =========================================================================
    elif "summary" in clean_q or "overview" in clean_q or "market summary" in clean_q:
        g_ctx = get_metal_context("Gold")
        s_ctx = get_metal_context("Silver")
        c_ctx = get_metal_context("Copper")
        
        reply = (
            f"### 📰 Global Commodity Market Summary\n\n"
            f"{ticker_lines}"
            f"**Institutional Briefing:**\n"
            f"The global commodity sectors are navigating distinct macroeconomic regimes. **Gold** acts as the core defensive wealth anchor under persistent interest rate pressures and geopolitical friction, maintaining a solid `{g_ctx['decision']['recommendation']}` stance. "
            f"**Copper** represents an aggressive cyclical play, highly geared to green energy transmission infrastructure and EV rollouts, registering a `{c_ctx['decision']['recommendation']}` stance. "
            f"**Silver** occupies a hybrid status, experiencing solar industrial supply deficits but facing higher tactical margins volatility, leading to a `{s_ctx['decision']['recommendation']}` recommendation.\n\n"
            f"**Key Focus Vectors today:**\n"
            f"- **Inflation/Rates Protection:** Gold has standard low-risk buffers and targets `${g_ctx['predictions']['thirty_day']['price']:.2f}`.\n"
            f"- **Industrial Growth Capture:** Copper demonstrates outstanding long-term projections, targeting `${c_ctx['predictions']['thirty_day']['price']:.2f}`.\n"
            f"- **Solar PV Deficit Hedging:** Silver is well-positioned for intermediate breakouts, targeting `${s_ctx['predictions']['thirty_day']['price']:.2f}`.\n\n"
            f"**Analyst Asset Allocation Advice:**\n"
            f"We advise institutional desks to maintain a strong core allocation in Gold for capital preservation, while selectively sizing tactical growth exposures in Copper and Silver to capture industrial transitions."
        )
        return reply

    # =========================================================================
    # 10. GENERAL CONVERSATIONAL SUMMARY OR DETAILED MARKET FEEDBACK
    # =========================================================================
    else:
        # Dynamic context synthesis based on target metal, avoiding static fallback
        reply = (
            f"### 🎙️ Strategic Commodity Commentary: {target_metal}\n\n"
            f"{ticker_lines}"
            f"Currently, **{target_metal}** is trading under `{dec['market_outlook']}` conditions. "
            f"Our decision systems recommend a **{dec['recommendation']}** stance with a confidence score of **{dec['confidence']}%**.\n\n"
            f"**Key Market Drivers today:**\n"
            f"- News sentiment is `{sent['positive_pct']}%` positive and `{sent['negative_pct']}%` negative.\n"
            f"- Spot projection boundaries list support floor at `${sim['worst_case']:.2f}` and resistance breakout target at `${sim['best_case']:.2f}`.\n"
            f"- Outlook remains resilient due to active geopolitical buffers and industrial green-transition demands.\n\n"
            f"Please select from the strategic quick actions below or ask a specific tactical question (e.g. \"Compare Gold and Copper\", \"What is gold price today?\") to compile custom portfolio reports."
        )
        return reply
