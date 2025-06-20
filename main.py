from flask import Flask, jsonify, request
from datetime import datetime
import os
import json
import glob
from run_autonomous_scan import run_autonomous_scan

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Autonomous scanner is running.",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health")
def health():
    return "OK", 200


@app.route("/scan", methods=["GET"])
def trigger_scan():
    result = run_autonomous_scan(dry_run=False)

    if not result or not result.get("results"):
        return jsonify({
            "status": "no-results",
            "message": "Scanner ran but found no valid trade plans.",
            "digest": result["digest"] if result else "No output"
        }), 200

    return jsonify({
        "status":
        "completed",
        "digest":
        result["digest"],
        "top_result":
        result.get("summary", {}).get("top_symbol", "N/A")
    }), 200


@app.route("/plans", methods=["GET"])
def get_sorted_plans():
    """Return sorted trading plans from the most recent scan"""
    try:
        # Get query parameters for sorting
        sort_by = request.args.get('sort_by', 'confluence_score')  # Default sort by confluence score
        order = request.args.get('order', 'desc')  # Default descending order
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))  # Default to today
        
        # Find the most recent progressive results file
        base_dir = './TradingPlans'
        json_pattern = f'progressive_results_{date}.json'
        json_file = os.path.join(base_dir, json_pattern)
        
        if not os.path.exists(json_file):
            # Try to find the most recent file if today's doesn't exist
            pattern = os.path.join(base_dir, 'progressive_results_*.json')
            files = glob.glob(pattern)
            if not files:
                return jsonify({
                    "status": "error",
                    "message": "No trading plans found"
                }), 404
            json_file = max(files, key=os.path.getctime)
        
        # Load the JSON data
        with open(json_file, 'r') as f:
            results = json.load(f)
        
        # Convert to sortable format
        plans = []
        for symbol, data in results.items():
            plan_data = {
                'symbol': symbol,
                'confluence_score': data.get('confluence', {}).get('score', 0),
                'bias': data.get('confluence', {}).get('bias', 'N/A'),
                'entry_price': 0,
                'target_price': 0,
                'option_type': 'N/A',
                'strike': 'N/A',
                'expiration': 'N/A',
                'position_size': 0,
                'max_hold_time': 'N/A'
            }
            
            # Extract trade plan details if available
            if 'trade_plan' in data and data['trade_plan']:
                tp = data['trade_plan']
                plan_data.update({
                    'entry_price': tp.get('entry_price', 0),
                    'target_price': tp.get('initial_target', 0),
                    'option_type': tp.get('type', 'N/A'),
                    'strike': tp.get('strike', 'N/A'),
                    'expiration': tp.get('expiration', 'N/A'),
                    'position_size': tp.get('position_size', 0),
                    'max_hold_time': tp.get('max_hold_time', 'N/A')
                })
            
            plans.append(plan_data)
        
        # Sort the plans
        reverse_order = order.lower() == 'desc'
        
        if sort_by == 'confluence_score':
            plans.sort(key=lambda x: x['confluence_score'], reverse=reverse_order)
        elif sort_by == 'entry_price':
            plans.sort(key=lambda x: x['entry_price'], reverse=reverse_order)
        elif sort_by == 'target_price':
            plans.sort(key=lambda x: x['target_price'], reverse=reverse_order)
        elif sort_by == 'symbol':
            plans.sort(key=lambda x: x['symbol'], reverse=reverse_order)
        else:
            plans.sort(key=lambda x: x['confluence_score'], reverse=True)  # Default fallback
        
        return jsonify({
            "status": "success",
            "total_plans": len(plans),
            "sort_by": sort_by,
            "order": order,
            "date": date,
            "plans": plans
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving plans: {str(e)}"
        }), 500


