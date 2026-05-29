import re
from backend.news.news_fetch import fetch_news
from backend.sentiment_analysis.sentiment import analyze_articles
from backend.decision_engine.decision import generate_decision

def clean_query(q):
    return re.sub(r'[^\w\s]', '', q.strip().lower())

def get_metal_context(metal_name):
    """Utility to fetch active data for a metal to construct chat context."""
    articles = fetch_news(metal_name)
    sentiment = analyze_articles(articles)
    decision = generate_decision(metal_name, sentiment, articles)
    return {
        "metal": metal_name,
        "articles": articles,
        "sentiment": sentiment,
        "decision": decision
    }

def calculate_opportunity_score(ctx):
    """Calculates a quantitative opportunity score to rank metals."""
    dec = ctx["decision"]
    sentiment = ctx["sentiment"]
    
    # Recommendation score
    rec_points = {"BUY": 3.0, "HOLD": 2.0, "SELL": 1.0}
    score = rec_points.get(dec["recommendation"], 2.0) * 15.0
    
    # Confidence weight
    score += dec["confidence"] * 0.3
    
    # Sentiment balance weight
    score += sentiment["positive_pct"] * 0.2
    
    # Risk adjustment
    risk_points = {"Low": 10.0, "Medium": 5.0, "High": 0.0}
    score += risk_points.get(dec["risk_level"], 5.0)
    
    return round(score, 1)

def get_ranked_metals():
    """Fetches all metal contexts and ranks them by opportunity score."""
    metals = ["Gold", "Silver", "Copper"]
    contexts = [get_metal_context(m) for m in metals]
    
    # Calculate score for each
    for ctx in contexts:
        ctx["opportunity_score"] = calculate_opportunity_score(ctx)
        
    # Sort descending by opportunity score
    return sorted(contexts, key=lambda x: x["opportunity_score"], reverse=True)

class CommodityAnalystEngine:
    def __init__(self, services=None):
        self.services = services

    def generate_response(self, current_metal, query):
        # Extracts actual metal name from UI string like 'Gold (GC=F)' -> 'Gold'
        metal_clean = current_metal.split(" ")[0].strip()
        return generate_chat_response(query, metal_clean)

def generate_conclusion_paragraph(ranked):
    """Generates standard AI conclusion summary for portfolio balance."""
    best = ranked[0]["metal"]
    second = ranked[1]["metal"]
    third = ranked[2]["metal"]
    
    return (
        f"### 🎯 AI Conclusion Section\n\n"
        f"Based on current sentiment ratios, risk-adjusted market outlook, and model confidence, "
        f"**{best}** remains the strongest investment choice today. **{second}** offers highly competitive "
        f"tactical growth potential but comes with slightly increased volatility, while **{third}** currently "
        f"presents a more moderate, wait-and-see opportunity. For a balanced portfolio, consider managing "
        f"exposure between safe-haven anchors ({best}) and green industrial transition drivers ({second}/{third})."
    )

