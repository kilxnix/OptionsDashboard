import os
from datetime import datetime
import json

from scanner_core import run_scanner, summarize_results, convert_numpy_types
from db_client import fetch_tickers_from_db


def save_to_local(results, directory="output"):
    """Save the scan results as a JSON file locally."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"trade_plans_{date_str}.json"
    full_path = os.path.join(directory, filename)

    # Convert numpy/pandas types to JSON-serializable types
    converted_results = convert_numpy_types(results)

    with open(full_path, "w") as f:
        json.dump(converted_results, f, indent=2, default=str)

    return full_path


def save_individual_scan_result(symbol, result_data, directory="output"):
    """Save individual scan result immediately"""
    if not os.path.exists(directory):
        os.makedirs(directory)

    date_str = datetime.now().strftime("%Y-%m-%d")
    progressive_file = os.path.join(directory, f"progressive_scan_{date_str}.json")

    # Load existing data or create new
    if os.path.exists(progressive_file):
        with open(progressive_file, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    # Add the new result
    existing_data[symbol] = convert_numpy_types(result_data)

    # Save back to file
    with open(progressive_file, 'w') as f:
        json.dump(existing_data, f, indent=2, default=str)

    print(f"✅ Progressive save: {symbol} saved to {progressive_file}")
    return True


def run_autonomous_scan(min_delta=0.25,
                        max_delta=0.68,
                        min_price=0.01,
                        max_price=0.10,
                        time_to_expiry_range=(2, 16),
                        iv_percentile_threshold=85,
                        discovery_limit=50,  # still accepted but unused now
                        dry_run=False,
                        auto_refresh_symbols=True,
                        symbol_limit=25):
    """
    Autonomous scan pipeline that:
      1. Optionally refreshes symbols from Yahoo Finance screeners
      2. Fetches tickers from your Supabase/Postgres table
      3. Runs the options scanner over them
      4. Saves results locally (unless dry_run=True)
      5. Summarizes results and returns a digest
    """
    print(
        f"\n📡 Starting autonomous scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}..."
    )

    # ── AUTO-REFRESH SYMBOLS FROM ALPHA VANTAGE ──
    if auto_refresh_symbols:
        print("🔄 Auto-refreshing symbols from Alpha Vantage...")
        try:
            import requests
            import time
            from db_client import update_tickers_in_db

            # Fetch fresh symbols from Alpha Vantage
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            if not api_key:
                print("❌ ALPHA_VANTAGE_API_KEY not set, skipping symbol refresh")
            else:
                url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={api_key}'

                try:
                    print("   Fetching top gainers, losers, and most active...")
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        data = response.json()

                        if 'Error Message' not in data and 'Information' not in data:
                            all_fresh_symbols = []
                            categories = ['top_gainers', 'top_losers', 'most_actively_traded']

                            for category in categories:
                                if category in data:
                                    symbols = [item['ticker'] for item in data[category]]
                                    all_fresh_symbols.extend(symbols)
                                    print(f"   ✅ {len(symbols)} symbols from {category}")

                            # Update database with fresh symbols
                            if all_fresh_symbols:
                                unique_symbols = list(dict.fromkeys(all_fresh_symbols))
                                update_result = update_tickers_in_db(unique_symbols, mode="replace")
                                print(f"🔄 Database updated with {len(unique_symbols)} fresh symbols")
                            else:
                                print("⚠️ No fresh symbols fetched, using existing database")
                        else:
                            print(f"❌ Alpha Vantage API error: {data.get('Error Message', data.get('Information', 'Unknown error'))}")

                except Exception as e:
                    print(f"   ❌ Failed to fetch from Alpha Vantage: {e}")
                    print("📦 Falling back to existing database")

        except Exception as e:
            print(f"❌ Symbol refresh failed: {e}")
            print("📦 Falling back to existing database")

    # ── PULL TICKERS FROM DATABASE ──
    all_symbols = fetch_tickers_from_db()
    if not all_symbols:
        print("❌ No tickers found in database.")
        return {
            "digest": "No tickers found in database.",
            "results": None,
            "summary": {},
            "output_path": None,
            "symbols_processed": 0
        }

    # Filter out problematic symbols and prioritize optionable stocks
    filtered_symbols = []
    skip_patterns = ['W', 'WS', 'WT', '+', 'WARRANTS', 'UNITS']
    
    for symbol in all_symbols:
        # Skip obvious warrants/rights/units
        if any(pattern in symbol.upper() for pattern in skip_patterns):
            continue
        # Skip very short symbols (often problematic)
        if len(symbol) < 2:
            continue
        # Skip symbols with numbers (often warrants)
        if any(char.isdigit() for char in symbol):
            continue
        filtered_symbols.append(symbol)
    
    # Take more symbols since we're filtering heavily
    symbols = filtered_symbols[:min(symbol_limit * 2, len(filtered_symbols))]
    print(f"🔍 Processing {len(symbols)} filtered symbols from {len(all_symbols)} total: {symbols[:5]}...")

    # ── Run your existing scanner_core logic with progressive saving ──
    print("🔄 Running optimized scanner...")
    start_time = datetime.now()
    
    results = run_scanner(
        symbols=symbols,
        min_delta=min_delta,
        max_delta=max_delta,
        min_price=min_price,
        max_price=max_price,
        time_to_expiry_range=time_to_expiry_range,
        iv_percentile_threshold=iv_percentile_threshold
    )
    
    scan_duration = datetime.now() - start_time
    print(f"⏱️  Scan completed in {scan_duration.total_seconds():.1f} seconds")

    # Additional safety: save each result from the final results dict too
    if results:
        for symbol, result_data in results.items():
            save_individual_scan_result(symbol, result_data)

    if not results:
        print("⚠️ No valid results found in scanner.")
        return {
            "digest": "No valid trade plans were generated.",
            "results": None,
            "summary": {},
            "output_path": None
        }

    # ── Save JSON locally (unless dry_run) ──
    output_path = None
    if not dry_run:
        output_path = save_to_local(results)

    # ── Build summary & digest ──
    summary = summarize_results(results)

    top = max(
        results.items(),
        key=lambda x: x[1].get("confluence", {}).get("score", 0),
        default=(None, {})
    )
    top_symbol = top[0] if top[0] else "N/A"
    top_score = top[1].get("confluence", {}).get("score", "N/A")
    top_bias = top[1].get("confluence", {}).get("bias", "N/A")

    digest = f"""
🗓️ {datetime.now().strftime('%Y-%m-%d')}
✅ {len(symbols)} symbols discovered
📈 {len(results)} trade plans generated
🚀 Top Setup: {top_symbol} (Score: {top_score}, Bias: {top_bias})
💾 Output saved: {output_path if output_path else 'Dry run'}
"""

    print(digest.strip())

    return {
        "digest": digest.strip(),
        "results": results,
        "summary": summary,
        "output_path": output_path,
        "symbols_processed": len(symbols),
        "processing_time": scan_duration.total_seconds()
    }


if __name__ == "__main__":
    run_autonomous_scan()