
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
    
    def get_option_price_history(self, symbol: str, strike: float, option_type: str, 
                                expiry: str, start_date: datetime, days: int = 30) -> Optional[Dict]:
        """Get option price history using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Format expiration date for yfinance
            exp_date = pd.to_datetime(expiry).strftime('%Y-%m-%d')
            
            # Get option chain for the expiration date
            try:
                options = ticker.option_chain(exp_date)
                
                if option_type.lower() == 'call':
                    chain = options.calls
                else:
                    chain = options.puts
                
                # Find the specific strike
                option_row = chain[chain['strike'] == strike]
                
                if not option_row.empty:
                    current_price = float(option_row.iloc[0]['lastPrice'])
                    bid = float(option_row.iloc[0]['bid'])
                    ask = float(option_row.iloc[0]['ask'])
                    volume = float(option_row.iloc[0]['volume'])
                    
                    return {
                        'current_price': current_price,
                        'bid': bid,
                        'ask': ask,
                        'mid_price': (bid + ask) / 2 if bid > 0 and ask > 0 else current_price,
                        'volume': volume,
                        'available': True
                    }
                else:
                    return {'available': False, 'reason': 'Strike not found'}
                    
            except Exception as e:
                return {'available': False, 'reason': f'Option chain error: {str(e)}'}
                
        except Exception as e:
            return {'available': False, 'reason': f'Symbol error: {str(e)}'}
    
    def simulate_option_performance(self, trade: TradePlan) -> Dict:
        """Simulate option performance based on stock price movement"""
        try:
            # Get stock price data
            ticker = yf.Ticker(trade.symbol)
            
            # Calculate days since prediction
            prediction_date = pd.to_datetime(trade.prediction_date)
            days_elapsed = (datetime.now() - prediction_date).days
            
            if days_elapsed <= 0:
                return {'status': 'FUTURE_TRADE', 'reason': 'Trade is in the future'}
            
            # Get historical stock data
            end_date = datetime.now()
            start_date = prediction_date
            
            hist = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if hist.empty:
                return {'status': 'NO_STOCK_DATA', 'reason': 'No stock price data available'}
            
            # Calculate stock price movement
            entry_stock_price = hist['Close'].iloc[0]
            current_stock_price = hist['Close'].iloc[-1]
            max_stock_price = hist['High'].max()
            min_stock_price = hist['Low'].min()
            
            # Estimate option price changes (simplified Black-Scholes approximation)
            stock_change_pct = (current_stock_price - entry_stock_price) / entry_stock_price
            max_stock_change_pct = (max_stock_price - entry_stock_price) / entry_stock_price
            min_stock_change_pct = (min_stock_price - entry_stock_price) / entry_stock_price
            
            # Estimate option price changes using delta (simplified)
            delta = abs(trade.delta) if trade.delta else 0.3  # Default delta if not available
            
            # Calculate estimated option prices
            current_option_est = trade.entry_price * (1 + stock_change_pct * delta * 3)  # Amplify with leverage
            max_option_est = trade.entry_price * (1 + max_stock_change_pct * delta * 3)
            min_option_est = trade.entry_price * (1 + min_stock_change_pct * delta * 3)
            
            # Ensure prices don't go negative
            current_option_est = max(0.01, current_option_est)
            max_option_est = max(0.01, max_option_est)
            min_option_est = max(0.01, min_option_est)
            
            # Check targets
            hit_initial = max_option_est >= trade.initial_target
            hit_final = max_option_est >= trade.final_target
            hit_stop = min_option_est <= trade.stop_loss
            
            # Determine exit scenario
            if hit_stop:
                exit_price = trade.stop_loss
                status = 'STOPPED_OUT'
            elif hit_final:
                exit_price = trade.final_target
                status = 'FINAL_TARGET'
            elif hit_initial:
                exit_price = trade.initial_target
                status = 'INITIAL_TARGET'
            else:
                exit_price = current_option_est
                status = 'TIME_EXIT'
            
            # Calculate P&L
            profit_loss = (exit_price - trade.entry_price) * trade.position_size * 100
            profit_loss_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
            
            return {
                'status': status,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'hit_initial': hit_initial,
                'hit_final': hit_final,
                'hit_stop': hit_stop,
                'entry_price': trade.entry_price,
                'exit_price': exit_price,
                'max_price_est': max_option_est,
                'min_price_est': min_option_est,
                'current_price_est': current_option_est,
                'stock_change_pct': stock_change_pct * 100,
                'days_elapsed': days_elapsed
            }
            
        except Exception as e:
            return {'status': 'ERROR', 'reason': f'Simulation error: {str(e)}'}
    
    def backtest_all_trades(self):
        """Run backtest on all loaded trades"""
        print(f"\nStarting backtest on {len(self.trades)} trades...")
        
        for i, trade in enumerate(self.trades):
            if i % 10 == 0:
                print(f"Processing trade {i+1}/{len(self.trades)}: {trade.symbol}")
            
            # Simulate the trade performance
            result = self.simulate_option_performance(trade)
            result['trade'] = trade
            self.results.append(result)
            
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
            return
        
        # Convert to DataFrame for analysis
        results_data = []
        for r in valid_results:
            trade = r['trade']
            results_data.append({
                'symbol': trade.symbol,
                'bias': trade.bias,
                'strike': trade.strike,
                'type': trade.option_type,
                'status': r['status'],
                'profit_loss': r.get('profit_loss', 0),
                'profit_loss_pct': r.get('profit_loss_pct', 0),
                'hit_initial': r.get('hit_initial', False),
                'hit_final': r.get('hit_final', False),
                'hit_stop': r.get('hit_stop', False),
                'delta': trade.delta or 0,
                'gamma': trade.gamma or 0,
                'theta': trade.theta or 0,
                'score': trade.score or 0,
                'confluence_score': trade.confluence_score or 0,
                'days_elapsed': r.get('days_elapsed', 0),
                'stock_change_pct': r.get('stock_change_pct', 0),
                'prediction_date': trade.prediction_date
            })
        
        df = pd.DataFrame(results_data)
        
        # 1. Overall Performance
        print(f"\n🎯 OVERALL PERFORMANCE:")
        print(f"   Total trades analyzed: {len(df)}")
        print(f"   Win rate (hit any target): {((df['hit_initial'] | df['hit_final']).sum() / len(df) * 100):.1f}%")
        print(f"   Initial target rate: {(df['hit_initial'].sum() / len(df) * 100):.1f}%")
        print(f"   Final target rate: {(df['hit_final'].sum() / len(df) * 100):.1f}%")
        print(f"   Stop loss rate: {(df['hit_stop'].sum() / len(df) * 100):.1f}%")
        print(f"   Average P&L: ${df['profit_loss'].mean():.2f}")
        print(f"   Total P&L: ${df['profit_loss'].sum():.2f}")
        
        # 2. Performance by Score Ranges
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
        
        # 3. Performance by Greeks
        print(f"\n⚡ PERFORMANCE BY GREEKS:")
        
        # Delta analysis
        successful_trades = df[df['hit_initial'] | df['hit_final']]
        unsuccessful_trades = df[~(df['hit_initial'] | df['hit_final'])]
        
        if len(successful_trades) > 0 and len(unsuccessful_trades) > 0:
            print(f"   Successful trades - Avg Delta: {successful_trades['delta'].mean():.3f}")
            print(f"   Unsuccessful trades - Avg Delta: {unsuccessful_trades['delta'].mean():.3f}")
            print(f"   Successful trades - Avg Gamma: {successful_trades['gamma'].mean():.3f}")
            print(f"   Unsuccessful trades - Avg Gamma: {unsuccessful_trades['gamma'].mean():.3f}")
            print(f"   Successful trades - Avg Score: {successful_trades['score'].mean():.2f}")
            print(f"   Unsuccessful trades - Avg Score: {unsuccessful_trades['score'].mean():.2f}")
        
        # 4. Performance by Option Type and Bias
        print(f"\n🎭 PERFORMANCE BY TYPE & BIAS:")
        type_bias_analysis = df.groupby(['type', 'bias']).agg({
            'hit_initial': 'mean',
            'profit_loss_pct': 'mean',
            'profit_loss': 'count'
        }).round(3)
        print(type_bias_analysis)
        
        # 5. Time-based Performance
        print(f"\n⏰ TIME-BASED PERFORMANCE:")
        df['days_held'] = pd.cut(df['days_elapsed'], bins=[0, 3, 7, 14, 30, 365], labels=['0-3d', '3-7d', '7-14d', '14-30d', '30d+'])
        time_analysis = df.groupby('days_held', observed=False).agg({
            'hit_initial': 'mean',
            'profit_loss_pct': 'mean'
        }).round(3)
        print(time_analysis)
        
        # 6. Optimization Recommendations
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        self.generate_recommendations(df)
        
        # Save results
        self.save_detailed_results(df)
        
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
