
#!/usr/bin/env python3
"""
Standalone script to run comprehensive backtesting on all historical trades
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import AdvancedBacktester

def main():
    print("🚀 Advanced Options Scanner Backtesting Engine")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize backtester
        backtester = AdvancedBacktester()
        
        # Load all historical trades
        print("\n📂 Loading historical trades...")
        trades = backtester.load_all_historical_trades()
        
        if not trades:
            print("❌ No trades found in ./TradingPlans/")
            print("Make sure you have progressive_results_*.json files")
            return
        
        print(f"✅ Loaded {len(trades)} historical trades")
        
        # Also try to load human readable file if it exists
        human_file = "./TradingPlans/human_readable_plans.txt"
        if os.path.exists(human_file):
            print("\n📄 Loading human readable trades file...")
            human_trades = backtester.parse_human_readable_file(human_file)
            if human_trades:
                backtester.trades.extend(human_trades)
                print(f"✅ Added {len(human_trades)} trades from human readable file")
        
        total_trades = len(backtester.trades)
        print(f"\n🎯 Total trades to backtest: {total_trades}")
        
        # Run backtest
        print("\n⚡ Running backtest simulation...")
        backtester.backtest_all_trades()
        
        # Analyze results
        print("\n📊 Analyzing results...")
        results_df = backtester.analyze_results()
        
        print("\n" + "="*60)
        print("✅ Backtesting Complete!")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNext Steps:")
        print("1. Review the generated CSV and JSON files")
        print("2. Use the recommendations to optimize your scanner")
        print("3. Run /backtest/optimize-thresholds API endpoint for specific tuning")
        print("="*60)
        
        return backtester, results_df
        
    except KeyboardInterrupt:
        print("\n⚠️ Backtesting interrupted by user")
        return None, None
    except Exception as e:
        print(f"\n❌ Error during backtesting: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    backtester, results = main()
