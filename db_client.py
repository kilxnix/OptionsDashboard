# db_client.py
import os
import psycopg2

def fetch_tickers_from_db():
    """
    Connects to your Supabase (Postgres) instance and returns
    a list of all tickers in the `tickers` table.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        sslmode="require"
    )
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM tickers;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Extract just the strings:
    return [row[0] for row in rows]
