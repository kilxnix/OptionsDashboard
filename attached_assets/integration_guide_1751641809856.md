# Integration Guide: Explosive Options Scanner

## Overview
This guide shows how to integrate the new Explosive Options Scanner components into your existing system.

## New Files to Add

1. **enhanced_options_grader.py** - Advanced scoring algorithm
2. **intelligent_trade_planner.py** - Data-driven trade plan generator
3. **adaptive_market_monitor.py** - Real-time position monitoring
4. **explosive_options_scanner.py** - Main integration module

## Updates to Existing Files

### 1. Update `scanner_core.py`

Add the following imports and integration:

```python
# Add to imports
from enhanced_options_grader import EnhancedOptionsGrader
from intelligent_trade_planner import IntelligentTradePlanner

# Replace the existing analyze_option function with:
def analyze_option_enhanced(option_data, symbol, market_data=None):
    """Enhanced option analysis using new grading system"""
    
    # Initialize grader
    grader = EnhancedOptionsGrader(ALPHA_VANTAGE_API_KEY)
    
    # Calculate comprehensive score
    score, analysis = grader.calculate_option_score(option_data, market_data)
    
    # Only proceed if score meets threshold
    if score < 60:  # Minimum score
        return None
    
    # Generate intelligent trade plan
    if score >= 60:
        planner = IntelligentTradePlanner(ALPHA_VANTAGE_API_KEY)
        trade_plan = planner.generate_intelligent_plan(
            option_data,
            analysis,
            market_data
        )
        
        return {
            'option_data': option_data,
            'score': score,
            'analysis': analysis,
            'trade_plan': trade_plan
        }
    
    return None
```

### 2. Update `enhanced_scanner.py`

Replace the `enhanced_option_scoring` method with:

```python
def enhanced_option_scoring(self, option_data, market_data, analysis_results):
    """Use new grading system for scoring"""
    from enhanced_options_grader import EnhancedOptionsGrader
    
    grader = EnhancedOptionsGrader(self.api_key)
    score, analysis = grader.calculate_option_score(
        option_data.to_dict() if hasattr(option_data, 'to_dict') else option_data,
        market_data
    )
    
    return score
```

### 3. Update `main.py`

Add new endpoints for the explosive scanner:

```python
@app.route("/explosive-scan", methods=["GET", "POST"])
def run_explosive_scan():
    """Run the new explosive options scanner"""
    try:
        from explosive_options_scanner import ExplosiveOptionsScanner
        
        # Get parameters
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            scan_type = data.get('scan_type', 'comprehensive')
            symbols = data.get('symbols', None)
            filters = data.get('filters', {})
        else:
            scan_type = request.args.get('scan_type', 'comprehensive')
            symbols = request.args.getlist('symbols') or None
            filters = {
                'min_price': float(request.args.get('min_price', 0.05)),
                'max_price': float(request.args.get('max_price', 5.00)),
                'min_delta': float(request.args.get('min_delta', 0.10)),
                'max_delta': float(request.args.get('max_delta', 0.40)),
                'min_days': int(request.args.get('min_days', 1)),
                'max_days': int(request.args.get('max_days', 30))
            }
        
        # Initialize scanner
        scanner = ExplosiveOptionsScanner(os.getenv('ALPHA_VANTAGE_API_KEY'))
        
        # Run scan
        results = scanner.run_explosive_scan(
            symbols=symbols,
            scan_type=scan_type,
            filters=filters
        )
        
        return jsonify({
            "status": "success",
            "scan_type": scan_type,
            "opportunities_found": len(results['opportunities']),
            "top_picks": results['top_picks'][:5],
            "summary": results['summary']
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Explosive scan failed: {str(e)}"
        }), 500


@app.route("/monitor-positions", methods=["GET"])
def monitor_positions():
    """Monitor active positions with adaptive system"""
    try:
        from explosive_options_scanner import ExplosiveOptionsScanner
        
        scanner = ExplosiveOptionsScanner(os.getenv('ALPHA_VANTAGE_API_KEY'))
        monitoring_results = scanner.monitor_active_positions()
        
        return jsonify({
            "status": "success",
            "positions_monitored": monitoring_results['positions_monitored'],
            "alerts": monitoring_results['alerts'],
            "exit_signals": monitoring_results['exit_signals'],
            "summary_actions": monitoring_results['summary_actions']
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Monitoring failed: {str(e)}"
        }), 500
```

### 4. Update `performance_tracker.py`

Add integration with the new scoring system:

```python
def track_enhanced_prediction(self, symbol, option_data, score_analysis, trade_plan):
    """Track predictions from enhanced scanner"""
    
    track_id = self.track_option_performance(symbol, option_data, trade_plan, 
                                           datetime.now().strftime('%Y-%m-%d'))
    
    # Store enhanced scoring data
    performance_data = self.load_performance_data()
    if track_id in performance_data:
        performance_data[track_id]['enhanced_scoring'] = {
            'total_score': score_analysis['total_score'],
            'confidence': score_analysis['confidence'],
            'components': score_analysis['components'],
            'unusual_activity': {
                'volume_spike': option_data.get('volume', 0) / max(option_data.get('open_interest', 1), 1),
                'oi_change': 0  # Would calculate from historical
            }
        }
    
    self.save_performance_data(performance_data)
    return track_id
```

