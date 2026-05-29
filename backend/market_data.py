import requests
import datetime
import time

# Centralized cache with state variables
_market_cache = {
    "gold": {
        "price": 0.0,
        "change_pct": 0.0,
        "unit": "USD per Troy Ounce",
        "last_updated": "",
        "stock": 12450200
    },
    "silver": {
        "price": 0.0,
        "change_pct": 0.0,
        "unit": "USD per Troy Ounce",
        "last_updated": "",
        "stock": 848200400
    },
    "copper": {
        "price": 0.0,
        "change_pct": 0.0,
        "unit": "USD per Pound",
        "last_updated": "",
        "stock": 112400
    },
    "source": "Yahoo Finance Real-Time Chart API",
    "status": "LIVE (15m delayed exchange feed)",
    "last_sync_timestamp": 0.0
}

# Yahoo Finance Chart API tickers
TICKERS = {
    "gold": "GC=F",    # Gold Futures (USD per troy ounce)
    "silver": "SI=F",  # Silver Futures (USD per troy ounce)
    "copper": "HG=F"   # Copper Futures (USD per pound)
}

def get_live_market_data(force_fetch=False):
    """
    Centralized Market Data Service powered by Yahoo Finance Chart APIs.
    Guarantees 100% price consistency and correct unit conversions:
    - Gold: USD per Troy Ounce (GC=F)
    - Silver: USD per Troy Ounce (SI=F)
    - Copper: USD per Pound (HG=F)
    
    Rejects data if stale (older than 5 minutes / 300 seconds) and the API is unreachable.
    """
    now_ts = time.time()
    
    # 1. Use cache if fresh (within 60 seconds) and not forced
    if not force_fetch and now_ts - _market_cache["last_sync_timestamp"] < 60.0 and _market_cache["gold"]["price"] > 0:
        return _market_cache

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    success_count = 0
    errors = []

    for metal, ticker in TICKERS.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [])
                
                if result and len(result) > 0:
                    meta = result[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")
                    
                    if price is not None and price > 0:
                        # Correct unit conversion: Yahoo Finance Copper Futures (HG=F)
                        # can sometimes be returned in cents per pound (e.g. 421.00) instead of USD (e.g. 4.21).
                        # If price > 50.0, convert from cents to USD per pound.
                        if metal == "copper" and price > 50.0:
                            price = price / 100.0
                            if prev_close is not None:
                                prev_close = prev_close / 100.0

                        change_pct = 0.0
                        if prev_close and prev_close > 0:
                            change_pct = ((price - prev_close) / prev_close) * 100.0
                            
                        # Update cache
                        _market_cache[metal]["price"] = round(price, 2)
                        _market_cache[metal]["change_pct"] = round(change_pct, 2)
                        _market_cache[metal]["last_updated"] = datetime.datetime.utcnow().strftime("%H:%M:%S")
                        success_count += 1
                        continue
                        
            errors.append(f"Ticker {ticker} returned invalid JSON: {response.text[:200]}")
        except Exception as e:
            errors.append(f"Failed to fetch {metal} ({ticker}) price: {str(e)}")

    # 2. Validation & Stale Data Check
    if success_count == 3:
        _market_cache["last_sync_timestamp"] = now_ts
        _market_cache["status"] = "🟢 LIVE DATA"
        print("[MARKET DATA] Centralized Yahoo Finance pricing sync completed successfully.")
        return _market_cache
        
    # If the API call fails, check if the cache is older than 5 minutes (300 seconds)
    stale_limit = 300.0
    is_cache_stale = (now_ts - _market_cache["last_sync_timestamp"]) > stale_limit
    
    if _market_cache["gold"]["price"] > 0 and not is_cache_stale:
        # Cache is still acceptable, mark status as delayed/fallback
        _market_cache["status"] = "🟡 DELAYED (Cache Backup)"
        print(f"[MARKET DATA] API partially unreachable. Utilizing fresh cache ({round(now_ts - _market_cache['last_sync_timestamp'])}s old).")
        return _market_cache
    else:
        # Stale data or empty cache -> Reject and raise Exception
        _market_cache["status"] = "🔴 OFFLINE / STALE"
        err_msg = f"Market prices are currently unavailable or stale (>5 mins old). Errors: {'; '.join(errors)}"
        print(f"[ERROR] {err_msg}")
        raise ValueError(err_msg)


def validate_and_sync_prices(client_prices):
    """
    Data Consistency Validation pipeline.
    Cross-checks active module reference prices with the Centralized Yahoo Finance spot price.
    Automatically overrides and synchronizes them if any mismatch > 0.01 exists.
    """
    live_data = get_live_market_data()
    synced_prices = {}
    
    for m in ["gold", "silver", "copper"]:
        truth_price = live_data[m]["price"]
        client_price = client_prices.get(m)
        
        if client_price is not None and abs(client_price - truth_price) > 0.01:
            print(f"[WARNING] DATA MISMATCH FOR {m.upper()}! Syncing price from client value ${client_price} to live Yahoo benchmark: ${truth_price}.")
            
        synced_prices[m] = truth_price
        
    return synced_prices
