# KABot Trading Bot

This repository contains a cryptocurrency and stock trading bot driven by sentiment signals from Reddit posts and simple technical indicators. It supports both live and mock trading via Kraken and Alpaca APIs.

## Project Structure

The core application now lives in the `ka_bot` package:

```
ka_bot/
    config.py
    main.py
    clients/
        alpaca_rest_client.py
        alpaca_ws_client.py
        kraken_rest_client.py
        kraken_ws_client.py
        reddit_client.py
    services/
        sentiment_engine.py
        technical_analyzer.py
        risk_manager.py
        asset_discoverer.py
        mock_trader.py
    db/
        database.py
    analysis/
        ai_sentiment_analyzer.py
    dashboard/
        dashboard.py
        dashboard_utils.py
```

Run the bot with:

```bash
python -m ka_bot.main
```

## Micro Trading Enhancements

This update introduces a basic volatility measure and improved risk management for micro trading:

- **Volatility Tracking**: The technical analyzer now calculates short‑term price volatility based on percentage returns of the last 20 data points.
- **Dynamic Position Sizing**: The risk manager reduces trade size when volatility exceeds `Config.VOLATILITY_THRESHOLD`.

These additions help the bot adapt position sizes to market conditions when executing very small, frequent trades.