## API Endpoints

### New Endpoints

1. **Explosive Scan**
   ```
   GET/POST /explosive-scan
   Parameters:
   - scan_type: 'comprehensive', 'quick', 'earnings', 'unusual_activity'
   - symbols: Optional list of symbols
   - filters: Price, delta, days filters
   ```

2. **Monitor Positions**
   ```
   GET /monitor-positions
   Returns real-time alerts and exit signals
   ```

3. **Market Regime**
   ```
   GET /market-regime
   Returns current market conditions and trading adjustments
   ```

## Usage Examples

### Running an Explosive Scan

```python
# Via API
curl -X POST http://localhost:8080/explosive-scan \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "earnings",
    "filters": {
      "min_price": 0.10,
      "max_price": 2.00,
      "min_delta": 0.15,
      "max_delta": 0.35
    }
  }'

# Via Python
from explosive_options_scanner import ExplosiveOptionsScanner

scanner = ExplosiveOptionsScanner(api_key)
results = scanner.run_explosive_scan(
    scan_type='unusual_activity',
    filters={'min_volume': 1000}
)
```

### Monitoring Active Positions

```python
# Set up continuous monitoring
import schedule

def monitor_loop():
    scanner = ExplosiveOptionsScanner(api_key)
    results = scanner.monitor_active_positions()
    
    # Check for critical alerts
    for signal in results['exit_signals']:
        if signal['urgency'] == 'CRITICAL':
            print(f"🚨 CRITICAL: {signal['action']}")
            # Send alert (email, SMS, etc.)

# Run every 15 minutes during market hours
schedule.every(15).minutes.do(monitor_loop)
```

## Configuration

### Environment Variables

Add to your `.env` file:
```
# Scanning Configuration
MIN_SCORE_THRESHOLD=60
MAX_CONCURRENT_POSITIONS=10
SCAN_FREQUENCY=continuous

# Risk Management
MAX_RISK_PER_TRADE=0.02
MIN_REWARD_RISK_RATIO=2.0

# Market Hours (Eastern Time)
MARKET_OPEN=09:30
MARKET_CLOSE=16:00
```

### Database Schema Updates

Add tables for enhanced tracking:

```sql
-- Enhanced predictions table
CREATE TABLE enhanced_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    option_type VARCHAR(4),
    strike DECIMAL(10,2),
    expiration DATE,
    entry_price DECIMAL(10,2),
    total_score DECIMAL(5,2),
    confidence INT,
    unusual_activity_score INT,
    prediction_time TIMESTAMP,
    trade_plan_json TEXT
);

-- Market regime history
CREATE TABLE market_regime (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    volatility_regime VARCHAR(20),
    trend VARCHAR(20),
    breadth VARCHAR(20),
    sentiment VARCHAR(20),
    adjustments_json TEXT
);
```

## Best Practices

1. **Scan Frequency**
   - Comprehensive scan: Once per day pre-market
   - Earnings scan: Daily for next 7 days
   - Unusual activity: Every 30 minutes
   - Quick scan: Every hour

2. **Position Management**
   - Never exceed 10 concurrent positions
   - Monitor every 15 minutes during market hours
   - Exit immediately on CRITICAL signals
   - Review all positions 30 minutes before close

3. **Risk Management**
   - Position size using Kelly Criterion
   - Maximum 2% risk per trade
   - Reduce size by 50% in high volatility
   - Always use stops (trailing after 10% profit)

4. **Performance Tracking**
   - Track every prediction
   - Review weekly performance
   - Adapt thresholds monthly
   - Focus on best-performing setups

## Troubleshooting

### Common Issues

1. **Alpha Vantage Rate Limits**
   - Solution: Implement caching for technical indicators
   - Use batch requests where possible

2. **Slow Scans**
   - Solution: Use parallel processing
   - Limit to 3 expirations per symbol
   - Cache market data for 5 minutes

3. **False Signals**
   - Solution: Require multiple confirmations
   - Increase minimum score threshold
   - Add time-of-day filters

## Next Steps

1. **Backtest the System**
   - Use historical data to validate scoring
   - Optimize thresholds
   - Calculate expected returns

2. **Add Notifications**
   - Email alerts for high-score opportunities
   - SMS for critical exit signals
   - Discord/Slack integration

3. **Enhance with ML**
   - Train on your performance data
   - Improve pattern recognition
   - Dynamic threshold adjustment

4. **Add More Data Sources**
   - Options flow data
   - Dark pool activity
   - Social sentiment
   - Insider trading

## Support

For issues or questions:
1. Check the logs in `./TradingPlans/logs/`
2. Review the performance metrics
3. Adjust thresholds based on results

The system will continuously improve as it learns from your trading performance!
