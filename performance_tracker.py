
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
        for track_id, track_data in performance_data.items():
            try:
                if track_data.get('final_outcome') is not None:
                    continue  # Already finalized
                
                symbol = track_data['symbol']
                option_details = track_data['option_details']
                expiration = pd.to_datetime(option_details['expiration'])
                
                # Skip if expired
                if datetime.now() > expiration:
                    if track_data.get('final_outcome') is None:
                        track_data['final_outcome'] = 'EXPIRED'
                        track_data['final_price'] = 0.0
                    continue
                
                # Get current option price
                current_price = self.get_current_option_price(symbol, option_details)
                
                if current_price is not None:
                    entry_price = option_details['entry_price']
                    target_price = option_details['predicted_target']
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
                    if current_price >= target_price and not track_data['hit_target']:
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
                
            except Exception as e:
                print(f"Error updating {track_id}: {e}")
                continue
        
        self.save_performance_data(performance_data)
        print(f"✅ Updated {updated_count} options")
        
        return updated_count
    
    def get_current_option_price(self, symbol, option_details):
        """
        Get current option price using yfinance
        """
        try:
            ticker = yf.Ticker(symbol)
            expiration_date = pd.to_datetime(option_details['expiration']).strftime('%Y-%m-%d')
            
            # Get option chain
            options = ticker.option_chain(expiration_date)
            
            if option_details['type'].lower() == 'call':
                chain = options.calls
            else:
                chain = options.puts
            
            # Find matching strike
            strike = float(option_details['strike'])
            matching_options = chain[chain['strike'] == strike]
            
            if not matching_options.empty:
                return float(matching_options.iloc[0]['lastPrice'])
            
            return None
            
        except Exception as e:
            print(f"Error fetching option price for {symbol}: {e}")
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
    
    def get_improvement_suggestions(self):
        """
        Analyze performance data to suggest improvements
        """
        metrics = self.calculate_performance_metrics()
        
        suggestions = []
        
        # Confluence score analysis
        if 'confluence_score_accuracy' in metrics:
            best_score_range = None
            best_win_rate = 0
            
            for score_range, data in metrics['confluence_score_accuracy'].items():
                if data['total'] >= 5 and data['win_rate'] > best_win_rate:
                    best_win_rate = data['win_rate']
                    best_score_range = score_range
            
            if best_score_range:
                suggestions.append(f"Focus on confluence scores in range {best_score_range} (win rate: {best_win_rate:.1f}%)")
        
        # Bias accuracy analysis
        if 'bias_accuracy' in metrics:
            for bias, data in metrics['bias_accuracy'].items():
                if data['total'] >= 3:
                    if data['win_rate'] < 40:
                        suggestions.append(f"{bias} bias predictions are underperforming ({data['win_rate']:.1f}% win rate)")
                    elif data['win_rate'] > 70:
                        suggestions.append(f"{bias} bias predictions are performing well ({data['win_rate']:.1f}% win rate)")
        
        # Overall win rate
        if metrics.get('win_rate', 0) < 50:
            suggestions.append("Overall win rate is below 50% - consider tightening entry criteria")
        
        return suggestions

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
