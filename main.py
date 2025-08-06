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

        filters = {'min_price': min_price}
        results = explosive_scanner.run_explosive_scan(scan_type=scan_type, filters=filters)

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
        results = explosive_scanner.run_explosive_scan(scan_type='earnings', filters={'min_price': 0.10})

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

@app.route('/tracked-options')
def get_tracked_options():
    try:
        performance_data = performance_tracker.load_performance_data()

        # Format the data for easier reading
        formatted_options = []
        for track_id, data in performance_data.items():
            option_info = {
                "symbol": data["symbol"],
                "strike": data["option_details"]["strike"],
                "type": data["option_details"]["type"],
                "expiration": data["option_details"]["expiration"],
                "entry_price": data["option_details"]["entry_price"],
                "predicted_target": data["option_details"]["predicted_target"],
                "predicted_bias": data["option_details"]["predicted_bias"],
                "confluence_score": data["option_details"]["confluence_score"],
                "prediction_date": data["prediction_date"],
                "final_outcome": data["final_outcome"],
                "max_profit": data["max_profit"],
                "max_loss": data["max_loss"],
                "days_tracked": data["days_tracked"],
                "hit_target": data["hit_target"],
                "hit_stop": data["hit_stop"]
            }
            formatted_options.append(option_info)

        # Sort by prediction date (newest first)
        formatted_options.sort(key=lambda x: x["prediction_date"], reverse=True)

        return jsonify({
            "total_tracked": len(formatted_options),
            "options": formatted_options
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-performance')
def update_performance():
    try:
        print("🔄 Starting performance update for all tracked options...")
        updated_count = performance_tracker.update_daily_performance()
        return jsonify({
            "message": f"Updated {updated_count} options",
            "updated_count": updated_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tracking-summary')
def get_tracking_summary():
    try:
        summary = performance_tracker.get_tracking_summary()
        return jsonify({
            "active_options": len(summary['active_options']),
            "finalized_options": len(summary['finalized_options']),
            "invalid_options": len(summary['invalid_options']),
            "expired_options": len(summary['expired_options']),
            "details": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup-finalized')
def cleanup_finalized():
    try:
        removed_count = performance_tracker.cleanup_finalized_options(keep_days=30)
        return jsonify({
            "message": f"Removed {removed_count} old finalized options",
            "removed_count": removed_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup-invalid')
def cleanup_invalid():
    try:
        removed_count = performance_tracker.remove_invalid_options()
        return jsonify({
            "message": f"Removed {removed_count} options with invalid entry prices",
            "removed_count": removed_count
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