@app.route("/plans/all", methods=["GET"])
def get_all_plans():
    """Return all trading plans from ALL progressive results files"""
    try:
        # Get query parameters for sorting
        sort_by = request.args.get('sort_by', 'confluence_score')
        order = request.args.get('order', 'desc')
        limit = request.args.get('limit', type=int)  # Optional limit
        
        base_dir = './TradingPlans'
        pattern = os.path.join(base_dir, 'progressive_results_*.json')
        files = glob.glob(pattern)
        
        if not files:
            return jsonify({
                "status": "error",
                "message": "No trading plans found"
            }), 404
        
        # Load and merge all files
        all_plans = []
        files_processed = []
        
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    results = json.load(f)
                
                # Extract date from filename for tracking
                filename = os.path.basename(file_path)
                date_part = filename.replace('progressive_results_', '').replace('.json', '')
                files_processed.append(date_part)
                
                # Convert each symbol's data to plan format
                for symbol, data in results.items():
                    plan_data = {
                        'symbol': symbol,
                        'scan_date': date_part,
                        'confluence_score': data.get('confluence', {}).get('score', 0),
                        'bias': data.get('confluence', {}).get('bias', 'N/A'),
                        'entry_price': 0,
                        'target_price': 0,
                        'option_type': 'N/A',
                        'strike': 'N/A',
                        'expiration': 'N/A',
                        'expiration_date': None,  # For proper date sorting
                        'position_size': 0,
                        'max_hold_time': 'N/A'
                    }
                    
                    # Extract trade plan details if available
                    if 'trade_plan' in data and data['trade_plan']:
                        tp = data['trade_plan']
                        expiration_str = tp.get('expiration', 'N/A')
                        plan_data.update({
                            'entry_price': tp.get('entry_price', 0),
                            'target_price': tp.get('initial_target', 0),
                            'option_type': tp.get('type', 'N/A'),
                            'strike': tp.get('strike', 'N/A'),
                            'expiration': expiration_str,
                            'position_size': tp.get('position_size', 0),
                            'max_hold_time': tp.get('max_hold_time', 'N/A')
                        })
                        
                        # Convert expiration to datetime for sorting
                        try:
                            if expiration_str != 'N/A':
                                plan_data['expiration_date'] = pd.to_datetime(expiration_str)
                        except:
                            plan_data['expiration_date'] = None
                    
                    all_plans.append(plan_data)
                    
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        if not all_plans:
            return jsonify({
                "status": "error",
                "message": "No valid plans found in any files"
            }), 404
        
        # Sort the plans
        reverse_order = order.lower() == 'desc'
        
        if sort_by == 'confluence_score':
            all_plans.sort(key=lambda x: x['confluence_score'], reverse=reverse_order)
        elif sort_by == 'entry_price':
            all_plans.sort(key=lambda x: x['entry_price'], reverse=reverse_order)
        elif sort_by == 'target_price':
            all_plans.sort(key=lambda x: x['target_price'], reverse=reverse_order)
        elif sort_by == 'symbol':
            all_plans.sort(key=lambda x: x['symbol'], reverse=reverse_order)
        elif sort_by == 'scan_date':
            all_plans.sort(key=lambda x: x['scan_date'], reverse=reverse_order)
        elif sort_by == 'expiration' or sort_by == 'expiration_date':
            # Sort by expiration date, putting None values at the end
            all_plans.sort(key=lambda x: x['expiration_date'] if x['expiration_date'] is not None else pd.Timestamp.max, reverse=reverse_order)
        else:
            all_plans.sort(key=lambda x: x['confluence_score'], reverse=True)
        
        # Apply limit if specified
        if limit and limit > 0:
            all_plans = all_plans[:limit]
        
        return jsonify({
            "status": "success",
            "total_plans": len(all_plans),
            "files_processed": files_processed,
            "sort_by": sort_by,
            "order": order,
            "plans": all_plans
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving all plans: {str(e)}"
        }), 500


@app.route("/plans/formatted", methods=["GET"])
def get_formatted_plans():
    """Return human-readable formatted trading plans"""
    try:
        # Get query parameters
        sort_by = request.args.get('sort_by', 'confluence_score')
        order = request.args.get('order', 'desc')
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        limit = int(request.args.get('limit', 10))  # Limit number of results
        
        # Get the sorted plans data
        base_dir = './TradingPlans'
        json_pattern = f'progressive_results_{date}.json'
        json_file = os.path.join(base_dir, json_pattern)
        
        if not os.path.exists(json_file):
            pattern = os.path.join(base_dir, 'progressive_results_*.json')
            files = glob.glob(pattern)
            if not files:
                return "No trading plans found", 404
            json_file = max(files, key=os.path.getctime)
        
        with open(json_file, 'r') as f:
            results = json.load(f)
        
        # Sort and format the results
        sorted_symbols = []
        for symbol, data in results.items():
            confluence_score = data.get('confluence', {}).get('score', 0)
            sorted_symbols.append((symbol, confluence_score, data))
        
        reverse_order = order.lower() == 'desc'
        if sort_by == 'confluence_score':
            sorted_symbols.sort(key=lambda x: x[1], reverse=reverse_order)
        else:
            sorted_symbols.sort(key=lambda x: x[0], reverse=reverse_order)
        
        # Limit results
        sorted_symbols = sorted_symbols[:limit]
        
        # Format as human-readable text
        formatted_output = f"Trading Plans - Sorted by {sort_by} ({order})\n"
        formatted_output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        formatted_output += f"Total Plans: {len(sorted_symbols)}\n"
        formatted_output += "=" * 80 + "\n\n"
        
        for i, (symbol, score, data) in enumerate(sorted_symbols, 1):
            formatted_output += f"{i}. {symbol} - Confluence Score: {score:.1f}/10\n"
            formatted_output += f"   Bias: {data.get('confluence', {}).get('bias', 'N/A')}\n"
            
            if 'trade_plan' in data and data['trade_plan']:
                tp = data['trade_plan']
                formatted_output += f"   Entry: ${tp.get('entry_price', 0):.2f}\n"
                formatted_output += f"   Target: ${tp.get('initial_target', 0):.2f}\n"
                formatted_output += f"   Strike: {tp.get('strike', 'N/A')} {tp.get('type', 'N/A').capitalize()}\n"
                formatted_output += f"   Expiration: {tp.get('expiration', 'N/A')}\n"
                formatted_output += f"   Position Size: {tp.get('position_size', 0)} contracts\n"
                formatted_output += f"   Max Hold: {tp.get('max_hold_time', 'N/A')}\n"
            
            formatted_output += "\n" + "-" * 60 + "\n\n"
        
        return formatted_output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        return f"Error retrieving formatted plans: {str(e)}", 500


if __name__ == "__main__":
    print("Starting Flask app on 0.0.0.0:8080...")
    try:
        app.run(host="0.0.0.0", port=8080, debug=True)
    except Exception as e:
        print(f"Error starting Flask app: {e}")
        raise
