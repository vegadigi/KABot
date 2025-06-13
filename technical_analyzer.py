# ==============================================================================
# File: technical_analyzer.py
# ==============================================================================
import pandas as pd
import pandas_ta as ta
from collections import defaultdict
from datetime import datetime, timezone


class TechnicalAnalyzer:
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        self.price_history = defaultdict(lambda: pd.DataFrame(columns=['close']))
        self.latest_indicators = {}
        self.latest_prices = {}
        print("Technical Analyzer initialized.")

    async def process_data_point(self, data):
        """Processes a single data point to update indicators."""
        if data.get('type') != 'market_data':
            return

        if not all(k in data for k in ['symbol', 'price', 'asset_class']):
            print(f"TECH_ANALYZER_WARNING: Skipping malformed market_data message: {data}")
            return

        try:
            symbol, price, asset_class = data['symbol'], data['price'], data['asset_class']
            timestamp = datetime.now(timezone.utc)
            self.latest_prices[symbol] = price

            new_row = pd.DataFrame([{'close': price}], index=[timestamp])
            self.price_history[symbol] = pd.concat([self.price_history[symbol], new_row]).tail(200)

            if len(self.price_history[symbol]) > 50:
                df = self.price_history[symbol]
                df.ta.rsi(length=14, append=True)
                df.ta.sma(length=20, append=True)
                df.ta.sma(length=50, append=True)
                df.ta.bbands(length=20, append=True)

                df['pct_change'] = df['close'].pct_change()
                df['volatility'] = df['pct_change'].rolling(window=20).std() * 100

                latest = df.iloc[-1]
                self.latest_indicators[symbol] = {
                    'rsi': latest.get('RSI_14'),
                    'sma_20': latest.get('SMA_20'),
                    'sma_50': latest.get('SMA_50'),
                    'upper_bollinger': latest.get('BBU_20_2.0'),
                    'lower_bollinger': latest.get('BBL_20_2.0'),
                    'volatility': latest.get('volatility')
                }
                asset_id = self.db.get_or_create_asset(symbol, asset_class)
                self.db.execute_query(
                    "INSERT INTO technical_indicators (asset_id, timestamp, rsi, sma_20, sma_50, upper_bollinger, lower_bollinger) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (asset_id, timestamp) DO NOTHING;",
                    (asset_id, timestamp, latest.get('RSI_14'), latest.get('SMA_20'), latest.get('SMA_50'),
                     latest.get('BBU_20_2.0'), latest.get('BBL_20_2.0')))
                print(
                    f"TA_LOG | Calculated indicators for {symbol} | RSI: {self.latest_indicators[symbol].get('rsi'):.2f}")
        except Exception as e:
            print(f"TECH_ANALYZER_ERROR: An unexpected error occurred during processing: {e}")