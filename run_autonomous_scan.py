import os
from datetime import datetime
import json

from scanner_core import run_scanner, summarize_results
from db_client import fetch_tickers_from_db


def save_to_local(results, directory="output"):
    """Save the scan results as a JSON file locally."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"trade_plans_{date_str}.json"
    full_path = os.path.join(directory, filename)

    with open(full_path, "w") as f:
        json.dump(results, f, indent=2)

    return full_path


def run_autonomous_scan(min_delta=0.25,
                        max_delta=0.68,
                        min_price=0.01,
                        max_price=0.10,
                        time_to_expiry_range=(2, 16),
                        iv_percentile_threshold=85,
                        discovery_limit=50,  # still accepted but unused now
                        dry_run=False):
    """
    Autonomous scan pipeline that:
      1. Fetches tickers from your Supabase/Postgres table
      2. Runs the options scanner over them
      3. Saves results locally (unless dry_run=True)
      4. Summarizes results and returns a digest
    """
    print(
        f"\n📡 Starting autonomous scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}..."
    )

    # ── NEW: pull tickers from DB instead of finviz discovery ──
    symbols = fetch_tickers_from_db()
    if not symbols:
        print("❌ No tickers found in database.")
        return {
            "digest": "No tickers found in database.",
            "results": None,
            "summary": {},
            "output_path": None
        }

    print(f"🔍 {len(symbols)} tickers found: {symbols[:5]}...")

    # ── Run your existing scanner_core logic ──
    results = run_scanner(
        symbols=symbols,
        min_delta=min_delta,
        max_delta=max_delta,
        min_price=min_price,
        max_price=max_price,
        time_to_expiry_range=time_to_expiry_range,
        iv_percentile_threshold=iv_percentile_threshold
    )

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
        "output_path": output_path
    }


if __name__ == "__main__":
    run_autonomous_scan()
