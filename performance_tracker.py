import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional

class PerformanceTracker:
    def __init__(self, data_dir="./TradingPlans"):
        self.data_dir = data_dir
        self.performance_file = os.path.join(data_dir, "performance_tracking.json")
        self.metrics_file = os.path.join(data_dir, "performance_metrics.json")

    def load_performance_data(self):
        """Load existing performance tracking data"""
        if os.path.exists(self.performance_file):
            with open(self.performance_file, 'r') as f:
                return json.load(f)
        return {}

    def save_performance_data(self, data):
        """Save performance tracking data"""
        with open(self.performance_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def track_option_performance(self, symbol, option_data, trade_plan, prediction_date):
        """
        Track an option's performance over time
        """
        performance_data = self.load_performance_data()

        # Create unique tracking ID
        track_id = f"{symbol}_{option_data.get('strike')}_{option_data.get('type')}_{option_data.get('expiration')}_{prediction_date}"

        if track_id not in performance_data:
            performance_data[track_id] = {
                'symbol': symbol,
                'prediction_date': prediction_date,
                'option_details': {
                    'strike': option_data.get('strike'),
                    'type': option_data.get('type'),
                    'expiration': option_data.get('expiration'),
                    'entry_price': trade_plan.get('entry_price'),
                    'predicted_target': trade_plan.get('initial_target'),
                    'predicted_bias': trade_plan.get('bias'),
                    'confluence_score': option_data.get('score', 0),
                    'delta': option_data.get('delta'),
                    'gamma': option_data.get('gamma'),
                    'theta': option_data.get('theta'),
                    'implied_vol': option_data.get('implied_volatility'),
                },
                'daily_tracking': {},
                'final_outcome': None,
                'max_profit': 0,
                'max_loss': 0,
                'days_tracked': 0,
                'hit_target': False,
                'hit_stop': False
            }

        self.save_performance_data(performance_data)
        return track_id

    def update_daily_performance(self):
        """
        Update performance for all tracked options daily
        """
        performance_data = self.load_performance_data()
        today = datetime.now().strftime('%Y-%m-%d')

        print(f"📊 Updating daily performance for {len(performance_data)} tracked options...")

        updated_count = 0
        skipped_reasons = {'finalized': 0, 'expired': 0, 'no_price': 0, 'invalid_entry': 0, 'conversion_error': 0}
        
        for track_id, track_data in performance_data.items():
            try:
                if track_data.get('final_outcome') is not None:
                    skipped_reasons['finalized'] += 1
                    continue  # Already finalized

                symbol = track_data['symbol']
                option_details = track_data['option_details']
                expiration = pd.to_datetime(option_details['expiration'])

                # Skip if expired
                if datetime.now() > expiration:
                    if track_data.get('final_outcome') is None:
                        track_data['final_outcome'] = 'EXPIRED'
                        track_data['final_price'] = 0.0
                    skipped_reasons['expired'] += 1
                    continue

                # Get current option price
                current_price = self.get_current_option_price(symbol, option_details)

                if current_price is not None and current_price > 0:
                    # Safely get and convert prices with validation
                    entry_price_raw = option_details.get('entry_price')
                    target_price_raw = option_details.get('predicted_target')
                    
                    # Skip if entry price is None or invalid
                    if entry_price_raw is None or entry_price_raw == '' or entry_price_raw <= 0:
                        skipped_reasons['invalid_entry'] += 1
                        print(f"⚠️ Skipping {symbol} - invalid entry price: {entry_price_raw}")
                        continue
                        
                    try:
                        entry_price = float(entry_price_raw)
                        target_price = float(target_price_raw) if target_price_raw is not None else 0
                    except (ValueError, TypeError):
                        skipped_reasons['conversion_error'] += 1
                        print(f"⚠️ Skipping {symbol} - price conversion error")
                        continue
                    
                    # Skip if entry price is invalid
                    if entry_price <= 0:
                        skipped_reasons['invalid_entry'] += 1
                        print(f"⚠️ Skipping {symbol} - entry price <= 0: {entry_price}")
                        continue
                        
                    stop_price = entry_price * 0.75  # Assuming 25% stop loss

                    # Calculate P&L
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100

                    # Update daily tracking
                    track_data['daily_tracking'][today] = {
                        'price': current_price,
                        'pnl_percent': pnl_percent,
                        'pnl_dollar': current_price - entry_price,
                        'days_held': (datetime.now() - pd.to_datetime(track_data['prediction_date'])).days
                    }

                    # Update max profit/loss
                    if pnl_percent > track_data['max_profit']:
                        track_data['max_profit'] = pnl_percent
                    if pnl_percent < track_data['max_loss']:
                        track_data['max_loss'] = pnl_percent

                    # Check if target or stop hit
                    if target_price > 0 and current_price >= target_price and not track_data['hit_target']:
                        track_data['hit_target'] = True
                        track_data['target_hit_date'] = today
                        track_data['final_outcome'] = 'TARGET_HIT'
                        track_data['final_price'] = current_price

                    elif current_price <= stop_price and not track_data['hit_stop']:
                        track_data['hit_stop'] = True
                        track_data['stop_hit_date'] = today
                        track_data['final_outcome'] = 'STOP_HIT'
                        track_data['final_price'] = current_price

                    track_data['days_tracked'] += 1
                    updated_count += 1
                else:
                    # Unable to get current price, increment days tracked but skip price updates
                    track_data['days_tracked'] += 1
                    skipped_reasons['no_price'] += 1
                    print(f"⚠️ No price data for {symbol} {option_details.get('strike')} {option_details.get('type')}")

            except Exception as e:
                print(f"Error updating {track_id}: {e}")
                continue

        self.save_performance_data(performance_data)
        print(f"✅ Updated {updated_count} options")
        print(f"📊 Skipped breakdown:")
        print(f"  • Already finalized: {skipped_reasons['finalized']}")
        print(f"  • Expired: {skipped_reasons['expired']}")
        print(f"  • No current price: {skipped_reasons['no_price']}")
        print(f"  • Invalid entry price: {skipped_reasons['invalid_entry']}")
        print(f"  • Conversion errors: {skipped_reasons['conversion_error']}")

        return updated_count

    def get_current_option_price(self, symbol, option_details):
        """
        Get current option price using yfinance
        """
        try:
            # Validate inputs first
            if not symbol or not option_details:
                return None
                
            strike = option_details.get('strike')
            option_type = option_details.get('type', '').lower()
            expiration = option_details.get('expiration')
            
            if not all([strike, option_type, expiration]):
                return None
                
            ticker = yf.Ticker(symbol)
            expiration_date = pd.to_datetime(expiration).strftime('%Y-%m-%d')

            # Get option chain
            options = ticker.option_chain(expiration_date)
            
            if options is None:
                return None

            if option_type == 'call':
                chain = options.calls
            else:
                chain = options.puts

            if chain is None or chain.empty:
                return None

            # Find matching strike
            strike_float = float(strike)
            matching_options = chain[chain['strike'] == strike_float]

            if not matching_options.empty:
                last_price = matching_options.iloc[0]['lastPrice']
                # Handle case where lastPrice might be None or NaN
                if last_price is not None and not pd.isna(last_price) and last_price != '':
                    try:
                        return float(last_price)
                    except (ValueError, TypeError):
                        return None

            return None

        except Exception as e:
            print(f"Error fetching option price for {symbol} {option_details.get('strike')} {option_details.get('type')}: {e}")
            return None

    def calculate_performance_metrics(self):
        """
        Calculate overall performance metrics and accuracy
        """
        performance_data = self.load_performance_data()

        if not performance_data:
            return {}

        metrics = {
            'total_predictions': len(performance_data),
            'targets_hit': 0,
            'stops_hit': 0,
            'expired_worthless': 0,
            'still_active': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'confluence_score_accuracy': {},
            'bias_accuracy': {},
            'best_performers': [],
            'worst_performers': []
        }

        all_outcomes = []
        confluence_outcomes = {}
        bias_outcomes = {'Bullish': [], 'Bearish': [], 'Neutral': []}

        for track_id, data in performance_data.items():
            outcome = data.get('final_outcome')
            confluence_score = data['option_details'].get('confluence_score', 0)
            predicted_bias = data['option_details'].get('predicted_bias', 'Unknown')
            max_profit = data.get('max_profit', 0)

            # Count outcomes
            if outcome == 'TARGET_HIT':
                metrics['targets_hit'] += 1
                all_outcomes.append('WIN')
            elif outcome == 'STOP_HIT':
                metrics['stops_hit'] += 1
                all_outcomes.append('LOSS')
            elif outcome == 'EXPIRED':
                metrics['expired_worthless'] += 1
                all_outcomes.append('LOSS')
            else:
                metrics['still_active'] += 1
                continue

            # Track by confluence score ranges
            score_range = f"{int(confluence_score//2)*2}-{int(confluence_score//2)*2+2}"
            if score_range not in confluence_outcomes:
                confluence_outcomes[score_range] = []
            confluence_outcomes[score_range].append(outcome)

            # Track by bias
            if predicted_bias in bias_outcomes:
                bias_outcomes[predicted_bias].append(outcome)

            # Track best/worst performers
            performance_record = {
                'symbol': data['symbol'],
                'max_profit': max_profit,
                'confluence_score': confluence_score,
                'outcome': outcome,
                'predicted_bias': predicted_bias
            }

            if max_profit > 50:  # > 50% gain
                metrics['best_performers'].append(performance_record)
            elif max_profit < -25:  # > 25% loss
                metrics['worst_performers'].append(performance_record)

        # Calculate win rate
        if all_outcomes:
            wins = all_outcomes.count('WIN')
            metrics['win_rate'] = (wins / len(all_outcomes)) * 100

        # Calculate confluence score accuracy
        for score_range, outcomes in confluence_outcomes.items():
            if outcomes:
                win_rate = (outcomes.count('TARGET_HIT') / len(outcomes)) * 100
                metrics['confluence_score_accuracy'][score_range] = {
                    'total': len(outcomes),
                    'wins': outcomes.count('TARGET_HIT'),
                    'win_rate': win_rate
                }

        # Calculate bias accuracy
        for bias, outcomes in bias_outcomes.items():
            if outcomes:
                win_rate = (outcomes.count('TARGET_HIT') / len(outcomes)) * 100
                metrics['bias_accuracy'][bias] = {
                    'total': len(outcomes),
                    'wins': outcomes.count('TARGET_HIT'),
                    'win_rate': win_rate
                }

        # Sort performers
        metrics['best_performers'] = sorted(metrics['best_performers'], 
                                          key=lambda x: x['max_profit'], reverse=True)[:10]
        metrics['worst_performers'] = sorted(metrics['worst_performers'], 
                                           key=lambda x: x['max_profit'])[:10]

        # Save metrics
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)

        return metrics

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
    
    def get_improvement_suggestions(self):
        """Generate specific improvement suggestions based on performance data"""
        metrics = self.calculate_performance_metrics()
        suggestions = []

        # Win rate suggestions
        if metrics['win_rate'] < 50:
            suggestions.append("Overall win rate is below 50% - consider tightening entry criteria")

        # Confluence score suggestions
        confluence_accuracy = metrics.get('confluence_score_accuracy', {})
        for score_range, data in confluence_accuracy.items():
            if data['total'] >= 5 and data['win_rate'] < 40:
                suggestions.append(f"Low win rate for {score_range} confluence scores - review pattern detection")

        # Bias accuracy suggestions
        bias_accuracy = metrics.get('bias_accuracy', {})
        for bias, data in bias_accuracy.items():
            if data['total'] >= 3 and data['win_rate'] < 45:
                suggestions.append(f"{bias} bias predictions underperforming - review directional analysis")

        # Position sizing suggestions
        if metrics.get('avg_loss', 0) > metrics.get('avg_win', 0):
            suggestions.append("Average losses exceed average wins - consider tighter stop losses")

        return suggestions

    def get_best_performing_symbols(self, min_trades=2):
        """
        Get symbols that have historically performed best in our scanner.
        Returns list of symbols sorted by performance.
        """
        try:
            if not os.path.exists(self.performance_file):
                return []

            with open(self.performance_file, 'r') as f:
                tracking_data = json.load(f)

            symbol_performance = {}

            for track_id, data in tracking_data.items():
                symbol = data.get('symbol', '')
                if not symbol:
                    continue

                # Initialize symbol tracking
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = {
                        'total_trades': 0,
                        'wins': 0,
                        'total_profit': 0,
                        'max_profit': 0
                    }

                symbol_performance[symbol]['total_trades'] += 1

                # Check if this trade was profitable
                max_profit = data.get('max_profit', 0)
                symbol_performance[symbol]['total_profit'] += max_profit
                symbol_performance[symbol]['max_profit'] = max(
                    symbol_performance[symbol]['max_profit'], max_profit
                )

                if max_profit > 10:  # Consider 10%+ a win
                    symbol_performance[symbol]['wins'] += 1

            # Filter symbols with minimum trades and calculate win rates
            qualified_symbols = []
            for symbol, perf in symbol_performance.items():
                if perf['total_trades'] >= min_trades:
                    win_rate = perf['wins'] / perf['total_trades'] * 100
                    avg_profit = perf['total_profit'] / perf['total_trades']

                    qualified_symbols.append({
                        'symbol': symbol,
                        'win_rate': win_rate,
                        'avg_profit': avg_profit,
                        'total_trades': perf['total_trades'],
                        'max_profit': perf['max_profit']
                    })

            # Sort by combined score (win rate + avg profit)
            qualified_symbols.sort(
                key=lambda x: (x['win_rate'] * 0.6 + x['avg_profit'] * 0.4), 
                reverse=True
            )

            return [item['symbol'] for item in qualified_symbols]

        except Exception as e:
            print(f"Error getting best performing symbols: {e}")
            return []

    def get_tracking_summary(self):
        """Get a summary of all tracked options by status"""
        performance_data = self.load_performance_data()
        
        summary = {
            'active_options': [],
            'finalized_options': [],
            'invalid_options': [],
            'expired_options': []
        }
        
        for track_id, data in performance_data.items():
            option_info = {
                'track_id': track_id,
                'symbol': data.get('symbol'),
                'strike': data.get('option_details', {}).get('strike'),
                'type': data.get('option_details', {}).get('type'),
                'expiration': data.get('option_details', {}).get('expiration'),
                'entry_price': data.get('option_details', {}).get('entry_price'),
                'final_outcome': data.get('final_outcome'),
                'max_profit': data.get('max_profit', 0),
                'prediction_date': data.get('prediction_date')
            }
            
            # Check if expired
            try:
                exp_date = pd.to_datetime(option_info['expiration'])
                if datetime.now() > exp_date:
                    summary['expired_options'].append(option_info)
                    continue
            except:
                pass
            
            # Check if invalid entry price
            if option_info['entry_price'] is None or option_info['entry_price'] == '':
                summary['invalid_options'].append(option_info)
            elif option_info['final_outcome'] is not None:
                summary['finalized_options'].append(option_info)
            else:
                summary['active_options'].append(option_info)
        
        return summary
    
    def cleanup_finalized_options(self, keep_days=30):
        """Remove finalized options older than specified days"""
        performance_data = self.load_performance_data()
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        original_count = len(performance_data)
        cleaned_data = {}
        removed_count = 0
        
        for track_id, data in performance_data.items():
            # Keep if not finalized
            if data.get('final_outcome') is None:
                cleaned_data[track_id] = data
                continue
                
            # Keep if recent
            try:
                prediction_date = pd.to_datetime(data.get('prediction_date'))
                if prediction_date >= cutoff_date:
                    cleaned_data[track_id] = data
                    continue
            except:
                pass
            
            # Remove old finalized options
            removed_count += 1
            print(f"Removing finalized option: {data.get('symbol')} {data.get('option_details', {}).get('strike')} {data.get('option_details', {}).get('type')}")
        
        # Save cleaned data
        self.save_performance_data(cleaned_data)
        print(f"✅ Cleanup complete: Removed {removed_count} old finalized options")
        print(f"📊 Total options: {original_count} → {len(cleaned_data)}")
        
        return removed_count
    
    def remove_invalid_options(self):
        """Remove options with invalid entry prices"""
        performance_data = self.load_performance_data()
        
        original_count = len(performance_data)
        cleaned_data = {}
        removed_count = 0
        
        for track_id, data in performance_data.items():
            entry_price = data.get('option_details', {}).get('entry_price')
            
            # Keep if entry price is valid
            if entry_price is not None and entry_price != '' and entry_price != 0:
                cleaned_data[track_id] = data
            else:
                removed_count += 1
                print(f"Removing invalid option: {data.get('symbol')} {data.get('option_details', {}).get('strike')} {data.get('option_details', {}).get('type')} (entry_price: {entry_price})")
        
        # Save cleaned data
        self.save_performance_data(cleaned_data)
        print(f"✅ Invalid options cleanup complete: Removed {removed_count} options with invalid entry prices")
        print(f"📊 Total options: {original_count} → {len(cleaned_data)}")
        
        return removed_count

