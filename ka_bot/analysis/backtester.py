# ============================================================================
# File: backtester.py
# Description: Simple backtesting utility to evaluate strategies on historical
# price data using yfinance.
# ============================================================================
import pandas as pd
import yfinance as yf


class Backtester:
    """Download historical data and run a simple strategy backtest."""

    def __init__(self, strategy_func, starting_balance=10000):
        """Initialize with a strategy callback and starting cash."""
        self.strategy_func = strategy_func
        self.starting_balance = starting_balance

    def download_price_history(self, symbol, period="1y", interval="1d"):
        """Fetch a year of historical prices for the given symbol."""
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if not df.empty:
            df.index = pd.to_datetime(df.index)
        return df

    def run(self, symbol):
        """Execute the strategy on the symbol and return trade history."""
        prices = self.download_price_history(symbol)
        cash = self.starting_balance
        position = 0.0
        history = []

        for date, row in prices.iterrows():
            price = row["Close"]
            signal = self.strategy_func(date, row)
            if signal == "buy" and cash > 0:
                qty = cash / price
                position += qty
                cash = 0
                history.append({"date": date, "action": "buy", "price": price, "qty": qty})
            elif signal == "sell" and position > 0:
                cash += position * price
                history.append({"date": date, "action": "sell", "price": price, "qty": position})
                position = 0

        final_value = cash + position * prices.iloc[-1]["Close"] if not prices.empty else cash
        return {"history": history, "final_value": final_value}
