# ==============================================================================
# File: risk_manager.py
# NEW FILE: Determines trade size based on market conditions.
# ==============================================================================
class RiskManager:
    def __init__(self, config, tech_analyzer):
        self.config = config
        self.tech_analyzer = tech_analyzer
        print("Risk Manager initialized.")

    def get_trade_volume_usd(self, symbol):
        """Determines the appropriate trade size in USD."""
        indicators = self.tech_analyzer.latest_indicators.get(symbol)

        # Default to a small "scalping" trade size
        volume_usd = self.config.BASE_TRADE_VOLUME_USD

        if not indicators:
            return volume_usd

        # Example of a trend-following logic
        # If short-term MA is above long-term MA, it indicates an uptrend.
        is_uptrend = indicators.get('sma_20', 0) > indicators.get('sma_50', 0)
        is_downtrend = indicators.get('sma_20', 0) < indicators.get('sma_50', 0)

        if is_uptrend or is_downtrend:
            # If a clear trend is identified, use a larger trade size.
            volume_usd = self.config.TREND_TRADE_VOLUME_USD
            print(f"RISK | Trend identified for {symbol}. Increasing trade size to ${volume_usd}.")

        return volume_usd
