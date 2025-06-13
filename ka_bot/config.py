# ==============================================================================
# File: config.py
# ==============================================================================
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Broker Credentials & URLs ---
    KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
    KRAKEN_PRIVATE_KEY = os.getenv("KRAKEN_PRIVATE_KEY")
    KRAKEN_REST_URL = "https://api.kraken.com"
    KRAKEN_WS_URL = "wss://ws.kraken.com/v2"

    APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")
    APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
    APCA_BASE_URL = "https://paper-api.alpaca.markets"

    # --- Data Sources ---
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "python:trading_bot:v0.1 (by /u/your_username)")

    # --- Core Logic ---
    TRADE_MODE = os.getenv("TRADE_MODE", "mock")
    SENTIMENT_CONFIDENCE_THRESHOLD = 0.6
    GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
    # --- Risk Management ---
    BASE_TRADE_VOLUME_USD = float(os.getenv("BASE_TRADE_VOLUME_USD", 20.0))
    TREND_TRADE_VOLUME_USD = float(os.getenv("TREND_TRADE_VOLUME_USD", 100.0))
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    VOLATILITY_THRESHOLD = float(os.getenv("VOLATILITY_THRESHOLD", 2.0))
    HIGH_VOLATILITY_REDUCTION_FACTOR = float(os.getenv("HIGH_VOLATILITY_REDUCTION_FACTOR", 0.5))

    # --- Asset Discovery ---
    DISCOVERY_MENTION_THRESHOLD = 10
    DISCOVERY_TIMEFRAME_SECONDS = 300

    # --- Database ---
    DB_HOST = os.getenv("DB_HOST", "db")  # IMPORTANT: Changed to 'db' for Docker networking
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "trading_bot_db")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    @staticmethod
    def validate():
        print(f"Trade mode is set to: {Config.TRADE_MODE.upper()}")
        if not all([Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME]):
            raise ValueError("Database configuration must be set in .env")
        print("Configuration loaded.")