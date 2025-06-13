# KABot Trading Bot

This repository contains a cryptocurrency and stock trading bot driven by sentiment signals from Reddit posts and simple technical indicators. It supports both live and mock trading via Kraken and Alpaca APIs.

## Micro Trading Enhancements

This update introduces a basic volatility measure and improved risk management for micro trading:

- **Volatility Tracking**: The technical analyzer now calculates short‑term price volatility based on percentage returns of the last 20 data points.
- **Dynamic Position Sizing**: The risk manager reduces trade size when volatility exceeds `Config.VOLATILITY_THRESHOLD`.

These additions help the bot adapt position sizes to market conditions when executing very small, frequent trades.
