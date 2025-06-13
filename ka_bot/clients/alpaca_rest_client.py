# ==============================================================================
# File: alpaca_rest_client.py
# NEW FILE: Handles stock trading via Alpaca.
# ==============================================================================
import alpaca_trade_api as tradeapi
import asyncio

class AlpacaRestClient:
    def __init__(self, config):
        self._config = config
        self.api = tradeapi.REST(
            key_id=self._config.APCA_API_KEY_ID,
            secret_key=self._config.APCA_API_SECRET_KEY,
            base_url=self._config.APCA_BASE_URL
        )
        print("Trader Initialized (AlpacaRestClient).")

    def get_tradable_assets(self):
        try: return {asset.symbol for asset in self.api.list_assets(status='active')}
        except Exception as e: print(f"Could not fetch Alpaca assets: {e}"); return set()

    async def place_order(self, symbol, qty, side, order_type, time_in_force):
        print(f"PLACING LIVE ALPACA ORDER: {side} {qty} of {symbol}...")
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                self.api.submit_order,
                symbol,
                qty,
                side,
                order_type,
                time_in_force,
            )
        except Exception as e:
            print(f"Alpaca order failed: {e}")
            return None
