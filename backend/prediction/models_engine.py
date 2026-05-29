import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.linear(out[:, -1, :])

def train_lstm(df, target_col='Close', epochs=10):
    prices = df[target_col].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled_prices = scaler.fit_transform(prices)
    
    X, y = [], []
    for i in range(20, len(scaled_prices)):
        X.append(scaled_prices[i-20:i])
        y.append(scaled_prices[i])
    X, y = np.array(X), np.array(y)
    
    X_train = torch.FloatTensor(X)
    y_train = torch.FloatTensor(y)
    
    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    for _ in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
    
    # Predict next 30 days
    model.eval()
    last_window = torch.FloatTensor(scaled_prices[-20:]).unsqueeze(0)
    preds = []
    with torch.no_grad():
        for _ in range(30):
            p = model(last_window)
            preds.append(p.item())
            last_window = torch.cat((last_window[:, 1:, :], p.unsqueeze(1)), dim=1)
            
    return scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()

def train_arima(series, order=(5,1,0)):
    model = ARIMA(series, order=order)
    model_fit = model.fit()
    return model_fit.forecast(steps=30)

def train_xgboost(df, target_col='Close'):
    # Feature engineering: lags
    df = df.copy()
    for i in range(1, 6):
        df[f'lag_{i}'] = df[target_col].shift(i)
    df.dropna(inplace=True)
    
    X = df[[f'lag_{i}' for i in range(1, 6)]].values
    y = df[target_col].values
    
    model = xgb.XGBRegressor(n_estimators=100)
    model.fit(X, y)
    
    # Prediction (recursive for 30 days)
    last_window = list(df[target_col].tail(5).values)
    preds = []
    for _ in range(30):
        p = model.predict(np.array([last_window[-5:]]))[0]
        preds.append(p)
        last_window.append(p)
    return np.array(preds)

def get_ensemble_prediction(df):
    """Combines LSTM, XGBoost and ARIMA."""
    # XGBoost
    xgb_preds = train_xgboost(df)
    
    # ARIMA
    arima_preds = train_arima(df['Close'])
    
    # LSTM
    lstm_preds = train_lstm(df)
    
    # Weighted Ensemble (Production Tuning)
    ensemble = (xgb_preds * 0.4) + (arima_preds * 0.2) + (lstm_preds * 0.4)
    
    # Confidence Intervals
    std = df['Close'].pct_change().std() * df['Close'].iloc[-1]
    upper_95 = ensemble + (1.96 * std * np.sqrt(np.arange(1, 31)))
    lower_95 = ensemble - (1.96 * std * np.sqrt(np.arange(1, 31)))
    
    return ensemble, upper_95, lower_95

import shap
def get_shap_explanations(df):
    """Calculate SHAP values for the XGBoost model."""
    target_col = 'Close'
    data = df.copy()
    for i in range(1, 6): data[f'lag_{i}'] = data[target_col].shift(i)
    data.dropna(inplace=True)
    features = [f'lag_{i}' for i in range(1, 6)]
    X = data[features]
    y = data[target_col]
    
    model = xgb.XGBRegressor(n_estimators=50)
    model.fit(X, y)
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X.tail(100))
    return explainer, shap_values, X.tail(100)
