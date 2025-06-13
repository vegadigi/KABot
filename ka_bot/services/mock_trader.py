# ==============================================================================
# File: mock_trader.py
# ==============================================================================
from datetime import datetime, timezone

class MockTrader:
    def __init__(self, config, db_manager):
        self._config, self._db = config, db_manager
        self.cash = 10000.0
        self.crypto_portfolio = {}
        self.stock_portfolio = {}
        print(f"MOCK Trader Initialized. Cash: ${self.cash:,.2f}")

    async def place_order(self, pair, o_type, side, vol, current_price, signal_id, asset_class, **kwargs):
        asset_id = self._db.get_or_create_asset(pair, asset_class)
        portfolio = self.crypto_portfolio if asset_class == 'crypto' else self.stock_portfolio

        if side == 'buy':
            trade_cost = vol * current_price
            if self.cash >= trade_cost:
                self.cash -= trade_cost
                portfolio[pair] = portfolio.get(pair, 0) + vol
                print(f"MOCK {asset_class.upper()} BUY: {vol:.6f} of {pair} @ ${current_price:,.2f}")
                self._db.execute_query("INSERT INTO trades (signal_id, asset_id, trade_type, price, volume, total_usd, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s);", (signal_id, asset_id, 'buy', current_price, vol, trade_cost, datetime.now(timezone.utc)))
        elif side == 'sell':
            volume_to_sell = portfolio.get(pair, 0)
            if volume_to_sell > 0:
                trade_value = volume_to_sell * current_price
                self.cash += trade_value
                portfolio[pair] = 0
                print(f"MOCK {asset_class.upper()} SELL: {volume_to_sell:.6f} of {pair} @ ${current_price:,.2f}")
                self._db.execute_query("INSERT INTO trades (signal_id, asset_id, trade_type, price, volume, total_usd, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s);", (signal_id, asset_id, 'sell', current_price, volume_to_sell, trade_value, datetime.now(timezone.utc)))
