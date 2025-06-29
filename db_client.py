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


def update_tickers_in_db(symbols, mode="replace"):
    """
    Updates the tickers table with new symbols.
    
    Args:
        symbols: List of ticker symbols to add
        mode: "replace" (clear and add new) or "append" (add to existing)
    
    Returns:
        dict with result information
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
    
    try:
        if mode == "replace":
            # Clear existing tickers
            cur.execute("DELETE FROM tickers;")
            print(f"Cleared existing tickers")
        
        # Insert new tickers (avoiding duplicates)
        for symbol in symbols:
            cur.execute(
                "INSERT INTO tickers (ticker) VALUES (%s) ON CONFLICT (ticker) DO NOTHING;",
                (symbol,)
            )
        
        conn.commit()
        
        # Get final count
        cur.execute("SELECT COUNT(*) FROM tickers;")
        total_count = cur.fetchone()[0]
        
        result = {
            "status": "success",
            "mode": mode,
            "symbols_processed": len(symbols),
            "total_in_db": total_count
        }
        
        print(f"Database update complete: {len(symbols)} symbols processed, {total_count} total in DB")
        return result
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Database update failed: {e}")
    finally:
        cur.close()
        conn.close()
