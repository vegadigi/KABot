# ==============================================================================
# File: sentiment_engine.py
# ==============================================================================
import asyncio


class SentimentEngine:
    def __init__(self, data_queue, config, traders, db, tech_analyzer, risk_manager, ai_analyzer, initial_assets):
        self.data_queue, self._config, self._traders, self._db = data_queue, config, traders, db
        self.tech, self.risk, self.analyzer = tech_analyzer, risk_manager, ai_analyzer
        self.crypto_keywords = self._generate_asset_keywords(initial_assets)
        self.stock_keywords = {}
        print("Sentiment engine initialized with AI Analyzer.")

    def _generate_asset_keywords(self, asset_list):
        k = {};
        [k.update({(b := a.split('/')[0]).upper(): a, b.lower(): a}) for a in asset_list];
        return k

    def add_asset(self, new_asset, asset_class):
        k = self.crypto_keywords if asset_class == 'crypto' else self.stock_keywords
        k.update(self._generate_asset_keywords([new_asset]) if asset_class == 'crypto' else {new_asset: new_asset})
        print(f"SentimentEngine now watching {asset_class}: {new_asset}")

    def _get_sentiment_signal(self, text):
        label, score = self.analyzer.analyze(text)
        if score < self._config.SENTIMENT_CONFIDENCE_THRESHOLD:
            return 'hold', score

        if label == 'positive': return 'buy', score
        if label == 'negative': return 'sell', score
        return 'hold', score

    def _identify_asset_in_text(self, text):
        for k, s in self.stock_keywords.items():
            if f"${k.upper()}" in text or k.upper() in text.upper().split(): return s, 'stock'
        for k, s in self.crypto_keywords.items():
            if k.lower() in text.lower(): return s, 'crypto'
        return None, None

    async def run(self):
        print("Core logic engine started...")
        while True:
            data = await self.data_queue.get()
            if data.get('type') in ('social_post', 'news_post'):
                asset, asset_class = self._identify_asset_in_text(data['text'])
                if not asset: continue

                signal, score = self._get_sentiment_signal(data['text'])
                price = self.tech.latest_prices.get(asset)
                indicators = self.tech.latest_indicators.get(asset)
                asset_id = self._db.get_or_create_asset(asset, asset_class)

                self._db.execute_query(
                    "INSERT INTO sentiment_signals(post_id,asset_id,sentiment_score,signal)VALUES(%s,%s,%s,%s);",
                    (data['post_id'], asset_id, score, signal))
                signal_id = self._db.execute_query("SELECT lastval();", fetch='one')[0]

                if signal != 'hold' and price and indicators and signal_id:
                    approved = False
                    rejection_reason = "None"
                    rsi = indicators.get('rsi')

                    if rsi is not None:
                        if signal == 'buy' and rsi <= self._config.RSI_OVERSOLD:
                            approved = True
                        elif signal == 'sell' and rsi >= self._config.RSI_OVERBOUGHT:
                            approved = True
                        else:
                            rejection_reason = f"RSI out of bounds ({rsi:.2f})"
                    else:
                        rejection_reason = "RSI not available"

                    if approved:
                        print(f"CONFIRM|{signal.upper()} for {asset} confirmed by RSI({rsi:.2f})")
                        vol_usd = self.risk.get_trade_volume_usd(asset)
                        vol_asset = vol_usd / price
                        trader = self._traders[asset_class]
                        await trader.place_order(asset, 'market', signal, vol_asset, current_price=price,
                                                 signal_id=signal_id, asset_class=asset_class, time_in_force='gtc')
                    else:
                        print(f"REJECT|{signal.upper()} for {asset} rejected. Reason: {rejection_reason}")
            await asyncio.sleep(0.01)
