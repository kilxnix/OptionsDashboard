from flask import Flask, jsonify, request
from datetime import datetime
import os
import json
import glob
import pandas as pd
import requests
import time
from run_autonomous_scan import run_autonomous_scan

app = Flask(__name__)

# Alpha Vantage API integration - no rate limiting needed with subscription


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


@app.route("/scan/parameters", methods=["GET"])
def get_scan_parameters():
    """Get available scan parameters and their default values"""
    return jsonify({
        "status": "success",
        "parameters": {
            "auto_refresh": {
                "type": "boolean",
                "default": True,
                "description": "Auto-refresh symbols from Alpha Vantage before scanning"
            },
            "limit": {
                "type": "integer", 
                "default": 25,
                "description": "Maximum number of symbols to process"
            },
            "min_delta": {
                "type": "float",
                "default": 0.25,
                "description": "Minimum option delta (0.0 to 1.0)"
            },
            "max_delta": {
                "type": "float", 
                "default": 0.68,
                "description": "Maximum option delta (0.0 to 1.0)"
            },
            "min_price": {
                "type": "float",
                "default": 0.01,
                "description": "Minimum option price in dollars"
            },
            "max_price": {
                "type": "float",
                "default": 0.10, 
                "description": "Maximum option price in dollars"
            },
            "min_days": {
                "type": "integer",
                "default": 2,
                "description": "Minimum days to expiration"
            },
            "max_days": {
                "type": "integer",
                "default": 16,
                "description": "Maximum days to expiration"
            },
            "iv_percentile": {
                "type": "integer",
                "default": 85,
                "description": "Minimum IV percentile threshold (0-100)"
            }
        },
        "example_usage": "/scan?min_delta=0.3&max_delta=0.7&min_price=0.05&max_price=0.20&min_days=1&max_days=30&iv_percentile=90"
    })


