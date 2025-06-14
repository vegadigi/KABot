# ==============================================================================
# File: dashboard.py
# Description: A web-based dashboard to analyze and visualize trading performance.
# UPDATED: Now includes a System Status panel and binds to the correct host.
# ==============================================================================
import os
from flask import Flask, render_template_string, request, redirect, url_for, flash
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import requests
from datetime import datetime
from dashboard_utils import DashboardDB

# --- Configuration ---
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "trading_bot_db")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# The bot container is named 'app' in docker-compose.yml
BOT_STATUS_URL = "http://app:8080/status"

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
db = DashboardDB(DATABASE_URL)


# --- Data Fetching and Processing ---
def get_trade_data():
    query = "SELECT t.timestamp, a.symbol, a.asset_class, t.trade_type, t.price, t.volume, t.total_usd FROM trades t JOIN assets a ON t.asset_id = a.id ORDER BY t.timestamp DESC;"
    rows = db.execute_query(query, fetch='all')
    if rows is None: return pd.DataFrame()
    df = pd.DataFrame(rows,
                      columns=['timestamp', 'symbol', 'asset_class', 'trade_type', 'price', 'volume', 'total_usd'])
    for col in ['price', 'volume', 'total_usd']: df[col] = df[col].astype(float)
    return df


def calculate_portfolio_performance(df, starting_capital=10000.0):
    if df.empty: return pd.DataFrame(columns=['timestamp', 'portfolio_value'])
    df_sorted = df.sort_values(by='timestamp').copy()
    df_sorted['cash_flow'] = df_sorted.apply(lambda r: -r['total_usd'] if r['trade_type'] == 'buy' else r['total_usd'],
                                             axis=1)
    df_sorted['portfolio_value'] = starting_capital + df_sorted['cash_flow'].cumsum()
    return df_sorted[['timestamp', 'portfolio_value']]


def get_monitored_items():
    assets_query = "SELECT a.symbol, a.asset_class FROM assets a JOIN monitored_assets ma ON a.id = ma.asset_id WHERE ma.is_active = TRUE ORDER BY a.asset_class, a.symbol;"
    subreddits_query = "SELECT name FROM monitored_subreddits WHERE is_active = TRUE ORDER BY name;"
    monitored_assets = db.execute_query(assets_query, fetch='all') or []
    monitored_subreddits = db.execute_query(subreddits_query, fetch='all') or []
    return monitored_assets, [item[0] for item in monitored_subreddits]


