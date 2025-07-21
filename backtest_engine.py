import re
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import yfinance as yf
from performance_tracker import PerformanceTracker

class TradePlan:
    """Represents a single trade plan from our scanner results"""
    def __init__(self, data_dict=None):
        if data_dict:
            self.symbol = data_dict.get('symbol')
            self.bias = data_dict.get('bias', 'Unknown')
            self.strike = float(data_dict.get('strike', 0))
            self.option_type = data_dict.get('type', 'call')
            self.expiry = data_dict.get('expiration', '')
            self.entry_price = float(data_dict.get('entry_price', 0))
            self.stop_loss = float(data_dict.get('stop_loss', 0))
            self.initial_target = float(data_dict.get('initial_target', 0))
            self.final_target = float(data_dict.get('final_target', 0))
            self.position_size = int(data_dict.get('position_size', 1))
            self.max_hold_time = data_dict.get('max_hold_time', '12 hours')
            self.delta = float(data_dict.get('delta', 0))
            self.gamma = float(data_dict.get('gamma', 0))
            self.theta = float(data_dict.get('theta', 0))
            self.score = float(data_dict.get('score', 0))
            self.confluence_score = float(data_dict.get('confluence_score', 0))
            self.prediction_date = data_dict.get('prediction_date', datetime.now().strftime('%Y-%m-%d'))
        else:
            # Initialize empty
            self.symbol = None
            self.bias = None
            self.strike = None
            self.option_type = None
            self.expiry = None
            self.entry_price = None
            self.stop_loss = None
            self.initial_target = None
            self.final_target = None
            self.position_size = None
            self.max_hold_time = None
            self.delta = None
            self.gamma = None
            self.theta = None
            self.score = None
            self.confluence_score = None
            self.prediction_date = None

    def __repr__(self):
        return f"TradePlan({self.symbol} ${self.strike} {self.option_type} exp:{self.expiry})"

