
from flask import Flask, jsonify, request
import json
import os
from datetime import datetime
from scanner_core import ProgressiveOptionsScanner
from enhanced_scanner import EnhancedOptionsScanner
from explosive_options_scanner import ExplosiveOptionsScanner
from performance_tracker import PerformanceTracker
import traceback

app = Flask(__name__)

# Get API key
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Initialize scanners
progressive_scanner = ProgressiveOptionsScanner()
enhanced_scanner = EnhancedOptionsScanner(ALPHA_VANTAGE_API_KEY)
explosive_scanner = ExplosiveOptionsScanner(ALPHA_VANTAGE_API_KEY)
performance_tracker = PerformanceTracker()

@app.route('/')
def home():
    return jsonify({
        "message": "Options Scanner API",
        "endpoints": [
            "/progressive-scan",
            "/enhanced-scan", 
            "/explosive-scan",
            "/explosive-earnings-combo",
            "/performance"
        ]
    })

@app.route('/progressive-scan')
def progressive_scan():
    try:
        results = progressive_scanner.run_scan()
        
        # Save results
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"TradingPlans/progressive_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/enhanced-scan')
def enhanced_scan():
    try:
        results = enhanced_scanner.run_scan()
        
        # Save results
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"TradingPlans/enhanced_scan_progress_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/explosive-scan')
def explosive_scan():
    try:
        scan_type = request.args.get('scan_type', 'earnings')
        min_price = float(request.args.get('min_price', 0.10))
        
        results = explosive_scanner.run_scan(scan_type=scan_type, min_price=min_price)
        
        # Save results
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"TradingPlans/explosive_scan_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/explosive-earnings-combo')
def explosive_earnings_combo():
    try:
        print("🎯 Starting explosive earnings combo tracking...")
        
        # Run explosive scan with earnings focus
        results = explosive_scanner.run_scan(scan_type='earnings', min_price=0.10)
        
        # Track performance
        performance_tracker.track_options(results)
        
        print(f"✅ Explosive earnings combo tracking completed. Found {len(results)} opportunities.")
        
        # Save results
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"TradingPlans/explosive_scan_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        return jsonify(results)
    except Exception as e:
        print(f"❌ Error in explosive earnings combo: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/performance')
def get_performance():
    try:
        metrics = performance_tracker.calculate_performance_metrics()
        suggestions = performance_tracker.get_improvement_suggestions()
        return jsonify({
            "metrics": metrics,
            "suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure TradingPlans directory exists
    os.makedirs('TradingPlans', exist_ok=True)
    
    print("Mounting Google Drive...")
    print("Using existing directory: TradingPlans")
    print("Starting Flask app on 0.0.0.0:8080...")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