@app.route("/scan", methods=["GET", "POST"])
def trigger_scan():
    # Handle both GET (query params) and POST (JSON body) requests
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        auto_refresh = data.get('auto_refresh', True)
        limit = int(data.get('limit', 0))  # 0 = unlimited
        min_delta = float(data.get('min_delta', 0.25))
        max_delta = float(data.get('max_delta', 0.68))
        min_price = float(data.get('min_price', 0.01))
        max_price = float(data.get('max_price', 0.10))
        min_days = int(data.get('min_days', 2))
        max_days = int(data.get('max_days', 16))
        iv_percentile = int(data.get('iv_percentile', 85))
    else:
        # GET request - use query parameters
        auto_refresh = request.args.get('auto_refresh', 'true').lower() == 'true'
        limit = int(request.args.get('limit', 0))  # 0 = unlimited
        min_delta = float(request.args.get('min_delta', 0.25))
        max_delta = float(request.args.get('max_delta', 0.68))
        min_price = float(request.args.get('min_price', 0.01))
        max_price = float(request.args.get('max_price', 0.10))
        min_days = int(request.args.get('min_days', 2))
        max_days = int(request.args.get('max_days', 16))
        iv_percentile = request.args.get('iv_percentile')
        iv_percentile = int(iv_percentile) if iv_percentile else 85
    
    result = run_autonomous_scan(
        dry_run=False, 
        auto_refresh_symbols=auto_refresh,
        symbol_limit=limit,
        min_delta=min_delta,
        max_delta=max_delta,
        min_price=min_price,
        max_price=max_price,
        time_to_expiry_range=(min_days, max_days),
        iv_percentile_threshold=iv_percentile
    )

    if not result or not result.get("results"):
        return jsonify({
            "status": "no-results",
            "message": "Scanner ran but found no valid trade plans.",
            "digest": result["digest"] if result else "No output",
            "symbols_processed": result.get("symbols_processed", 0) if result else 0
        }), 200

    # Get summary stats
    results = result.get("results", {})
    top_scores = sorted([(k, v.get("confluence", {}).get("score", 0)) 
                        for k, v in results.items()], 
                       key=lambda x: x[1], reverse=True)
    
    return jsonify({
        "status": "completed",
        "digest": result["digest"],
        "symbols_processed": result.get("symbols_processed", 0),
        "opportunities_found": len(results),
        "top_3_symbols": [f"{sym} ({score:.1f})" for sym, score in top_scores[:3]],
        "scan_parameters": {
            "min_delta": min_delta,
            "max_delta": max_delta,
            "min_price": min_price,
            "max_price": max_price,
            "days_to_expiry": f"{min_days}-{max_days}",
            "iv_percentile_threshold": iv_percentile,
            "auto_refresh": auto_refresh,
            "symbol_limit": limit
        }
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


def fetch_alphavantage_top_symbols():
    """Fetch top gainers, losers, and most active symbols from Alpha Vantage"""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise Exception("ALPHA_VANTAGE_API_KEY environment variable not set")
    
    url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={api_key}'
    
    try:
        print("Fetching top gainers, losers, and most active from Alpha Vantage...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data:
            raise Exception(f"Alpha Vantage error: {data['Error Message']}")
        
        if 'Information' in data:
            raise Exception(f"Alpha Vantage info: {data['Information']}")
        
        all_symbols = []
        categories = ['top_gainers', 'top_losers', 'most_actively_traded']
        
        for category in categories:
            if category in data:
                category_symbols = [item['ticker'] for item in data[category]]
                all_symbols.extend(category_symbols)
                print(f"Fetched {len(category_symbols)} symbols from {category}")
        
        # Add common optionable stocks as backup
        backup_symbols = [
            'SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
            'NVDA', 'META', 'AMD', 'INTC', 'NFLX', 'CRM', 'UBER', 'LYFT',
            'BABA', 'DIS', 'BA', 'GE', 'F', 'GM', 'T', 'VZ', 'JPM', 'BAC',
            'WFC', 'C', 'GS', 'MS', 'XOM', 'CVX', 'KO', 'PEP', 'WMT', 'TGT'
        ]
        
        # Add backup symbols if we have fewer than 40 unique symbols
        if len(all_symbols) < 40:
            for symbol in backup_symbols:
                if symbol not in all_symbols:
                    all_symbols.append(symbol)
                    if len(all_symbols) >= 60:  # Cap at reasonable number
                        break
        
        # Remove duplicates while preserving order
        unique_symbols = list(dict.fromkeys(all_symbols))
        print(f"Total unique symbols (including backup): {len(unique_symbols)}")
        
        return {
            'all_symbols': unique_symbols,
            'top_gainers': [item['ticker'] for item in data.get('top_gainers', [])],
            'top_losers': [item['ticker'] for item in data.get('top_losers', [])],
            'most_active': [item['ticker'] for item in data.get('most_actively_traded', [])]
        }
        
    except Exception as e:
        print(f"Error fetching Alpha Vantage data: {e}")
        # Return backup symbols as fallback
        backup_symbols = [
            'SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
            'NVDA', 'META', 'AMD', 'INTC', 'NFLX', 'UBER', 'DIS', 'F'
        ]
        return {'all_symbols': backup_symbols, 'top_gainers': [], 'top_losers': [], 'most_active': []}


@app.route("/screener/symbols", methods=["GET"])
def get_screener_symbols():
    """Get symbols from Alpha Vantage screeners"""
    try:
        # Get category type from query params
        category = request.args.get('category', 'all')
        valid_categories = ['all', 'top_gainers', 'top_losers', 'most_active']
        
        if category not in valid_categories:
            return jsonify({
                "status": "error",
                "message": f"Invalid category. Valid options: {valid_categories}"
            }), 400
        
        data = fetch_alphavantage_top_symbols()
        
        if category == 'all':
            symbols = data['all_symbols']
        elif category == 'top_gainers':
            symbols = data['top_gainers']
        elif category == 'top_losers':
            symbols = data['top_losers']
        elif category == 'most_active':
            symbols = data['most_active']
        
        return jsonify({
            "status": "success",
            "category": category,
            "total_symbols": len(symbols),
            "symbols": symbols
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error fetching symbols: {str(e)}"
        }), 500


@app.route("/screener/all", methods=["GET"])
def get_all_screener_symbols():
    """Get symbols from Alpha Vantage top gainers, losers, and most active"""
    try:
        data = fetch_alphavantage_top_symbols()
        
        response_data = {
            "status": "success",
            "source": "alpha_vantage",
            "categories": {
                "top_gainers": data['top_gainers'],
                "top_losers": data['top_losers'],
                "most_active": data['most_active']
            },
            "combined_unique_symbols": data['all_symbols'],
            "total_unique": len(data['all_symbols']),
            "breakdown": {
                "top_gainers": len(data['top_gainers']),
                "top_losers": len(data['top_losers']),
                "most_active": len(data['most_active'])
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error fetching all symbols: {str(e)}"
        }), 500


@app.route("/screener/fallback", methods=["GET"])
def get_fallback_symbols():
    """Get symbols from database when Yahoo Finance is rate limited"""
    try:
        from db_client import fetch_tickers_from_db
        
        db_symbols = fetch_tickers_from_db()
        
        return jsonify({
            "status": "success",
            "source": "database",
            "total_symbols": len(db_symbols),
            "symbols": db_symbols,
            "message": "Using database symbols as fallback"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error fetching fallback symbols: {str(e)}"
        }), 500


@app.route("/screener/update-db", methods=["POST", "GET"])
def update_database_symbols():
    """Update database with fresh symbols from Yahoo Finance screeners"""
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            # For GET requests, use query parameters
            mode = request.args.get('mode', 'replace')
            custom_symbols_str = request.args.get('symbols', '')
            custom_symbols = custom_symbols_str.split(',') if custom_symbols_str else []
        else:
            # For POST requests, use JSON body
            data = request.get_json() if request.is_json else {}
            mode = data.get('mode', 'replace')  # Default to replace
            custom_symbols = data.get('symbols', [])  # Allow custom symbol list
        
        if custom_symbols:
            # Use provided symbols
            symbols_to_add = custom_symbols
            source = "custom"
        else:
            # Fetch from Alpha Vantage
            data = fetch_alphavantage_top_symbols()
            symbols_to_add = data['all_symbols']
            source = "alpha_vantage"
        
        if not symbols_to_add:
            return jsonify({
                "status": "error",
                "message": "No symbols to add to database"
            }), 400
        
        # Update database
        from db_client import update_tickers_in_db
        result = update_tickers_in_db(symbols_to_add, mode=mode)
        
        return jsonify({
            "status": "success",
            "source": source,
            "mode": mode,
            "symbols_added": len(symbols_to_add),
            "total_in_database": result["total_in_db"],
            "message": f"Database updated successfully with {len(symbols_to_add)} symbols"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Error updating database: {str(e)}"
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