def get_system_status():
    try:
        response = requests.get(BOT_STATUS_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not connect to bot status endpoint: {e}")
    return {}


# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Bot Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background-color: #f0f2f5; color: #333; }
        .header { background-color: #fff; padding: 20px 40px; border-bottom: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; padding: 20px; }
        .card { background-color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); padding: 20px; flex: 1 1 100%; min-width: 300px; }
        .config-card { flex-basis: 30%; }
        h1, h2 { color: #1c293a; border-bottom: 2px solid #eef2f7; padding-bottom: 10px; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        th { background-color: #f8f9fa; font-weight: 600; }
        tr:hover { background-color: #f1f1f1; }
        .buy { color: #28a745; font-weight: bold; }
        .sell { color: #dc3545; font-weight: bold; }
        form { margin-top: 20px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        input[type="text"], select { padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
        button { padding: 10px 15px; border: none; background-color: #007bff; color: white; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        button:hover { background-color: #0056b3; }
        .flash { padding: 15px; margin: 10px 0; border-radius: 4px; color: #fff; }
        .flash.success { background-color: #28a745; }
        .flash.error { background-color: #dc3545; }
        .list-group { list-style: none; padding: 0; }
        .list-group li { padding: 8px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .status-running { color: #28a745; font-weight: bold; }
        .status-initializing { color: #ffc107; }
        .status-error { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header"><h1>Trading Bot Analytics Dashboard</h1></div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %} {% for c, m in messages %} <div class="card flash {{ c }}">{{ m }}</div> {% endfor %} {% endif %}
        {% endwith %}

        <div class="card">
            <h2>System Status</h2>
            <ul class="list-group">
                {% for component, status_info in system_status.items() %}
                <li>
                    <span>{{ component.replace('_', ' ').title() }}</span>
                    <span class="status-{{ status_info.status.lower().split(':')[0] }}">{{ status_info.status }}</span>
                </li>
                {% else %}
                <li>Could not fetch system status. Is the bot running?</li>
                {% endfor %}
            </ul>
        </div>

        <div class="card">
            <h2>Portfolio Performance (Realized P&L)</h2>
            <div>{{ plot_div | safe }}</div>
        </div>

        <div class="card config-card">
            <h2>Add Monitored Asset</h2>
            <form action="{{ url_for('add_asset') }}" method="post">
                <input type="text" name="symbol" placeholder="Asset Symbol (e.g., BTC/USD or AAPL)" required size="30">
                <select name="asset_class"><option value="crypto">Crypto</option><option value="stock">Stock</option></select>
                <button type="submit">Add Asset</button>
            </form>
            <h3>Currently Monitored Assets</h3>
            <ul class="list-group">
            {% for asset, class in monitored_assets %} <li>{{ asset }} ({{ class }})</li> {% else %} <li>No assets being monitored.</li> {% endfor %}
            </ul>
        </div>

        <div class="card config-card">
            <h2>Add Monitored Subreddit</h2>
            <form action="{{ url_for('add_subreddit') }}" method="post">
                <input type="text" name="subreddit" placeholder="Subreddit Name (e.g., CryptoMoonShots)" required size="30">
                <button type="submit">Add Subreddit</button>
            </form>
            <h3>Currently Monitored Subreddits</h3>
            <ul class="list-group">
            {% for sub in monitored_subreddits %} <li>r/{{ sub }}</li> {% else %} <li>No subreddits being monitored.</li> {% endfor %}
            </ul>
        </div>

        <div class="card">
            <h2>Recent Trades (Top 50)</h2>
            <div>{{ trades_table | safe }}</div>
        </div>
    </div>
</body>
</html>
"""


# --- Flask Routes ---
@app.route('/')
def dashboard():
    trades_df = get_trade_data()
    performance_df = calculate_portfolio_performance(trades_df)
    monitored_assets, monitored_subreddits = get_monitored_items()
    system_status = get_system_status()

    plot_div = "<p>No trading data available to generate performance plot.</p>"
    if not performance_df.empty:
        fig = px.line(performance_df, x='timestamp', y='portfolio_value', title='Portfolio Value Over Time')
        plot_div = fig.to_html(full_html=False, include_plotlyjs='cdn')

    trades_display_df = trades_df.head(50).copy()
    if not trades_display_df.empty:
        trades_display_df['price'] = trades_display_df['price'].map('${:,.2f}'.format)
        trades_display_df['total_usd'] = trades_display_df['total_usd'].map('${:,.2f}'.format)
        trades_display_df['volume'] = trades_display_df['volume'].map('{:,.6f}'.format)
        trades_display_df['trade_type'] = trades_display_df['trade_type'].apply(
            lambda x: f'<span class="{x.lower()}">{x.upper()}</span>')

    trades_table = trades_display_df.to_html(index=False, classes='table', escape=False)

    return render_template_string(HTML_TEMPLATE,
                                  plot_div=plot_div,
                                  trades_table=trades_table,
                                  monitored_assets=monitored_assets,
                                  monitored_subreddits=monitored_subreddits,
                                  system_status=system_status
                                  )


@app.route('/add_asset', methods=['POST'])
def add_asset():
    symbol = request.form.get('symbol', '').strip().upper()
    asset_class = request.form.get('asset_class')
    if symbol and asset_class:
        if db.add_monitored_asset(symbol, asset_class):
            flash(f'Successfully added asset: {symbol}', 'success')
        else:
            flash(f'Failed to add asset: {symbol}', 'error')
    else:
        flash('Invalid input for asset.', 'error')
    return redirect(url_for('dashboard'))


@app.route('/add_subreddit', methods=['POST'])
def add_subreddit():
    subreddit = request.form.get('subreddit', '').strip()
    if subreddit:
        if db.add_monitored_subreddit(subreddit):
            flash(f'Successfully added subreddit: r/{subreddit}', 'success')
        else:
            flash(f'Failed to add subreddit: r/{subreddit}', 'error')
    else:
        flash('Invalid input for subreddit.', 'error')
    return redirect(url_for('dashboard'))


# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask dashboard server...")
    print("Navigate to http://127.0.0.1:5001 in your web browser.")
    # CORRECTED: Bind to '0.0.0.0' to be accessible from outside the Docker container
    app.run(debug=True, port=5000, host='0.0.0.0')