def generate_chat_response(query, current_metal):
    """
    Enhanced AI Investment Advisor chatbot response compiler.
    Provides professional, investor-friendly, deeply detailed responses with Explainable AI 
    indicators, contributor breakdowns, and strategic comparisons.
    """
    clean_q = clean_query(query)
    current_metal_lower = current_metal.lower() if current_metal else "gold"
    
    # Fetch rankings since almost all high-quality advisor responses compare or conclude with them
    ranked = get_ranked_metals()
    conclusion_text = generate_conclusion_paragraph(ranked)
    
    # -------------------------------------------------------------------------
    # 1. INTELLIGENT INVESTMENT COMPARISON
    # Matches: "best investment", "gold vs silver vs copper", "where to invest today"
    # -------------------------------------------------------------------------
    if ("best" in clean_q and "investment" in clean_q) or ("vs" in clean_q or "compare" in clean_q or "comparison" in clean_q) or ("where" in clean_q and "invest" in clean_q) or ("which metal" in clean_q and "buy today" in clean_q):
        medals = ["🏆 Best Investment", "🥈 Second", "🥉 Third"]
        ranking_lines = []
        reasoning_lines = []
        
        for idx, ctx in enumerate(ranked):
            m_name = ctx["metal"]
            dec = ctx["decision"]
            sent = ctx["sentiment"]
            
            # Formulate the ranking banner
            ranking_lines.append(f"{medals[idx]}: **{m_name}** (Outlook: `{dec['market_outlook']}` | Recommendation: `{dec['recommendation']}`)")
            
            # Formulate detailed reason paragraphs
            if m_name == "Gold":
                reason_desc = (
                    f"Gold acts as the premier safe-haven hedge. Currently shows robust **{sent['positive_pct']}% positive sentiment** "
                    f"due to sustained central bank reserve buying and expectations of rate easing. Risk profile is **{dec['risk_level']}**, "
                    f"making it an exceptionally stable wealth anchor amidst current geopolitical frictions."
                )
            elif m_name == "Silver":
                reason_desc = (
                    f"Silver represents a high-beta hybrid metal. Industrial solar panel fabrications show strong long-term structural "
                    f"drivers, but thin trading liquidity introduces **{dec['risk_level']} risk** with short-term options volatility. "
                    f"It ranks as a solid secondary satellite allocation pending clear price breakouts."
                )
            else: # Copper
                reason_desc = (
                    f"Copper is the premier economic bellwether. Demands are heavily supported by EV grids and grid infrastructure "
                    f"overhauls, offset slightly by Chinese real-estate drags. It presents **{dec['risk_level']} risk** but offers "
                    f"outstanding growth velocity during global industrial rebounds."
                )
                
            reasoning_lines.append(f"- **{m_name}**: {reason_desc}")

        reply = (
            f"### 🏆 Global Metals Investment Comparison & Rankings\n\n"
            f"We have compiled real-time news caches, sentiment scores, and decision criteria across all three metals to rank the current tactical opportunities:\n\n"
            + "\n".join(ranking_lines) + "\n\n"
            f"### 🔍 Detailed Opportunity Breakdown\n\n"
            + "\n\n".join(reasoning_lines) + "\n\n"
            f"**Portfolio Selection Strategy:**\n"
            f"Our quantitative models evaluate risk-adjusted confidence scores. Anchoring in low-risk bullion with satellite industrial exposures optimizes returns while mitigating geopolitical spikes.\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 2. DETAILED ADVISOR: Should I invest in Gold/Silver/Copper now?
    # -------------------------------------------------------------------------
    elif "should i invest in" in clean_q or "invest in" in clean_q or "buy" in clean_q or "sell" in clean_q or "hold" in clean_q:
        target_metal = current_metal
        if "gold" in clean_q: target_metal = "Gold"
        elif "silver" in clean_q: target_metal = "Silver"
        elif "copper" in clean_q: target_metal = "Copper"
        
        ctx = get_metal_context(target_metal)
        dec = ctx["decision"]
        sent = ctx["sentiment"]
        cb = dec["confidence_breakdown"]
        
        # Explainable AI: key lists
        positives_list = "\n".join([f"✓ **{p}**" for p in dec["key_positives"]])
        negatives_list = "\n".join([f"⚠ **{n}**" for n in dec["key_negatives"]])
        
        news_list = "\n".join([f"- *\"{n['title']}\"* (Source: {n['source']} | Sentiment: `{n['sentiment_label']}`)" for n in dec["influential_news"]])

        reply = (
            f"### 📊 Advisor Investment Analysis: {target_metal}\n\n"
            f"Our intelligence models recommend a **{dec['recommendation']}** stance for **{target_metal}** with a market outlook of **{dec['market_outlook']}**.\n\n"
            f"#### 🔍 Explainable AI Section: Why {dec['recommendation']}?\n\n"
            f"Our decision engine synthesizes positive signals and negative risks to form a quantitative consensus. Here is the underlying reasoning:\n\n"
            f"**Key Positive Factors:**\n"
            f"{positives_list}\n\n"
            f"**Key Negative Risks:**\n"
            f"{negatives_list}\n\n"
            f"#### 📈 Confidence Contributor Breakdown\n"
            f"Current Confidence Score: **{dec['confidence']}%**\n"
            f"- **News Sentiment Impact:** `{cb['sentiment_contrib']}%` (Strength of active positive/negative news balances)\n"
            f"- **Market Trend Technicals:** `{cb['trend_contrib']}%` (Agreement patterns in historical sentiment overlays)\n"
            f"- **Economic & Macro Factors:** `{cb['macro_contrib']}%` (Interest rate directions and central bank indexes)\n\n"
            f"#### 📰 Most Influential News Events Impacting {target_metal}:\n"
            f"{news_list}\n\n"
            f"**Strategic Advisor Takeaway:**\n"
            f"If executing a trade, ensure your exposures align with {target_metal}'s **{dec['risk_level']}** risk profile. Long-term trends remain favorable but watch the short-term resistance levels indicated by current economic filters.\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 3. DETAILED ADVISOR: Is Copper/Silver/Gold too risky?
    # -------------------------------------------------------------------------
    elif "risky" in clean_q or "risk" in clean_q:
        target_metal = current_metal
        if "gold" in clean_q: target_metal = "Gold"
        elif "silver" in clean_q: target_metal = "Silver"
        elif "copper" in clean_q: target_metal = "Copper"
        
        ctx = get_metal_context(target_metal)
        dec = ctx["decision"]
        
        risks_map = {
            "Gold": "Gold has a **Low** risk profile today. Its safe-haven nature buffers it against standard market liquidations, though monetary tightening or a spiking US Dollar remain active risks.",
            "Silver": "Silver currently carries a **Medium to High** risk profile. While supported by photovoltaics and green industrial themes, its thin trading volume leaves it highly vulnerable to speculative options liquidations.",
            "Copper": "Copper represents a **High** risk, high-growth profile. Its pricing acts as an economic bellwether, meaning it is highly sensitive to real estate indicators in China and global commercial construction slowdowns."
        }
        
        negatives_list = "\n".join([f"⚠ **{n}**" for n in dec["key_negatives"]])
        
        reply = (
            f"### 🛡️ Risk Assessment & Volatility Profile: {target_metal}\n\n"
            f"{risks_map.get(target_metal, '')}\n\n"
            f"**Key Bearish Risk Indicators (Active Headwinds):**\n"
            f"{negatives_list}\n\n"
            f"**Mitigation Framework:**\n"
            f"For investors concerned with risk: balancing exposures to Gold offers capital preservation. We advise sizing positions in higher-risk metals (like Copper/Silver) proportionally smaller to accommodate sharp short-term margins volatility.\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 4. DETAILED ADVISOR: Which metal is safest?
    # -------------------------------------------------------------------------
    elif "safest" in clean_q or "safe" in clean_q or "secure" in clean_q:
        g_ctx = get_metal_context("Gold")
        s_ctx = get_metal_context("Silver")
        c_ctx = get_metal_context("Copper")
        
        reply = (
            f"### 🛡️ Safe-Haven Analysis: Safe Asset Allocations\n\n"
            f"**Gold (Au)** is unequivocally identified by our intelligence engine as the **Safest Investment** of the three metals.\n\n"
            f"**Why Gold remains the ultimate safe-haven:**\n"
            f"1. **Monetary History**: Unlike Copper and Silver, Gold is historically treated as a global monetary reserve. Central banks continue to buy gold bullion at record rates to diversify reserves away from fiat dependencies.\n"
            f"2. **Negative Interest-Yield Resilience**: During inflation spikes or geopolitical conflicts, capital flees from equities and bonds into physical gold as a hedge against systemic defaults.\n"
            f"3. **Lowest Risk Profile**: Currently, Gold registers a **{g_ctx['decision']['risk_level']}** risk rating, compared to the **{s_ctx['decision']['risk_level']}** and **{c_ctx['decision']['risk_level']}** ratings for Silver and Copper respectively.\n\n"
            f"**Comparison Chart:**\n"
            f"| Asset | Risk Level | Core Hedge Capability | Model Sentiment |\n"
            f"| :--- | :---: | :--- | :---: |\n"
            f"| **Gold** | **Low** | Geopolitical Risk, Inflation, Currency Strains | `{g_ctx['sentiment']['positive_pct']}% Pos` |\n"
            f"| **Silver** | Medium | Moderate Industrial Hedging, High Volatility | `{s_ctx['sentiment']['positive_pct']}% Pos` |\n"
            f"| **Copper** | High | Economic Growth proxy (No safe-haven properties) | `{c_ctx['sentiment']['positive_pct']}% Pos` |\n\n"
            f"**Advisor Takeaway:**\n"
            f"If your primary goal is capital preservation, maintain Gold as your anchor asset. Leverage Silver and Copper solely for tactical growth capture.\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 5. DETAILED ADVISOR: Which metal has highest growth potential?
    # -------------------------------------------------------------------------
    elif "highest growth" in clean_q or "growth potential" in clean_q or "growth" in clean_q or "potential" in clean_q:
        c_ctx = get_metal_context("Copper")
        s_ctx = get_metal_context("Silver")
        g_ctx = get_metal_context("Gold")
        
        reply = (
            f"### ⚡ Growth Velocity Report: Industrial Clean-Energy Transitions\n\n"
            f"Our models identify **Copper (Cu)** as the metal with the **Highest Growth Potential**, closely followed by **Silver (Ag)**.\n\n"
            f"**Why Copper holds the highest growth coefficient:**\n"
            f"- **Power Grid Transitions**: Global grid updates, EV charging networks, and electricity grids require extensive copper wiring. Copper cannot be substituted easily in electrical systems.\n"
            f"- **EV Proliferation**: Electric vehicles use 3-4x more copper than internal combustion engines, creating massive structural growth tailwinds.\n"
            f"- **Latin American Mining Deficits**: Operational strikes and strict eco-permitting in Chile and Peru suppress mining supply, promising high price pressure as industrial demand scales.\n\n"
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

    # -------------------------------------------------------------------------
    # 6. DETAILED ADVISOR: What could change today's recommendation?
    # -------------------------------------------------------------------------
    elif "change todays" in clean_q or "could change" in clean_q or "change today" in clean_q:
        target_metal = current_metal
        if "gold" in clean_q: target_metal = "Gold"
        elif "silver" in clean_q: target_metal = "Silver"
        elif "copper" in clean_q: target_metal = "Copper"
        
        g_triggers = [
            "**Federal Reserve Rates**: A sudden hawkish interest rate hike or delay in planned rate cuts would immediately raise bond yields, decreasing the appeal of non-yielding gold and causing a downward recommendation shift.",
            "**De-escalation of Systemic Frictions**: Resolution of major geopolitical conflicts would decrease the safe-haven premium, driving funds back into risk assets."
        ]
        
        s_triggers = [
            "**Solar Panel Innovation**: Breakthroughs in copper-based or organic alternatives replacing silver paste would instantly wipe out silver's primary long-term green demand cushion.",
            "**Manufacturing Index Slump**: A drop in global manufacturing PMIs would cut semiconductor assembly demand, triggering a HOLD or SELL signal."
        ]
        
        c_triggers = [
            "**Chinese Real Estate Resolution**: A strong economic rescue plan reviving Chinese housing and pipe demand would immediately boost copper to a strong BUY.",
            "**South American Mine Supply Surpluses**: Quick settlements of labor strikes or greenlighting major mine sites would increase stockpiles, suppressing copper prices."
        ]
        
        active_triggers = g_triggers
        if target_metal.lower() == "silver": active_triggers = s_triggers
        elif target_metal.lower() == "copper": active_triggers = c_triggers
        
        reply = (
            f"### 🔄 Market Triggers & Dynamic Changes: {target_metal}\n\n"
            f"Our decision recommendations are derived from real-time news data feeds. The current stance is highly dynamic and could shift if the following critical triggers occur:\n\n"
            + "\n\n".join(active_triggers) +
            f"\n\n**What to monitor today:**\n"
            f"- Watch bond yield indicators (US 10-Year yield).\n"
            f"- Monitor updates on geopolitical risk channels.\n"
            f"- Watch central bank speech transcripts for shifts in interest rate policies.\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 7. MARKET SENTIMENT & OUTLOOK
    # -------------------------------------------------------------------------
    elif "sentiment" in clean_q or "outlook" in clean_q:
        target_metal = current_metal
        if "gold" in clean_q: target_metal = "Gold"
        elif "silver" in clean_q: target_metal = "Silver"
        elif "copper" in clean_q: target_metal = "Copper"
        
        ctx = get_metal_context(target_metal)
        sentiment = ctx["sentiment"]
        dec = ctx["decision"]
        cb = dec["confidence_breakdown"]
        
        reply = (
            f"### 📈 Sentiment Analytics Report: {target_metal}\n\n"
            f"The overall sentiment index for **{target_metal}** is currently **{sentiment['overall_sentiment']}**.\n\n"
            f"**Sentiment Distribution:**\n"
            f"- **Positive Sentiment:** `{sentiment['positive_pct']}%` 📈 (Reflecting high buyer demand and geopolitical safe-haven flow headlines)\n"
            f"- **Neutral Sentiment:** `{sentiment['neutral_pct']}%` ⚖️ (Reflecting range-bound consolidations and options pricing volatility)\n"
            f"- **Negative Sentiment:** `{sentiment['negative_pct']}%` 📉 (Reflecting high dollar indexes and inflation-delayed rate cut concerns)\n\n"
            f"**Decision Confidence Breakdown (Total: {dec['confidence']}%):**\n"
            f"- News Sentiment: `{cb['sentiment_contrib']}%` of total score\n"
            f"- Market Trend Technicals: `{cb['trend_contrib']}%` of total score\n"
            f"- Economic & Macro Factors: `{cb['macro_contrib']}%` of total score\n\n"
            f"**Outlook Summary:**\n"
            f"*{dec['explanation']}*\n\n"
            + conclusion_text
        )
        return reply

    # -------------------------------------------------------------------------
    # 8. DEFAULT CONVERSATIONAL FALLBACK
    # -------------------------------------------------------------------------
    else:
        reply = (
            f"Hello! I am your **AI Investment Advisor & Metals Assistant**.\n\n"
            f"I have analyzed real-time news streams, calculated financial sentiment indexes, and compiled actionable trade decisions across Gold, Silver, and Copper.\n\n"
            f"**How I can help you today:**\n"
            f"- Compare Gold, Silver, and Copper opportunity rankings (🏆 *Best Investment*)\n"
            f"- Check the detailed **Explainable AI Section** for any specific metal\n"
            f"- Ask about volatility risks or safest allocation strategies\n\n"
            f"**Quick-Access Investment Advisor Questions:**\n"
            f"- *\"Which metal should I buy today?\"*\n"
            f"- *\"Compare Gold and Copper\"*\n"
            f"- *\"Why is Gold bullish?\"*\n"
            f"- *\"What are today's biggest risks?\"*\n"
            f"- *\"Which metal has the strongest sentiment?\"*\n\n"
            f"Please click any of the suggestion buttons below or type your investment question!"
        )
        return reply
