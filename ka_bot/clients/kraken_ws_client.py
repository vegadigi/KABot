# ==============================================================================
# File: kraken_ws_client.py
# UPDATED: Added keepalive ping settings to the WebSocket connection.
# ==============================================================================
import asyncio, websockets, json
from datetime import datetime, timezone


class KrakenWsClient:
    def __init__(self, initial_assets, data_queue, config):
        self._config, self._url, self._subscribed_assets, self._data_queue, self._connection = config, config.KRAKEN_WS_URL, set(
            initial_assets), data_queue, None

    async def connect(self):
        try:
            # Added ping_interval and ping_timeout to maintain connection
            self._connection = await websockets.connect(
                self._url,
                ping_interval=20,
                ping_timeout=20
            )
            print("Successfully connected to Kraken WebSocket API with keepalive.")
            if self._subscribed_assets: await self.subscribe(list(self._subscribed_assets))
        except Exception as e:
            print(f"Error connecting to Kraken WebSocket: {e}")

    async def subscribe(self, assets_to_sub):
        if not self._connection or not assets_to_sub: return
        msg = {"method": "subscribe", "params": {"channel": "ticker", "symbol": assets_to_sub}}
        await self._connection.send(json.dumps(msg))
        print(f"Kraken subscribed to: {assets_to_sub}")

    async def add_subscription(self, new_asset):
        if new_asset not in self._subscribed_assets:
            self._subscribed_assets.add(new_asset)
            print(f"Kraken dynamically subscribing to {new_asset}")
            await self.subscribe([new_asset]);
            return True
        return False

    async def listen(self):
        while True:
            try:
                if not self._connection or self._connection.closed:
                    await self.connect()

                async for message in self._connection:
                    data = json.loads(message)
                    if data.get('channel') == 'ticker' and 'data' in data:
                        price, symbol = float(data['data'][0]['last']), data['data'][0]['symbol']
                        await self._data_queue.put(
                            {'type': 'market_data', 'source': 'kraken', 'symbol': symbol, 'price': price,
                             'asset_class': 'crypto'})
            except websockets.exceptions.ConnectionClosed:
                print(f"Kraken WS connection closed. Reconnecting in 5 seconds...")
            except Exception as e:
                print(f"Critical error in Kraken listener: {e}. Reconnecting in 5 seconds...")

            await asyncio.sleep(5)