def update_performance_tracking():
    """Standalone function to update performance tracking"""
    tracker = PerformanceTracker()
    return tracker.update_daily_performance()

def analyze_performance():
    """Standalone function to analyze performance"""
    tracker = PerformanceTracker()
    metrics = tracker.calculate_performance_metrics()
    suggestions = tracker.get_improvement_suggestions()

    print("\n📊 PERFORMANCE ANALYSIS")
    print("=" * 50)
    print(f"Total Predictions: {metrics.get('total_predictions', 0)}")
    print(f"Win Rate: {metrics.get('win_rate', 0):.1f}%")
    print(f"Targets Hit: {metrics.get('targets_hit', 0)}")
    print(f"Stops Hit: {metrics.get('stops_hit', 0)}")
    print(f"Still Active: {metrics.get('still_active', 0)}")

    print("\n🎯 CONFLUENCE SCORE ACCURACY:")
    for score_range, data in metrics.get('confluence_score_accuracy', {}).items():
        print(f"  {score_range}: {data['win_rate']:.1f}% ({data['wins']}/{data['total']})")

    print("\n📈 BIAS ACCURACY:")
    for bias, data in metrics.get('bias_accuracy', {}).items():
        print(f"  {bias}: {data['win_rate']:.1f}% ({data['wins']}/{data['total']})")

    print("\n💡 IMPROVEMENT SUGGESTIONS:")
    for suggestion in suggestions:
        print(f"  • {suggestion}")

    return metrics, suggestions

if __name__ == "__main__":
    analyze_performance()