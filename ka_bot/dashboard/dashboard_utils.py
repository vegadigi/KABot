# ==============================================================================
# File: database_utils.py
# Description: A utility class for the dashboard to interact with the database.
# ==============================================================================
import psycopg2
from datetime import datetime

class DashboardDB:
    def __init__(self, db_url):
        self.db_url = db_url

    def _get_connection(self):
        try:
            return psycopg2.connect(self.db_url)
        except psycopg2.OperationalError as e:
            print(f"Dashboard DB Error: {e}")
            return None

    def execute_query(self, query, params=None, fetch=None):
        conn = self._get_connection()
        if not conn: return None
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch:
                    return cur.fetchone() if fetch == 'one' else cur.fetchall()
                conn.commit()
        except Exception as error:
            print(f"Dashboard DB query error: {error}")
            conn.rollback()
        finally:
            if conn: conn.close()

    def get_or_create_asset(self, symbol, asset_class):
        asset = self.execute_query("SELECT id FROM assets WHERE symbol = %s;", (symbol,), fetch='one')
        if asset:
            return asset[0]
        else:
            self.execute_query("INSERT INTO assets (symbol, asset_class) VALUES (%s, %s);", (symbol, asset_class))
            asset = self.execute_query("SELECT id FROM assets WHERE symbol = %s;", (symbol,), fetch='one')
            return asset[0]

    def add_monitored_asset(self, symbol, asset_class):
        try:
            asset_id = self.get_or_create_asset(symbol, asset_class)
            # Use ON CONFLICT to avoid errors if the asset is already monitored
            self.execute_query("INSERT INTO monitored_assets (asset_id, is_active) VALUES (%s, TRUE) ON CONFLICT (asset_id) DO NOTHING;", (asset_id,))
            print(f"Successfully added/verified monitored asset: {symbol}")
            return True
        except Exception as e:
            print(f"Error adding monitored asset {symbol}: {e}")
            return False

    def add_monitored_subreddit(self, name):
        try:
            # Use ON CONFLICT to avoid errors if the subreddit already exists
            self.execute_query("INSERT INTO monitored_subreddits (name, is_active) VALUES (%s, TRUE) ON CONFLICT (name) DO NOTHING;", (name,))
            print(f"Successfully added/verified monitored subreddit: r/{name}")
            return True
        except Exception as e:
            print(f"Error adding monitored subreddit r/{name}: {e}")
            return False
