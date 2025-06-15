# ==============================================================================
# File: main.py
# UPDATED: Added a simple HTTP server for status reporting.
# ==============================================================================
import asyncio
from config import Config
from db.database import DatabaseManager
from clients.kraken_ws_client import KrakenWsClient
from clients.kraken_rest_client import KrakenRestClient
from clients.alpaca_ws_client import AlpacaWsClient
from clients.alpaca_rest_client import AlpacaRestClient
from clients.reddit_client import RedditClient
from clients.news_client import FinancialNewsClient
from services.technical_analyzer import TechnicalAnalyzer
from services.risk_manager import RiskManager
from services.sentiment_engine import SentimentEngine
from analysis.ai_sentiment_analyzer import AISentimentAnalyzer
from services.mock_trader import MockTrader
from services.asset_discoverer import AssetDiscoverer
import threading
import http.server
import socketserver
import json
from datetime import datetime, timezone

# --- Shared Status Dictionary ---
status_data = {
    'kraken_ws': {'status': 'Initializing', 'last_seen': None},
    'alpaca_ws': {'status': 'Initializing', 'last_seen': None},
    'reddit_client': {'status': 'Initializing', 'last_seen': None},
    'pipeline_processor': {'status': 'Initializing', 'last_seen': None},
    'sentiment_engine': {'status': 'Initializing', 'last_seen': None},
    'asset_discoverer': {'status': 'Initializing', 'last_seen': None},
    'asset_monitor': {'status': 'Initializing', 'last_seen': None},
    'news_client': {'status': 'Initializing', 'last_seen': None},
}


def update_status(component, new_status='Running'):
    status_data[component]['status'] = new_status
    status_data[component]['last_seen'] = datetime.now(timezone.utc).isoformat()


# --- Status Server ---
class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode('utf-8'))
        else:
            self.send_error(404, "File not found")


def run_status_server():
    PORT = 8080
    with socketserver.TCPServer(("", PORT), StatusHandler) as httpd:
        print(f"Status server running at http://localhost:{PORT}")
        httpd.serve_forever()


async def main():
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}"); return

    config = Config()
    db_manager = DatabaseManager(config)
    db_manager.connect()

    initial_assets = db_manager.get_monitored_assets()
    subreddits = db_manager.get_monitored_subreddits()

    raw_data_queue = asyncio.Queue()
    processed_data_queue = asyncio.Queue()

    kraken_rest = KrakenRestClient(config)
    alpaca_rest = AlpacaRestClient(config)

    mock_trader_instance = MockTrader(config, db_manager)
    traders = {
        'crypto': kraken_rest if config.TRADE_MODE == 'live' else mock_trader_instance,
        'stock': alpaca_rest if config.TRADE_MODE == 'live' else mock_trader_instance
    }

    tech_analyzer = TechnicalAnalyzer(config, db_manager)

    initial_crypto = [a for a in initial_assets if '/' in a]
    initial_stocks = [a for a in initial_assets if '/' not in a]

    kraken_ws = KrakenWsClient(initial_crypto, raw_data_queue, config)
    loop = asyncio.get_event_loop()
    alpaca_ws = AlpacaWsClient(initial_stocks, raw_data_queue, config, loop)
    reddit_client = RedditClient(raw_data_queue, config, db_manager, subreddits)
    news_client = FinancialNewsClient(raw_data_queue, db_manager)

    ai_analyzer = AISentimentAnalyzer()
    risk_manager = RiskManager(config, tech_analyzer)

    sentiment_engine = SentimentEngine(processed_data_queue, config, traders, db_manager, tech_analyzer, risk_manager,
                                       ai_analyzer, initial_assets)
    for asset in initial_assets:
        sentiment_engine.add_asset(asset, 'crypto' if '/' in asset else 'stock')

    asset_discoverer = AssetDiscoverer(processed_data_queue, config, {'crypto': kraken_rest, 'stock': alpaca_rest},
                                       {'crypto': kraken_ws, 'stock': alpaca_ws}, sentiment_engine)

    await asset_discoverer.initialize()

    async def asset_monitor(db, kr_ws, al_ws, engine, poll_interval=30):
        print("Database asset monitor started...")
        known = set(await asyncio.to_thread(db.get_monitored_assets))
        while True:
            update_status('asset_monitor')
            current = set(await asyncio.to_thread(db.get_monitored_assets))
            new_assets = current - known
            for asset in new_assets:
                if '/' in asset:
                    if await kr_ws.add_subscription(asset):
                        engine.add_asset(asset, 'crypto')
                else:
                    if await al_ws.add_subscription(asset):
                        engine.add_asset(asset, 'stock')
            known = current
            await asyncio.sleep(poll_interval)

    async def pipeline_processor(raw_q, processed_q):
        print("Linear pipeline processor started.")
        while True:
            data = await raw_q.get()
            update_status('pipeline_processor')
            await tech_analyzer.process_data_point(data)
            await processed_q.put(data)
            raw_q.task_done()

    async def run_and_update_status(component_name, coro):
        update_status(component_name, 'Running')
        try:
            await coro
        except Exception as e:
            update_status(component_name, f'Error: {e}')
            print(f"Error in {component_name}: {e}")

    alpaca_thread = threading.Thread(target=alpaca_ws.run, daemon=True)
    alpaca_thread.start()
    update_status('alpaca_ws', 'Running')  # Assume it starts correctly

    # Start status server in a separate thread
    status_thread = threading.Thread(target=run_status_server, daemon=True)
    status_thread.start()

    print("Starting all data streams and engines...")
    await asyncio.gather(
        run_and_update_status('kraken_ws', kraken_ws.listen()),
        run_and_update_status('reddit_client', reddit_client.stream_comments()),
        run_and_update_status('news_client', news_client.poll()),
        run_and_update_status('pipeline_processor', pipeline_processor(raw_data_queue, processed_data_queue)),
        run_and_update_status('sentiment_engine', sentiment_engine.run()),
        run_and_update_status('asset_discoverer', asset_discoverer.run()),
        run_and_update_status('asset_monitor', asset_monitor(db_manager, kraken_ws, alpaca_ws, sentiment_engine))
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutting down.")