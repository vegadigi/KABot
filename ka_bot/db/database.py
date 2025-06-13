# ==============================================================================
# File: database.py
# ==============================================================================
import psycopg2
from psycopg2 import pool
from datetime import datetime
import time


class DatabaseManager:
    def __init__(self, config):
        self._config, self._pool = config, None
        print("Database Manager initialized.")

    def connect(self):
        retries = 5
        while retries > 0:
            try:
                self._pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=self._config.DATABASE_URL)
                conn = self._get_connection()
                print("Database connection pool created successfully.")
                self._create_tables(conn)
                self._seed_initial_data(conn)
                self._release_connection(conn)
                return
            except psycopg2.OperationalError as e:
                print(f"FATAL: Could not connect to the database: {e}. Retrying in 5 seconds...")
                retries -= 1
                time.sleep(5)
        print("FATAL: Could not connect to database after multiple retries. Exiting.")
        exit(1)

    def _get_connection(self):
        return self._pool.getconn()

    def _release_connection(self, conn):
        self._pool.putconn(conn)

    def _create_tables(self, conn):
        commands = (
            """CREATE TABLE IF NOT EXISTS assets
            (
                id
                SERIAL
                PRIMARY
                KEY,
                symbol
                VARCHAR
               (
                20
               ) UNIQUE NOT NULL, asset_class VARCHAR
               (
                   20
               ) NOT NULL, first_seen TIMESTAMPTZ DEFAULT NOW
               (
               ));""",
            """CREATE TABLE IF NOT EXISTS monitored_assets
            (
                id
                SERIAL
                PRIMARY
                KEY,
                asset_id
                INTEGER
                NOT
                NULL
                REFERENCES
                assets
               (
                id
               ) UNIQUE, is_active BOOLEAN DEFAULT TRUE);""",
            """CREATE TABLE IF NOT EXISTS monitored_subreddits
            (
                id
                SERIAL
                PRIMARY
                KEY,
                name
                VARCHAR
               (
                100
               ) UNIQUE NOT NULL, is_active BOOLEAN DEFAULT TRUE);""",
            """CREATE TABLE IF NOT EXISTS price_ticks
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                asset_id
                INTEGER
                NOT
                NULL
                REFERENCES
                assets
               (
                id
               ), price NUMERIC
               (
                   20,
                   8
               ) NOT NULL, timestamp TIMESTAMPTZ NOT NULL);""",
            """CREATE TABLE IF NOT EXISTS technical_indicators
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                asset_id
                INTEGER
                NOT
                NULL
                REFERENCES
                assets
               (
                id
               ), timestamp TIMESTAMPTZ NOT NULL, rsi NUMERIC
               (
                   10,
                   2
               ), sma_20 NUMERIC
               (
                   20,
                   8
               ), sma_50 NUMERIC
               (
                   20,
                   8
               ), upper_bollinger NUMERIC
               (
                   20,
                   8
               ), lower_bollinger NUMERIC
               (
                   20,
                   8
               ), UNIQUE
               (
                   asset_id,
                   timestamp
               ));""",
            """CREATE TABLE IF NOT EXISTS social_posts
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                source
                VARCHAR
               (
                50
               ) NOT NULL, content TEXT NOT NULL, author VARCHAR
               (
                   100
               ), subreddit VARCHAR
               (
                   100
               ), timestamp TIMESTAMPTZ DEFAULT NOW
               (
               ));""",
            """CREATE TABLE IF NOT EXISTS sentiment_signals
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                post_id
                INTEGER
                REFERENCES
                social_posts
               (
                id
               ), asset_id INTEGER REFERENCES assets
               (
                   id
               ), sentiment_score NUMERIC
               (
                   5,
                   4
               ) NOT NULL, signal VARCHAR
               (
                   10
               ) NOT NULL, timestamp TIMESTAMPTZ DEFAULT NOW
               (
               ));""",
            """CREATE TABLE IF NOT EXISTS trades
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                signal_id
                INTEGER
                REFERENCES
                sentiment_signals
               (
                id
               ), asset_id INTEGER NOT NULL REFERENCES assets
               (
                   id
               ), trade_type VARCHAR
               (
                   4
               ) NOT NULL, price NUMERIC
               (
                   20,
                   8
               ) NOT NULL, volume NUMERIC
               (
                   20,
                   8
               ) NOT NULL, total_usd NUMERIC
               (
                   20,
                   8
               ) NOT NULL, timestamp TIMESTAMPTZ NOT NULL);"""
        )
        with conn.cursor() as cur:
            for command in commands: cur.execute(command)
        conn.commit()
        print("Database tables verified/created successfully.")

    def _seed_initial_data(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM monitored_subreddits;")
            if cur.fetchone()[0] == 0:
                print("Seeding initial subreddits...")
                default_subreddits = [('CryptoCurrency',), ('wallstreetbets',), ('stocks',)]
                cur.executemany("INSERT INTO monitored_subreddits (name) VALUES (%s);", default_subreddits)

            cur.execute("SELECT COUNT(*) FROM monitored_assets;")
            if cur.fetchone()[0] == 0:
                print("Seeding initial assets...")
                default_assets = [('BTC/USD', 'crypto'), ('ETH/USD', 'crypto')]
                for symbol, asset_class in default_assets:
                    asset_id = self.get_or_create_asset(symbol, asset_class, conn)
                    cur.execute("INSERT INTO monitored_assets (asset_id) VALUES (%s);", (asset_id,))
        conn.commit()

    def execute_query(self, query, params=None, fetch=None, conn=None):
        release_conn = False
        if conn is None:
            conn = self._get_connection()
            release_conn = True
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch: return cur.fetchone() if fetch == 'one' else cur.fetchall()
            conn.commit()
        except Exception as error:
            print(f"Database query error: {error}")
        finally:
            if release_conn and conn: self._release_connection(conn)

    def get_or_create_asset(self, symbol, asset_class='crypto', conn=None):
        asset_id = self.execute_query("SELECT id FROM assets WHERE symbol = %s;", (symbol,), fetch='one', conn=conn)
        if asset_id: return asset_id[0]
        self.execute_query("INSERT INTO assets (symbol, asset_class) VALUES (%s, %s);", (symbol, asset_class),
                           conn=conn)
        return self.execute_query("SELECT id FROM assets WHERE symbol = %s;", (symbol,), fetch='one', conn=conn)[0]

    def get_monitored_assets(self):
        rows = self.execute_query(
            "SELECT a.symbol FROM assets a JOIN monitored_assets ma ON a.id = ma.asset_id WHERE ma.is_active = TRUE;",
            fetch='all')
        return [row[0] for row in rows] if rows else []

    def get_monitored_subreddits(self):
        rows = self.execute_query("SELECT name FROM monitored_subreddits WHERE is_active = TRUE;", fetch='all')
        return [row[0] for row in rows] if rows else []