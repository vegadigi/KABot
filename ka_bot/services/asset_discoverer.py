# ==============================================================================
# File: asset_discoverer.py
# UPDATED: Corrected logic for classifying assets.
# ==============================================================================
import asyncio
import re, time, aiohttp, json as json_parser
from collections import defaultdict


class AssetDiscoverer:
    def __init__(self, data_queue, config, rest_clients, ws_clients, sentiment_engine):
        self.data_queue, self.config, self.rest, self.ws, self.engine = data_queue, config, rest_clients, ws_clients, sentiment_engine
        self.potential_assets = defaultdict(list)
        self.known_crypto_pairs = set()
        self.known_stock_tickers = set()
        print("Asset Discoverer initialized.")

    async def initialize(self):
        print("Discoverer fetching initial lists of tradable assets...")
        kraken_pairs = await self.rest['crypto'].get_tradable_asset_pairs()
        if kraken_pairs:
            for pair_data in kraken_pairs.values():
                if 'wsname' in pair_data and pair_data['wsname'].endswith('/USD'):
                    self.known_crypto_pairs.add(pair_data['wsname'])
            print(f"Found {len(self.known_crypto_pairs)} USD-based crypto pairs on Kraken.")
        alpaca_assets = self.rest['stock'].get_tradable_assets()
        if alpaca_assets:
            self.known_stock_tickers = alpaca_assets
            print(f"Found {len(self.known_stock_tickers)} tradable stocks on Alpaca.")
            for stock in self.known_stock_tickers: self.engine.add_asset(stock, 'stock')

    async def _extract_tickers_with_ai(self, text):
        prompt = f"Analyze: '{text}'. Extract potential stock tickers (like 'TSLA', 'AAPL') and crypto tickers (like 'BTC', 'ETH'). Ignore common words. If none, return empty list."
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"responseMimeType": "application/json", "responseSchema": {"type": "OBJECT",
                                                                                                   "properties": {
                                                                                                       "tickers": {
                                                                                                           "type": "ARRAY",
                                                                                                           "items": {
                                                                                                               "type": "STRING"}}}}}}
        try:
            api_key = self.config.GEMINI_API_KEY
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            async with aiohttp.ClientSession() as s:
                async with s.post(api_url, json=payload) as r:
                    if r.status == 200:
                        res = await r.json();
                        return json_parser.loads(res['candidates'][0]['content']['parts'][0]['text']).get("tickers", [])
                    return []
        except:
            return []

    async def _validate_and_add_asset(self, ticker, asset_class):
        if asset_class == 'crypto':
            pair = f"{ticker.upper()}/USD"
            if pair in self.known_crypto_pairs:
                if await self.ws['crypto'].add_subscription(pair): self.engine.add_asset(pair, 'crypto')
        elif asset_class == 'stock':
            if ticker.upper() in self.known_stock_tickers:
                if await self.ws['stock'].add_subscription(ticker.upper()): self.engine.add_asset(ticker.upper(),
                                                                                                  'stock')
        self.potential_assets.pop(ticker, None)

    async def run(self):
        print("Asset Discoverer listening...")
        while True:
            data = await self.data_queue.get()
            if data.get('type') in ('social_post', 'news_post'):
                tickers = await self._extract_tickers_with_ai(data['text'])
                for ticker in tickers:
                    ticker_upper = ticker.upper()
                    asset_class = None
                    if ticker_upper in self.known_stock_tickers:
                        asset_class = 'stock'
                    elif f"{ticker_upper}/USD" in self.known_crypto_pairs:
                        asset_class = 'crypto'
                    else:
                        continue  # Not a known asset, ignore

                    ws_client = self.ws[asset_class]
                    asset_name = f"{ticker_upper}/USD" if asset_class == 'crypto' else ticker_upper
                    if asset_name in ws_client._subscribed_assets: continue

                    now = time.time()
                    self.potential_assets[ticker].append(now)
                    self.potential_assets[ticker] = [ts for ts in self.potential_assets[ticker] if
                                                     now - ts < self.config.DISCOVERY_TIMEFRAME_SECONDS]
                    if len(self.potential_assets[ticker]) >= self.config.DISCOVERY_MENTION_THRESHOLD:
                        print(f"DISCOVERY | High mention count for {ticker}. Validating...")
                        await self._validate_and_add_asset(ticker, asset_class)
            await asyncio.sleep(0.01)