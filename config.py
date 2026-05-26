"""
Configuration settings for the Commodity Intelligence System
Matches Day-1 config.py specification.
"""
import os


class Config:
    # Flask / FastAPI settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'commodity-ai-2026')
    DEBUG = True

    # Database
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'commodity.db')

    # Commodities to track
    COMMODITIES = {
        'gold':   {'symbol': 'GC=F', 'name': 'Gold',   'unit': 'USD/oz'},
        'silver': {'symbol': 'SI=F', 'name': 'Silver', 'unit': 'USD/oz'},
        'copper': {'symbol': 'HG=F', 'name': 'Copper', 'unit': 'USD/lb'},
    }

    # Data settings
    DATA_PERIOD = '5y'          # 5 years of historical data
    DATA_INTERVAL = '1d'        # Daily data

    # Model settings
    TRAIN_TEST_SPLIT = 0.8      # 80% train, 20% test
    PREDICTION_DAYS = [1, 7, 30]  # Next day, week, month

    # Feature engineering parameters
    MA_WINDOWS = [5, 10, 20, 50]   # Moving average windows
    VOLATILITY_WINDOW = 20          # Volatility calculation window
