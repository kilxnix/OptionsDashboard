#!/usr/bin/env python3
"""
Test script to verify the updated scoring thresholds are working correctly
"""

import os
from datetime import datetime
from explosive_options_scanner import ExplosiveOptionsScanner

def test_scanner_thresholds():
    """Test the scanner with updated thresholds"""
    
    # Get API key from environment
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
    
    # Initialize scanner
    scanner = ExplosiveOptionsScanner(api_key)
    
    print("=" * 80)
    print(f"TESTING UPDATED SCANNER THRESHOLDS - {datetime.now()}")
    print("=" * 80)
    
    # Test symbols known to have options
    test_symbols = ['AAPL', 'SPY', 'TSLA', 'AMD', 'NVDA']
    
    print(f"\n📊 Testing with symbols: {', '.join(test_symbols)}")
    print(f"🎯 Min score threshold: {scanner.scan_config['min_score']}")
    print("\n🔍 Expected thresholds:")
    print("  - Score >= 50: STRONG BUY")
    print("  - Score >= 40: BUY")
    print("  - Score >= 30: CAUTIOUS BUY")
    print("  - Score >= 25: WATCH")
    print("  - Score >= 15: NEUTRAL")
    print("  - Score < 15: REJECT")
    
    # Run a quick scan
    try:
        results = scanner.run_explosive_scan(
            symbols=test_symbols[:3],  # Test with first 3 symbols
            scan_type='quick',
            filters={
                'min_volume': 50,  # Lower threshold for testing
                'min_oi': 50,
                'max_days_to_expiry': 45
            }
        )
        
        print("\n" + "=" * 80)
        print("SCAN RESULTS:")
        print("=" * 80)
        
        # Check if we got any opportunities
        if results.get('opportunities'):
            print(f"\n✅ Found {len(results['opportunities'])} symbols with opportunities")
            
            # Display results for each symbol
            for symbol, data in results['opportunities'].items():
                best = data.get('best_opportunity', {})
                if best:
                    score = best.get('total_score', 0)
                    rec = best.get('recommendation', 'N/A')
                    confidence = best.get('confidence', 0)
                    
                    print(f"\n📈 {symbol}:")
                    print(f"  Score: {score:.1f}")
                    print(f"  Recommendation: {rec}")
                    print(f"  Confidence: {confidence}%")
                    
                    # Check if recommendation matches expected threshold
                    if score >= 50:
                        expected = "STRONG BUY"
                    elif score >= 40:
                        expected = "BUY"
                    elif score >= 30:
                        expected = "CAUTIOUS BUY"
                    elif score >= 25:
                        expected = "WATCH"
                    elif score >= 15:
                        expected = "NEUTRAL"
                    else:
                        expected = "REJECT"
                    
                    if expected in rec:
                        print(f"  ✅ Threshold working correctly")
                    else:
                        print(f"  ⚠️ Expected '{expected}' based on score {score:.1f}")
        else:
            print("\n⚠️ No opportunities found. This might be due to:")
            print("  - Market conditions")
            print("  - API limits")
            print("  - No options meeting criteria")
            
        # Check top picks
        if results.get('top_picks'):
            print("\n" + "=" * 80)
            print(f"TOP {len(results['top_picks'])} PICKS:")
            print("=" * 80)
            
            for i, pick in enumerate(results['top_picks'][:3], 1):
                symbol = pick.get('symbol', 'N/A')
                score = pick.get('total_score', 0)
                rec = pick.get('recommendation', 'N/A')
                
                print(f"\n#{i}. {symbol}")
                print(f"  Score: {score:.1f}")
                print(f"  Recommendation: {rec}")
                
                # The top pick should typically be actionable
                if i == 1 and score >= 30:
                    if "BUY" in rec:
                        print("  ✅ Top pick is actionable!")
                    else:
                        print("  ⚠️ Top pick should be actionable with score >= 30")
        
        # Display summary
        if results.get('summary'):
            print("\n" + "=" * 80)
            print("SUMMARY:")
            print("=" * 80)
            print(results['summary'])
            
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scanner_thresholds()