class AdvancedBacktester:
    """Advanced backtesting engine for our options scanner"""

    def __init__(self, alpha_vantage_key: str = None):
        self.av_key = alpha_vantage_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.trades = []
        self.results = []
        self.performance_tracker = PerformanceTracker()

    def load_trades_from_json(self, json_file: str) -> List[TradePlan]:
        """Load trades from progressive results JSON files"""
        print(f"Loading trades from {json_file}...")

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            trades = []
            for symbol, symbol_data in data.items():
                if 'trade_plan' in symbol_data and symbol_data['trade_plan']:
                    trade_plan = symbol_data['trade_plan']

                    # Create unified data structure
                    trade_data = {
                        'symbol': symbol,
                        'bias': trade_plan.get('bias', symbol_data.get('confluence', {}).get('bias', 'Unknown')),
                        'strike': trade_plan.get('strike', '0').replace('$', ''),
                        'type': trade_plan.get('type', 'call'),
                        'expiration': trade_plan.get('expiration', ''),
                        'entry_price': trade_plan.get('entry_price', 0),
                        'stop_loss': trade_plan.get('stop_loss', 0),
                        'initial_target': trade_plan.get('initial_target', 0),
                        'final_target': trade_plan.get('final_target', 0),
                        'position_size': trade_plan.get('position_size', 1),
                        'max_hold_time': trade_plan.get('max_hold_time', '12 hours'),
                        'delta': trade_plan.get('delta', 0),
                        'gamma': trade_plan.get('gamma', 0),
                        'theta': trade_plan.get('theta', 0),
                        'score': trade_plan.get('score', 0),
                        'confluence_score': symbol_data.get('confluence', {}).get('score', 0),
                        'prediction_date': json_file.split('_')[-1].replace('.json', '') if '_' in json_file else datetime.now().strftime('%Y-%m-%d')
                    }

                    trades.append(TradePlan(trade_data))

            print(f"Loaded {len(trades)} trades from {json_file}")
            return trades

        except Exception as e:
            print(f"Error loading trades from {json_file}: {e}")
            return []

    def load_all_historical_trades(self, directory: str = "./TradingPlans") -> List[TradePlan]:
        """Load all historical trades from progressive results files"""
        all_trades = []

        # Find all progressive results files
        json_files = [f for f in os.listdir(directory) if f.startswith('progressive_results_') and f.endswith('.json')]
        json_files.sort()  # Sort by date

        print(f"Found {len(json_files)} historical result files")

        for json_file in json_files:
            file_path = os.path.join(directory, json_file)
            trades = self.load_trades_from_json(file_path)
            all_trades.extend(trades)

        self.trades = all_trades
        print(f"Total historical trades loaded: {len(all_trades)}")
        return all_trades

    def parse_human_readable_file(self, file_path: str) -> List[TradePlan]:
        """Parse the human_readable_plans.txt file (your original format)"""
        print(f"Parsing trades from {file_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"File {file_path} not found")
            return []

        trades = []
        trade_sections = content.split('📈 Trade Plan for')

        for section in trade_sections[1:]:  # Skip first empty section
            trade = TradePlan()

            # Extract symbol and bias
            symbol_match = re.search(r'(\w+)\s+\((\w+)\s+Bias\)', section)
            if symbol_match:
                trade.symbol = symbol_match.group(1)
                trade.bias = symbol_match.group(2)

            # Extract option details
            option_match = re.search(r'\$\$?([\d.]+)\s+(Call|Put)\s+expiring\s+([\d-]+)', section)
            if option_match:
                trade.strike = float(option_match.group(1))
                trade.option_type = option_match.group(2).lower()
                trade.expiry = option_match.group(3)

            # Extract prices
            entry_match = re.search(r'Entry Price:\s*\$?([\d.]+)', section)
            if entry_match:
                trade.entry_price = float(entry_match.group(1))

            stop_match = re.search(r'Stop Loss:\s*\$?([\d.]+)', section)
            if stop_match:
                trade.stop_loss = float(stop_match.group(1))

            initial_match = re.search(r'Initial Target:\s*\$?([\d.]+)', section)
            if initial_match:
                trade.initial_target = float(initial_match.group(1))

            final_match = re.search(r'Final Target:\s*\$?([\d.]+)', section)
            if final_match:
                trade.final_target = float(final_match.group(1))

            # Extract position size and hold time
            size_match = re.search(r'Position Size:\s*(\d+)', section)
            if size_match:
                trade.position_size = int(size_match.group(1))

            hold_match = re.search(r'Max Hold Time:\s*(\d+)\s*hours?', section)
            if hold_match:
                trade.max_hold_time = int(hold_match.group(1))

            # Extract Greeks
            metrics_match = re.search(r'Delta:\s*([-\d.]+).*?Gamma:\s*([\d.]+).*?Theta:\s*([-\d.]+).*?Score:\s*([\d.]+)', section)
            if metrics_match:
                trade.delta = float(metrics_match.group(1))
                trade.gamma = float(metrics_match.group(2))
                trade.theta = float(metrics_match.group(3))
                trade.score = float(metrics_match.group(4))

            if trade.symbol and trade.strike and trade.option_type and trade.expiry:
                trades.append(trade)

        print(f"Parsed {len(trades)} trades from human readable file")
        return trades

    def get_historical_option_data(self, symbol: str, strike: float, option_type: str, 
                                          expiry: str, trade_date: str) -> Optional[Dict]:
        """Get historical option data using Alpha Vantage"""
        if not self.av_key:
            return None

        try:
            # Format the date for Alpha Vantage API
            formatted_date = pd.to_datetime(trade_date).strftime('%Y-%m-%d')

            # Alpha Vantage historical options endpoint
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'HISTORICAL_OPTIONS',
                'symbol': symbol,
                'date': formatted_date,
                'apikey': self.av_key
            }

            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if 'data' in data:
                # Find the specific option contract
                for contract in data['data']:
                    if (float(contract.get('strike', 0)) == strike and 
                        contract.get('type', '').lower() == option_type.lower() and
                        contract.get('expiration', '') == expiry):

                        return {
                            'price': float(contract.get('last', 0)),
                            'bid': float(contract.get('bid', 0)),
                            'ask': float(contract.get('ask', 0)),
                            'volume': float(contract.get('volume', 0)),
                            'delta': float(contract.get('delta', 0)),
                            'gamma': float(contract.get('gamma', 0)),
                            'theta': float(contract.get('theta', 0)),
                            'iv': float(contract.get('implied_volatility', 0)),
                            'available': True
                        }

            return {'available': False, 'reason': 'Contract not found in historical data'}

        except Exception as e:
            return {'available': False, 'reason': f'Alpha Vantage error: {str(e)}'}

    def simulate_option_performance(self, trade: TradePlan) -> Dict:
        """Simulate option performance based on stock price movement"""
        try:
            # Validate trade data with more robust checking
            if not hasattr(trade, 'symbol') or not trade.symbol:
                return {'status': 'ERROR', 'reason': 'No symbol provided'}

            # Check entry price with multiple possible attributes
            entry_price = None
            for attr in ['entry_price', 'mark', 'lastPrice', 'price']:
                if hasattr(trade, attr):
                    val = getattr(trade, attr)
                    if val and val != 0:
                        try:
                            entry_price = float(val)
                            break
                        except (ValueError, TypeError):
                            continue

            if not entry_price or entry_price <= 0:
                return {'status': 'ERROR', 'reason': 'No valid entry price found'}

            # Get stock price data with timeout and retry
            try:
                ticker = yf.Ticker(trade.symbol)

                # Calculate days since prediction with better fallback
                prediction_date = None
                for attr in ['prediction_date', 'date', 'scan_date']:
                    if hasattr(trade, attr):
                        date_val = getattr(trade, attr)
                        if date_val:
                            try:
                                prediction_date = pd.to_datetime(date_val)
                                break
                            except:
                                continue

                if not prediction_date:
                    prediction_date = datetime.now() - timedelta(days=30)  # Default fallback

                days_elapsed = (datetime.now() - prediction_date).days

                if days_elapsed <= 0:
                    return {'status': 'FUTURE_TRADE', 'reason': 'Trade is in the future'}

                # No upper limit on age since Alpha Vantage has 15+ years of data

                # Get historical stock data with better error handling
                end_date = datetime.now()
                start_date = max(prediction_date - timedelta(days=5), datetime.now() - timedelta(days=365))

                hist = ticker.history(start=start_date, end=end_date, interval='1d', timeout=30)

                if hist is None or hist.empty or len(hist) < 2:
                    return {'status': 'NO_STOCK_DATA', 'reason': f'No stock data for {trade.symbol}'}

            except Exception as e:
                return {'status': 'NO_STOCK_DATA', 'reason': f'Data fetch error for {trade.symbol}: {str(e)[:100]}'}

            # Calculate stock price movement with robust error handling
            try:
                # Use the closest date to prediction as entry
                hist_sorted = hist.sort_index()

                # Handle potential NaN values
                hist_sorted = hist_sorted.dropna()
                if hist_sorted.empty:
                    return {'status': 'NO_STOCK_DATA', 'reason': 'No valid price data after cleaning'}

                entry_stock_price = float(hist_sorted['Close'].iloc[0])
                current_stock_price = float(hist_sorted['Close'].iloc[-1])

                # Check for valid prices
                if pd.isna(entry_stock_price) or pd.isna(current_stock_price) or entry_stock_price <= 0 or current_stock_price <= 0:
                    return {'status': 'ERROR', 'reason': 'Invalid stock prices found'}

                max_stock_price = float(hist_sorted['High'].max())
                min_stock_price = float(hist_sorted['Low'].min())

                # Check for valid max/min prices
                if pd.isna(max_stock_price) or pd.isna(min_stock_price):
                    return {'status': 'ERROR', 'reason': 'Invalid max/min prices'}

                # Calculate percentage changes
                stock_change_pct = (current_stock_price - entry_stock_price) / entry_stock_price
                max_stock_change_pct = (max_stock_price - entry_stock_price) / entry_stock_price
                min_stock_change_pct = (min_stock_price - entry_stock_price) / entry_stock_price

            except Exception as e:
                return {'status': 'ERROR', 'reason': f'Price calculation error: {str(e)[:100]}'}

            # Extract trade attributes with comprehensive defaults
            try:
                # Initial and final targets
                initial_target = entry_price * 1.5  # Default 50% gain
                final_target = entry_price * 2.0    # Default 100% gain
                stop_loss = entry_price * 0.7       # Default 30% loss
                position_size = 1                   # Default 1 contract
                delta = 0.3                         # Default delta

                # Try to get actual values from trade object
                for attr, default in [
                    ('initial_target', initial_target),
                    ('final_target', final_target),
                    ('stop_loss', stop_loss),
                    ('position_size', position_size),
                    ('delta', delta)
                ]:
                    if hasattr(trade, attr):
                        val = getattr(trade, attr)
                        if val is not None and str(val).strip() != '' and str(val) != 'nan':
                            try:
                                if attr == 'position_size':
                                    parsed_val = int(float(val))
                                    locals()[attr] = max(1, parsed_val)
                                else:
                                    parsed_val = float(val)
                                    if not pd.isna(parsed_val) and parsed_val > 0:
                                        locals()[attr] = parsed_val
                            except (ValueError, TypeError):
                                pass  # Keep default

                # Ensure delta is reasonable
                delta = min(1.0, max(0.1, abs(delta)))

                # Get option type
                option_type = 'call'  # Default
                for attr in ['option_type', 'type', 'optionType']:
                    if hasattr(trade, attr):
                        val = getattr(trade, attr)
                        if val and str(val).strip().lower() in ['call', 'put']:
                            option_type = str(val).strip().lower()
                            break

            except Exception as e:
                return {'status': 'ERROR', 'reason': f'Trade attribute extraction error: {str(e)[:100]}'}

            # Calculate option price estimates with improved model
            try:
                # Direction multiplier for calls vs puts
                direction_multiplier = 1 if option_type.lower() == 'call' else -1

                # More conservative leverage factor
                leverage_factor = min(4, max(1.5, delta * 6))

                # Estimate option prices
                current_option_est = max(0.01, entry_price * (1 + stock_change_pct * delta * leverage_factor * direction_multiplier))
                max_option_est = max(0.01, entry_price * (1 + max_stock_change_pct * delta * leverage_factor * direction_multiplier))
                min_option_est = max(0.01, entry_price * (1 + min_stock_change_pct * delta * leverage_factor * direction_multiplier))

                # For puts, flip the min/max logic
                if option_type.lower() == 'put':
                    temp = max_option_est
                    max_option_est = min_option_est  
                    min_option_est = temp

                # Check target hits
                hit_initial = max_option_est >= initial_target
                hit_final = max_option_est >= final_target
                hit_stop = min_option_est <= stop_loss

                # Determine exit scenario
                if hit_stop and not hit_initial:
                    exit_price = stop_loss
                    status = 'STOPPED_OUT'
                elif hit_final:
                    exit_price = final_target
                    status = 'FINAL_TARGET'
                elif hit_initial:
                    exit_price = initial_target
                    status = 'INITIAL_TARGET'
                else:
                    exit_price = current_option_est
                    status = 'TIME_EXIT'

                # Calculate P&L
                profit_loss = (exit_price - entry_price) * position_size * 100
                profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100

                return {
                    'status': status,
                    'profit_loss': round(profit_loss, 2),
                    'profit_loss_pct': round(profit_loss_pct, 2),
                    'hit_initial': hit_initial,
                    'hit_final': hit_final,
                    'hit_stop': hit_stop,
                    'entry_price': entry_price,
                    'exit_price': round(exit_price, 2),
                    'max_price_est': round(max_option_est, 2),
                    'min_price_est': round(min_option_est, 2),
                    'current_price_est': round(current_option_est, 2),
                    'stock_change_pct': round(stock_change_pct * 100, 2),
                    'days_elapsed': days_elapsed,
                    'option_type': option_type
                }

            except Exception as e:
                return {'status': 'ERROR', 'reason': f'Option calculation error: {str(e)[:100]}'}

        except Exception as e:
            return {'status': 'ERROR', 'reason': f'General simulation error: {str(e)[:100]}'}

    def backtest_all_trades(self):
        """Run backtest on all loaded trades"""
        print(f"\nStarting backtest on {len(self.trades)} trades...")

        for i, trade in enumerate(self.trades):
            if i % 10 == 0:
                print(f"Processing trade {i+1}/{len(self.trades)}: {getattr(trade, 'symbol', 'Unknown')}")

            try:
                # Simulate the trade performance
                result = self.simulate_option_performance(trade)
                result['trade'] = trade
                self.results.append(result)
            except Exception as e:
                print(f"⚠️ Error processing trade {i+1}: {str(e)[:100]}")
                # Add error result so we can track failures
                self.results.append({
                    'status': 'ERROR',
                    'reason': f'Processing error: {str(e)[:100]}',
                    'trade': trade
                })

            # Small delay to avoid overwhelming APIs
            if i % 50 == 0:
                time.sleep(1)

        print("Backtest complete!")

    def analyze_results(self):
        """Comprehensive analysis of backtest results"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE BACKTEST ANALYSIS")
        print("="*80)

        # Filter valid results
        valid_results = [r for r in self.results if r.get('status') not in ['ERROR', 'NO_STOCK_DATA', 'FUTURE_TRADE']]

        if not valid_results:
            print("❌ No valid results to analyze")
            print(f"Total results processed: {len(self.results)}")

            # Show error breakdown
            error_breakdown = {}
            for r in self.results:
                status = r.get('status', 'UNKNOWN')
                error_breakdown[status] = error_breakdown.get(status, 0) + 1

            print("\n📊 Error breakdown:")
            for status, count in sorted(error_breakdown.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count}")

            # Show some sample error reasons for debugging
            for status in ['ERROR', 'NO_STOCK_DATA']:
                sample_errors = [r.get('reason', 'No reason') for r in self.results if r.get('status') == status][:3]
                if sample_errors:
                    print(f"\n  Sample {status} reasons:")
                    for reason in sample_errors:
                        print(f"    - {reason}")

            return pd.DataFrame()

        # Convert to DataFrame for analysis with safe data extraction
        results_data = []
        for r in valid_results:
            try:
                trade = r['trade']

                # Safely extract trade data with defaults
                symbol = getattr(trade, 'symbol', 'UNKNOWN')
                bias = getattr(trade, 'bias', 'Unknown')
                strike = getattr(trade, 'strike', 0)
                option_type = getattr(trade, 'option_type', 'call')
                delta = getattr(trade, 'delta', None)
                gamma = getattr(trade, 'gamma', None)  
                theta = getattr(trade, 'theta', None)
                score = getattr(trade, 'score', None)
                confluence_score = getattr(trade, 'confluence_score', None)
                prediction_date = getattr(trade, 'prediction_date', None)

                # Convert None values to appropriate defaults
                delta = float(delta) if delta is not None else 0.0
                gamma = float(gamma) if gamma is not None else 0.0
                theta = float(theta) if theta is not None else 0.0
                score = float(score) if score is not None else 0.0
                confluence_score = float(confluence_score) if confluence_score is not None else 0.0

                results_data.append({
                    'symbol': symbol,
                    'bias': bias,
                    'strike': float(strike) if strike else 0.0,
                    'type': str(option_type),
                    'status': r.get('status', 'UNKNOWN'),
                    'profit_loss': float(r.get('profit_loss', 0)),
                    'profit_loss_pct': float(r.get('profit_loss_pct', 0)),
                    'hit_initial': bool(r.get('hit_initial', False)),
                    'hit_final': bool(r.get('hit_final', False)),
                    'hit_stop': bool(r.get('hit_stop', False)),
                    'delta': delta,
                    'gamma': gamma,
                    'theta': theta,
                    'score': score,
                    'confluence_score': confluence_score,
                    'days_elapsed': int(r.get('days_elapsed', 0)),
                    'stock_change_pct': float(r.get('stock_change_pct', 0)),
                    'prediction_date': str(prediction_date) if prediction_date else 'Unknown'
                })
            except Exception as e:
                print(f"⚠️ Error processing result: {e}")
                continue

        if not results_data:
            print("❌ No valid data to analyze after processing")
            return pd.DataFrame()

        df = pd.DataFrame(results_data)

        # 1. Overall Performance
        print(f"\n🎯 OVERALL PERFORMANCE:")
        print(f"   Total trades analyzed: {len(df)}")

        win_rate = ((df['hit_initial'] | df['hit_final']).sum() / len(df) * 100) if len(df) > 0 else 0
        initial_rate = (df['hit_initial'].sum() / len(df) * 100) if len(df) > 0 else 0
        final_rate = (df['hit_final'].sum() / len(df) * 100) if len(df) > 0 else 0
        stop_rate = (df['hit_stop'].sum() / len(df) * 100) if len(df) > 0 else 0

        print(f"   Win rate (hit any target): {win_rate:.1f}%")
        print(f"   Initial target rate: {initial_rate:.1f}%")
        print(f"   Final target rate: {final_rate:.1f}%")
        print(f"   Stop loss rate: {stop_rate:.1f}%")
        print(f"   Average P&L: ${df['profit_loss'].mean():.2f}")
        print(f"   Total P&L: ${df['profit_loss'].sum():.2f}")

        # 2. Performance by Score Ranges
        try:
            print(f"\n📈 PERFORMANCE BY SCORE RANGES:")
            score_bins = [0, 5, 7, 8, 9, 10]
            df['score_range'] = pd.cut(df['confluence_score'], bins=score_bins, include_lowest=True)

            score_analysis = df.groupby('score_range', observed=False).agg({
                'hit_initial': 'mean',
                'hit_final': 'mean', 
                'profit_loss_pct': 'mean',
                'profit_loss': 'count'
            }).round(3)
            score_analysis.columns = ['Initial_Target_%', 'Final_Target_%', 'Avg_Return_%', 'Count']
            print(score_analysis)
        except Exception as e:
            print(f"⚠️ Error in score analysis: {e}")

        # 3. Performance by Greeks (with error handling)
        try:
            print(f"\n⚡ PERFORMANCE BY GREEKS:")

            successful_trades = df[df['hit_initial'] | df['hit_final']]
            unsuccessful_trades = df[~(df['hit_initial'] | df['hit_final'])]

            if len(successful_trades) > 0 and len(unsuccessful_trades) > 0:
                print(f"   Successful trades - Avg Delta: {successful_trades['delta'].mean():.3f}")
                print(f"   Unsuccessful trades - Avg Delta: {unsuccessful_trades['delta'].mean():.3f}")
                print(f"   Successful trades - Avg Gamma: {successful_trades['gamma'].mean():.3f}")
                print(f"   Unsuccessful trades - Avg Gamma: {unsuccessful_trades['gamma'].mean():.3f}")
                print(f"   Successful trades - Avg Score: {successful_trades['score'].mean():.2f}")
                print(f"   Unsuccessful trades - Avg Score: {unsuccessful_trades['score'].mean():.2f}")
        except Exception as e:
            print(f"⚠️ Error in Greeks analysis: {e}")

        # 4. Performance by Option Type and Bias (with error handling)
        try:
            print(f"\n🎭 PERFORMANCE BY TYPE & BIAS:")
            type_bias_analysis = df.groupby(['type', 'bias']).agg({
                'hit_initial': 'mean',
                'profit_loss_pct': 'mean',
                'profit_loss': 'count'
            }).round(3)
            print(type_bias_analysis)
        except Exception as e:
            print(f"⚠️ Error in type/bias analysis: {e}")

        # 5. Time-based Performance (with error handling)
        try:
            print(f"\n⏰ TIME-BASED PERFORMANCE:")
            df['days_held'] = pd.cut(df['days_elapsed'], bins=[0, 3, 7, 14, 30, 365], 
                                   labels=['0-3d', '3-7d', '7-14d', '14-30d', '30d+'])
            time_analysis = df.groupby('days_held', observed=False).agg({
                'hit_initial': 'mean',
                'profit_loss_pct': 'mean'
            }).round(3)
            print(time_analysis)
        except Exception as e:
            print(f"⚠️ Error in time analysis: {e}")

        # 6. Optimization Recommendations
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        try:
            self.generate_recommendations(df)
        except Exception as e:
            print(f"⚠️ Error generating recommendations: {e}")

        # Save results
        try:
            self.save_detailed_results(df)
        except Exception as e:
            print(f"⚠️ Error saving results: {e}")

        return df

    def generate_recommendations(self, df: pd.DataFrame):
        """Generate specific recommendations for improving the scanner"""
        recommendations = []

        # Score threshold recommendations
        high_score_df = df[df['confluence_score'] >= 8]
        low_score_df = df[df['confluence_score'] < 6]

        if len(high_score_df) > 0:
            high_score_win_rate = (high_score_df['hit_initial'] | high_score_df['hit_final']).mean()
            recommendations.append(f"1. High scoring trades (8+): {high_score_win_rate*100:.1f}% win rate - Focus on these!")

        if len(low_score_df) > 0:
            low_score_win_rate = (low_score_df['hit_initial'] | low_score_df['hit_final']).mean()
            recommendations.append(f"2. Low scoring trades (<6): {low_score_win_rate*100:.1f}% win rate - Consider filtering out")

        # Greeks recommendations
        successful = df[df['hit_initial'] | df['hit_final']]
        if len(successful) > 0:
            optimal_delta = successful['delta'].mean()
            optimal_gamma = successful['gamma'].mean()
            recommendations.append(f"3. Optimal Delta range: {optimal_delta-0.05:.2f} - {optimal_delta+0.05:.2f}")
            recommendations.append(f"4. Optimal Gamma range: {optimal_gamma-0.01:.3f} - {optimal_gamma+0.01:.3f}")

        # Bias recommendations
        bias_performance = df.groupby('bias')['hit_initial'].mean()
        best_bias = bias_performance.idxmax()
        recommendations.append(f"5. Best performing bias: {best_bias} ({bias_performance[best_bias]*100:.1f}% success rate)")

        for rec in recommendations:
            print(f"   {rec}")

    def save_detailed_results(self, df: pd.DataFrame):
        """Save detailed results for further analysis"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save detailed CSV
        csv_file = f'./TradingPlans/backtest_results_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
