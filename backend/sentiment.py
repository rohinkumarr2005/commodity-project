import re
import math

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    print("Warning: TextBlob not installed. Falling back to dynamic lexicon-based sentiment analysis.")

# Commodity specific keyword adjustments to refine basic sentiment analysis
FINANCIAL_LEXICON = {
    # Positive keywords
    "surge": 0.8, "rally": 0.8, "boom": 0.8, "all-time high": 0.9, "deficit": 0.4, # supply deficit causes prices to rise
    "shortage": 0.4, "inflow": 0.5, "record high": 0.8, "demand": 0.3, "bullish": 0.9,
    "recovery": 0.5, "gain": 0.4, "growth": 0.4, "optimism": 0.6, "strengthen": 0.5,
    "soar": 0.7, "skyrocket": 0.8, "climb": 0.3, "upgrade": 0.5, "safe-haven": 0.4,
    
    # Negative keywords
    "slump": -0.8, "drop": -0.5, "decline": -0.5, "bearish": -0.9, "oversupply": -0.6,
    "surplus": -0.5, "plunge": -0.8, "outflow": -0.5, "fall": -0.4, "weakness": -0.5,
    "slowdown": -0.4, "recession": -0.6, "halt": -0.3, "disruption": -0.2, "cut": -0.3,
    "concern": -0.3, "uncertainty": -0.2, "tumble": -0.7, "selloff": -0.8, "downgrade": -0.5
}


def analyze_text(text):
    """
    Analyzes polarity of a text string.
    Returns polarity in the range [-1.0, 1.0].
    """
    if not text:
        return 0.0
        
    polarity = 0.0
    
    # 1. Base polarity from TextBlob if available
    if HAS_TEXTBLOB:
        try:
            polarity = TextBlob(text).sentiment.polarity
        except Exception:
            polarity = 0.0
            
    # 2. Reinforce or fallback with Commodity-Specific Financial Lexicon
    text_lower = text.lower()
    lexicon_score = 0.0
    match_count = 0
    
    for word, weight in FINANCIAL_LEXICON.items():
        # Match using word boundaries for precise matching
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            lexicon_score += weight * matches
            match_count += matches
            
    if match_count > 0:
        avg_lexicon_score = lexicon_score / match_count
        if HAS_TEXTBLOB:
            # Blend both scores (70% TextBlob, 30% Lexicon overlay for custom financial context)
            polarity = (0.7 * polarity) + (0.3 * avg_lexicon_score)
        else:
            polarity = avg_lexicon_score

    # Clamp polarity to [-1.0, 1.0]
    return max(-1.0, min(1.0, polarity))


def get_sentiment_label(polarity):
    """
    Labels polarity score.
    - Polarity > 0.05 is Positive
    - Polarity < -0.05 is Negative
    - Otherwise Neutral
    """
    if polarity > 0.05:
        return "Positive"
    elif polarity < -0.05:
        return "Negative"
    else:
        return "Neutral"


def analyze_articles(articles):
    """
    Performs sentiment analysis on a list of articles.
    Mutates articles in-place to add 'sentiment_polarity' and 'sentiment_label' keys.
    Returns a dictionary summarizing aggregate stats.
    """
    if not articles:
        return {
            "positive_pct": 0,
            "negative_pct": 0,
            "neutral_pct": 0,
            "overall_sentiment": "Neutral",
            "avg_polarity": 0.0
        }
        
    pos_count = 0
    neg_count = 0
    neu_count = 0
    total_polarity = 0.0
    
    for article in articles:
        title = article.get("title", "")
        desc = article.get("description", "")
        # Combine title and description for richer context, weighting the title twice
        combined_text = f"{title} {title} {desc}"
        
        polarity = analyze_text(combined_text)
        label = get_sentiment_label(polarity)
        
        article["sentiment_polarity"] = polarity
        article["sentiment_label"] = label
        
        total_polarity += polarity
        if label == "Positive":
            pos_count += 1
        elif label == "Negative":
            neg_count += 1
        else:
            neu_count += 1
            
    total = len(articles)
    pos_pct = round((pos_count / total) * 100)
    neg_pct = round((neg_count / total) * 100)
    neu_pct = 100 - pos_pct - neg_pct  # Ensure it sums up to exactly 100%
    
    avg_polarity = total_polarity / total
    
    # Determine aggregate market sentiment
    if avg_polarity > 0.15:
        overall = "Bullish"
    elif avg_polarity < -0.15:
        overall = "Bearish"
    else:
        overall = "Neutral"
        
    return {
        "positive_pct": pos_pct,
        "negative_pct": neg_pct,
        "neutral_pct": max(0, neu_pct),
        "overall_sentiment": overall,
        "avg_polarity": round(avg_polarity, 2)
    }
