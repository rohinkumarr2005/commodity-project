import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta

# Configuration
COMMODITIES = {
    'Gold': 'GC=F',
    'Silver': 'SI=F',
    'Copper': 'HG=F'
}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dataset')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

def create_dirs():
    for d in [DATA_DIR, MODEL_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def get_historical_rates(start_date, end_date):
    print("Fetching historical USD/INR exchange rates...")
    data = yf.download("USDINR=X", start=start_date, end=end_date)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    data = data[['Close']].rename(columns={'Close': 'Rate'})
    return data

def convert_to_indian_units(df, name, rates):
    df = df.join(rates, on='Date', how='inner')
    
    # Conversion Formulas
    for col in ['Open', 'High', 'Low', 'Close']:
        if name == 'Gold':
            df[col] = (df[col] * df['Rate']) / 31.1035 * 10
        elif name == 'Silver':
            df[col] = (df[col] * df['Rate']) / 31.1035 * 1000
        elif name == 'Copper':
            df[col] = (df[col] * df['Rate']) * 2.20462
            
    return df

def fetch_and_convert_data(symbol, name, rates):
    print(f"Fetching and converting data for {name} ({symbol})...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    
    data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    if data.empty:
        return pd.DataFrame()
        
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    data.reset_index(inplace=True)
    
    data = convert_to_indian_units(data, name, rates)
    
    file_path = os.path.join(DATA_DIR, f"{name.lower()}_inr.csv")
    data.to_csv(file_path, index=False)
    return data

def preprocess_and_engineer(df):
    if len(df) < 30:
        return pd.DataFrame()
        
    df = df.copy()
    df = df.sort_values('Date')
    
    df['Prev_Close'] = df['Close'].shift(1)
    df['Price_Range'] = df['High'] - df['Low']
    df['MA7'] = df['Close'].rolling(window=7).mean()
    df['MA30'] = df['Close'].rolling(window=30).mean()
    df['Volatility'] = df['Close'].rolling(window=7).std()
    
    df['Target_Next'] = df['Close'].shift(-1)
    df['Target_7d'] = df['Close'].shift(-7)
    df['Target_30d'] = df['Close'].shift(-30)
    
    df.dropna(inplace=True)
    return df

def train_models(name, df):
    print(f"Training INR models for {name} (Rows: {len(df)})...")
    features = ['Open', 'High', 'Low', 'Volume', 'Prev_Close', 'Price_Range', 'MA7', 'MA30', 'Volatility']
    targets = ['Target_Next', 'Target_7d', 'Target_30d']
    
    X = df[features]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model_bundle = {}
    for target in targets:
        y = df[target]
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, shuffle=False)
        model = LinearRegression()
        model.fit(X_train, y_train)
        model_bundle[target] = model

    joblib.dump(model_bundle, os.path.join(MODEL_DIR, f"{name.lower()}_inr_model_bundle.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, f"{name.lower()}_inr_scaler.pkl"))

def main():
    create_dirs()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    rates = get_historical_rates(start_date, end_date)
    
    for name, symbol in COMMODITIES.items():
        df = fetch_and_convert_data(symbol, name, rates)
        df_engineered = preprocess_and_engineer(df)
        if not df_engineered.empty:
            train_models(name, df_engineered)

if __name__ == "__main__":
    main()