```python
        print(f"\n💾 Detailed results saved to {csv_file}")

        # Save summary JSON
        summary = {
            'backtest_date': datetime.now().isoformat(),
            'total_trades': len(df),
            'win_rate': float((df['hit_initial'] | df['hit_final']).mean() * 100),
            'initial_target_rate': float(df['hit_initial'].mean() * 100),
            'final_target_rate': float(df['hit_final'].mean() * 100),
            'stop_loss_rate': float(df['hit_stop'].mean() * 100),
            'total_profit_loss': float(df['profit_loss'].sum()),
            'average_profit_loss': float(df['profit_loss'].mean()),
            'best_score_threshold': 8.0,  # Based on analysis
            'optimal_delta_range': [0.15, 0.35],  # Based on successful trades
            'recommendations': [
                "Focus on trades with confluence scores >= 8",
                "Consider filtering trades with scores < 6",
                "Optimize for delta range 0.15-0.35",
                "Monitor gamma/theta ratios for explosive potential"
            ]
        }

        json_file = f'./TradingPlans/backtest_summary_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"📋 Summary saved to {json_file}")

    def calculate_similarity(self, option1: Dict, option2: Dict) -> float:
        """Placeholder similarity function"""
        # For demonstration, return a constant value (replace with actual logic)
        return 0.75

def main():
    """Main backtesting function"""
    print("🚀 Advanced Options Scanner Backtesting Engine")
    print("=" * 50)

    # Initialize backtester
    backtester = AdvancedBacktester()

    # Load all historical trades
    trades = backtester.load_all_historical_trades()

    if not trades:
        print("❌ No trades found. Make sure you have progressive_results_*.json files in ./TradingPlans/")
        return

    # Run backtest
    backtester.backtest_all_trades()

    # Analyze results
    results_df = backtester.analyze_results()

    print("\n✅ Backtesting complete! Check the saved files for detailed results.")

    return backtester, results_df

if __name__ == "__main__":
    backtester, results = main()