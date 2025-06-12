# ==============================================================================
# File: alpaca_ws_client.py
# UPDATED: Added a robust reconnection loop and proper thread-safe async calls.
# ==============================================================================
import alpaca_trade_api as tradeapi
import time
import asyncio


class AlpacaWsClient:
    def __init__(self, initial_assets, data_queue, config, loop):
        self._config = config
        self._data_queue = data_queue
        self._subscribed_assets = set(initial_assets)
        self._conn = None
        self.loop = loop  # Store a reference to the main event loop

    def _handle_trade_sync(self, trade):
        """A synchronous wrapper to be called from the Alpaca thread."""
        # This schedules the async handler to be run on the main event loop
        asyncio.run_coroutine_threadsafe(
            self._handle_trade_async(trade),
            self.loop
        )

    async def _handle_trade_async(self, trade):
        """The actual async handler for processing the trade data."""
        await self._data_queue.put({
            'type': 'market_data',
            'source': 'alpaca',
            'symbol': trade.symbol,
            'price': trade.price,
            'asset_class': 'stock'
        })

    async def add_subscription(self, new_asset):
        if new_asset not in self._subscribed_assets:
            self._subscribed_assets.add(new_asset)
            if self._conn:
                print(f"Alpaca dynamically subscribing to {new_asset}")
                # The library handles calling this from the main thread
                self._conn.subscribe_trades(self._handle_trade_sync, new_asset)
            return True
        return False

    def run(self):
        print("Alpaca WS Client starting...")
        while True:
            try:
                self._conn = tradeapi.Stream(
                    key_id=self._config.APCA_API_KEY_ID,
                    secret_key=self._config.APCA_API_SECRET_KEY,
                    base_url=self._config.APCA_BASE_URL,
                    data_feed='iex'
                )

                if self._subscribed_assets:
                    for asset in list(self._subscribed_assets):
                        self._conn.subscribe_trades(self._handle_trade_sync, asset)

                self._conn.run()

            except ValueError as e:
                if "connection limit exceeded" in str(e):
                    print("Alpaca connection limit exceeded. Waiting 60 seconds before retrying...")
                    time.sleep(60)
                else:
                    print(f"Alpaca WS value error: {e}. Retrying in 10s.")
                    time.sleep(10)
            except Exception as e:
                print(f"An unexpected error occurred in Alpaca WS client: {e}. Retrying in 10s.")
                time.sleep(10)