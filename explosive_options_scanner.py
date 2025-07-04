
# explosive_options_scanner.py
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import concurrent.futures
import requests
import yfinance as yf
import time

from enhanced_options_grader import EnhancedOptionsGrader
from intelligent_trade_planner import IntelligentTradePlanner
from performance_tracker import PerformanceTracker

class ExplosiveOptionsScanner:
    """
    Main integration class that combines all components to find explosive options opportunities
    """
    
    def __init__(self, alpha_vantage_key: str, base_dir: str = "./TradingPlans"):
        self.av_key = alpha_vantage_key
        self.base_dir = base_dir
        
        # Initialize all components
        self.grader = EnhancedOptionsGrader(alpha_vantage_key)
        self.planner = IntelligentTradePlanner(alpha_vantage_key)
        self.tracker = PerformanceTracker(base_dir)
        
        # Load and adapt based on historical performance
        self._adapt_from_history()
        
        # Scan configuration
        self.scan_config = {
            'min_score': 60,  # Minimum score to consider
            'max_positions': 10,  # Max concurrent positions
            'scan_frequency': 'continuous',  # or 'daily', 'hourly'
            'focus_list': []  # Symbols to prioritize
        }
        
        # Results cache
        self.scan_results = {}
        self.last_scan_time = None
    
    def run_explosive_scan(self, 
                          symbols: List[str] = None,
                          scan_type: str = 'comprehensive',
                          filters: Dict = None) -> Dict:
        """
        Run the explosive options scanner
        
        Args:
            symbols: List of symbols to scan (None = use discovery)
            scan_type: 'comprehensive', 'quick', 'earnings', 'unusual_activity'
            filters: Additional filters to apply
        """
        print(f"🚀 EXPLOSIVE OPTIONS SCANNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Get symbols based on scan type
        if symbols is None:
            symbols = self._discover_symbols(scan_type)
        
        print(f"🔍 Scanning {len(symbols)} symbols for explosive opportunities...")
        
        # Initialize results
        results = {
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'scan_type': scan_type,
                'symbols_scanned': len(symbols),
                'filters_applied': filters or {}
            },
            'opportunities': {},
            'top_picks': [],
            'by_category': {
                'earnings_plays': [],
                'unusual_activity': [],
                'technical_setups': [],
                'volatility_plays': []
            }
        }
        
        # Process symbols in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {}
            
            for symbol in symbols:
                future = executor.submit(self._scan_symbol, symbol, scan_type, filters)
                future_to_symbol[future] = symbol
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    symbol_results = future.result()
                    if symbol_results and symbol_results['best_opportunity']:
                        results['opportunities'][symbol] = symbol_results
                        self._categorize_opportunity(symbol_results, results['by_category'])
                        
                        # Print progress
                        best = symbol_results['best_opportunity']
                        print(f"  ✅ {symbol}: Score {best['total_score']:.1f} - {best['recommendation']}")
                        
                except Exception as e:
                    print(f"  ❌ {symbol}: Error - {str(e)}")
        
        # Generate top picks
        results['top_picks'] = self._generate_top_picks(results['opportunities'])
        
        # Save results
        self._save_scan_results(results)
        
        # Generate summary
        results['summary'] = self._generate_scan_summary(results)
        
        print("\n" + results['summary'])
        
        return results
    
    def _scan_symbol(self, symbol: str, scan_type: str, filters: Dict = None) -> Optional[Dict]:
        """
        Scan a single symbol for explosive opportunities
        """
        try:
            # Get market data
            market_data = self._fetch_enhanced_market_data(symbol)
            if not market_data:
                return None
            
            # Get options chains
            options_data = self._fetch_all_options(symbol)
            if options_data is None or options_data.empty:
                return None
            
            # Apply initial filters
            if filters:
                options_data = self._apply_filters(options_data, filters)
                if options_data.empty:
                    return None
            
            # Score all options
            scored_options = []
            for idx, option in options_data.iterrows():
                score, analysis = self.grader.calculate_option_score(option.to_dict(), market_data)
                
                if score >= self.scan_config['min_score']:
                    option_dict = option.to_dict()
                    option_dict['score_analysis'] = analysis
                    option_dict['total_score'] = score
                    scored_options.append(option_dict)
            
            if not scored_options:
                return None
            
            # Sort by score
            scored_options.sort(key=lambda x: x['total_score'], reverse=True)
            
            # Get best opportunity
            best_option = scored_options[0]
            
            # Generate intelligent plan for best option
            plan = self.planner.generate_intelligent_plan(
                best_option,
                best_option['score_analysis'],
                market_data
            )
            
            # Package results
            return {
                'symbol': symbol,
                'market_data': market_data,
                'best_opportunity': best_option,
                'trading_plan': plan,
                'other_opportunities': scored_options[1:5],  # Top 5
                'scan_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            return None
    
    def monitor_active_positions(self) -> Dict:
        """
        Monitor all active positions and generate alerts
        """
        print(f"\n📡 MONITORING ACTIVE POSITIONS - {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        
        monitoring_results = {
            'timestamp': datetime.now().isoformat(),
            'positions_monitored': 0,
            'alerts': [],
            'exit_signals': [],
            'adjustments': []
        }
        
        # Get active positions from tracker
        active_positions = self._get_active_positions()
        
        for position_id, position_data in active_positions.items():
            print(f"\n📊 Monitoring {position_id}...")
            monitoring_results['positions_monitored'] += 1
        
        # Generate summary actions
        monitoring_results['summary_actions'] = self._generate_summary_actions(monitoring_results)
        
        # Save monitoring results
        self._save_monitoring_results(monitoring_results)
        
        return monitoring_results
    
    def _discover_symbols(self, scan_type: str) -> List[str]:
        """
        Discover symbols based on scan type
        """
        symbols = []
        
        if scan_type == 'earnings':
            # Get pre-earnings stocks
            symbols = self._get_pre_earnings_stocks()
        
        elif scan_type == 'unusual_activity':
            # Get stocks with unusual options activity
            symbols = self._get_unusual_activity_stocks()
        
        elif scan_type == 'quick':
            # Get top movers and high volume stocks
            symbols = self._get_top_movers()[:50]
        
        else:  # comprehensive
            # Combine multiple sources
            earnings = self._get_pre_earnings_stocks()[:30]
            movers = self._get_top_movers()[:30]
            unusual = self._get_unusual_activity_stocks()[:20]
            
            # Combine and dedupe
            all_symbols = list(set(earnings + movers + unusual))
            symbols = all_symbols
        
        # Always include focus list
        if self.scan_config['focus_list']:
            symbols = self.scan_config['focus_list'] + [s for s in symbols if s not in self.scan_config['focus_list']]
        
        return symbols[:100]  # Cap at 100 for performance
    
    def _get_pre_earnings_stocks(self) -> List[str]:
        """Get stocks with upcoming earnings"""
        try:
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)
            
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return []
            
            headers = lines[0].split(',')
            symbol_idx = headers.index('symbol') if 'symbol' in headers else 0
            date_idx = headers.index('reportDate') if 'reportDate' in headers else 1
            
            current_date = datetime.now().date()
            earnings_stocks = []
            
            for line in lines[1:]:
                try:
                    fields = line.split(',')
                    symbol = fields[symbol_idx].strip().strip('"')
                    earnings_date_str = fields[date_idx].strip().strip('"')
                    
                    if symbol and earnings_date_str:
                        earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d').date()
                        days_to_earnings = (earnings_date - current_date).days
                        
                        if 0 <= days_to_earnings <= 21:
                            earnings_stocks.append(symbol)
                except:
                    continue
            
            return earnings_stocks
            
        except:
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # Fallback
    
    def _get_top_movers(self) -> List[str]:
        """Get top gainers, losers, and most active"""
        try:
            url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={self.av_key}'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            all_symbols = []
            for category in ['top_gainers', 'top_losers', 'most_actively_traded']:
                if category in data:
                    symbols = [item['ticker'] for item in data[category]]
                    all_symbols.extend(symbols)
            
            return list(set(all_symbols))
            
        except:
            # Fallback to high-volume stocks
            return ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN']
    
    def _get_unusual_activity_stocks(self) -> List[str]:
        """Get stocks with unusual options activity"""
        # This would integrate with options flow data
        # For now, return stocks known for options activity
        return ['TSLA', 'NVDA', 'AMD', 'SPY', 'QQQ', 'AAPL', 'GME', 'AMC']
    
    def _fetch_enhanced_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch comprehensive market data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return None
            
            # Calculate metrics
            current_price = hist['Close'].iloc[-1]
            volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100
            
            # Get earnings info
            earnings_date = info.get('earningsDate')
            earnings_info = {
                'is_pre_earnings': False,
                'days_to_earnings': None
            }
            
            if earnings_date:
                if isinstance(earnings_date, list):
                    earnings_date = earnings_date[0]
                days_to_earnings = (pd.to_datetime(earnings_date) - datetime.now()).days
                earnings_info = {
                    'is_pre_earnings': 0 <= days_to_earnings <= 21,
                    'days_to_earnings': days_to_earnings,
                    'earnings_priority': 'high' if days_to_earnings <= 7 else 'medium'
                }
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'volatility_30d': volatility,
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown'),
                'beta': info.get('beta', 1.0),
                'earnings_info': earnings_info,
                'volume_avg': info.get('averageVolume', 0)
            }
            
        except:
            return None
    
    def _fetch_all_options(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch all options for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            
            if not expirations:
                return None
            
            all_options = []
            
            # Limit to next 3 expirations for speed
            for exp_date in expirations[:3]:
                try:
                    options = ticker.option_chain(exp_date)
                    
                    # Process calls
                    if not options.calls.empty:
                        calls = options.calls.copy()
                        calls['type'] = 'call'
                        calls['expiration'] = exp_date
                        calls['symbol'] = symbol
                        all_options.append(calls)
                    
                    # Process puts
                    if not options.puts.empty:
                        puts = options.puts.copy()
                        puts['type'] = 'put'
                        puts['expiration'] = exp_date
                        puts['symbol'] = symbol
                        all_options.append(puts)
                    
                except Exception as e:
                    print(f"Error fetching options for {symbol} {exp_date}: {e}")
                    continue
            
            if all_options:
                combined = pd.concat(all_options, ignore_index=True)
                
                # Standardize columns - handle missing columns gracefully
                if 'lastPrice' in combined.columns:
                    combined['mark'] = combined['lastPrice']
                elif 'ask' in combined.columns and 'bid' in combined.columns:
                    combined['mark'] = (combined['ask'] + combined['bid']) / 2
                else:
                    combined['mark'] = 0.5  # Default fallback
                
                # Add days to expiration
                combined['days_to_expiry'] = (pd.to_datetime(combined['expiration']) - datetime.now()).dt.days
                
                # Ensure required columns exist
                required_columns = ['volume', 'openInterest', 'delta', 'gamma', 'theta', 'impliedVolatility']
                for col in required_columns:
                    if col not in combined.columns:
                        combined[col] = 0  # Default value
                
                # Standardize column names
                if 'openInterest' in combined.columns:
                    combined['open_interest'] = combined['openInterest']
                if 'impliedVolatility' in combined.columns:
                    combined['implied_volatility'] = combined['impliedVolatility']
                
                return combined
            
            return None
            
        except Exception as e:
            print(f"Error fetching options for {symbol}: {e}")
            return None
    
    def _apply_filters(self, options_data: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply filters to options data"""
        if options_data is None or options_data.empty:
            return pd.DataFrame()
            
        filtered = options_data.copy()
        
        # Price filters
        if 'min_price' in filters and 'mark' in filtered.columns:
            filtered = filtered[filtered['mark'] >= filters['min_price']]
        if 'max_price' in filters and 'mark' in filtered.columns:
            filtered = filtered[filtered['mark'] <= filters['max_price']]
        
        # Delta filters
        if 'min_delta' in filters and 'delta' in filtered.columns:
            filtered = filtered[filtered['delta'].abs() >= filters['min_delta']]
        if 'max_delta' in filters and 'delta' in filtered.columns:
            filtered = filtered[filtered['delta'].abs() <= filters['max_delta']]
        
        # Days to expiry
        if 'min_days' in filters and 'days_to_expiry' in filtered.columns:
            filtered = filtered[filtered['days_to_expiry'] >= filters['min_days']]
        if 'max_days' in filters and 'days_to_expiry' in filtered.columns:
            filtered = filtered[filtered['days_to_expiry'] <= filters['max_days']]
        
        # Volume filter
        if 'min_volume' in filters and 'volume' in filtered.columns:
            filtered = filtered[filtered['volume'] >= filters['min_volume']]
        
        return filtered
    
    def _categorize_opportunity(self, symbol_results: Dict, categories: Dict):
        """Categorize opportunity by type"""
        best = symbol_results['best_opportunity']
        score_components = best['score_analysis']['components']
        
        # Earnings play
        if symbol_results['market_data'].get('earnings_info', {}).get('is_pre_earnings'):
            categories['earnings_plays'].append({
                'symbol': symbol_results['symbol'],
                'days_to_earnings': symbol_results['market_data']['earnings_info']['days_to_earnings'],
                'score': best['total_score']
            })
        
        # Unusual activity
        if score_components.get('unusual_activity_score', 0) >= 18:
            categories['unusual_activity'].append({
                'symbol': symbol_results['symbol'],
                'activity_score': score_components['unusual_activity_score'],
                'total_score': best['total_score']
            })
        
        # Technical setup
        if score_components.get('technical_score', 0) >= 12:
            categories['technical_setups'].append({
                'symbol': symbol_results['symbol'],
                'technical_score': score_components['technical_score'],
                'total_score': best['total_score']
            })
        
        # Volatility play
        if score_components.get('iv_opportunity_score', 0) >= 8:
            categories['volatility_plays'].append({
                'symbol': symbol_results['symbol'],
                'iv_score': score_components['iv_opportunity_score'],
                'total_score': best['total_score']
            })
    
    def _generate_top_picks(self, opportunities: Dict) -> List[Dict]:
        """Generate top picks from all opportunities"""
        # Sort all opportunities by score
        all_opps = []
        for symbol, data in opportunities.items():
            best = data['best_opportunity']
            plan = data['trading_plan']
            
            all_opps.append({
                'symbol': symbol,
                'option': f"{symbol} {best['strike']} {best['type'].upper()}",
                'expiration': best['expiration'],
                'score': best['total_score'],
                'confidence': best['score_analysis']['confidence'],
                'entry_price': best['mark'],
                'target_1': plan['targets']['target_1']['price'],
                'stop_loss': plan['stop_loss']['stop_price'],
                'recommendation': best['score_analysis']['recommendation'],
                'formatted_plan': plan['formatted_text']
            })
        
        # Sort by score
        all_opps.sort(key=lambda x: x['score'], reverse=True)
        
        return all_opps[:10]  # Top 10
    
    def _generate_scan_summary(self, results: Dict) -> str:
        """Generate human-readable scan summary"""
        summary = f"""
📊 EXPLOSIVE OPTIONS SCAN SUMMARY
{'='*50}
Scan Time: {results['scan_metadata']['timestamp']}
Symbols Scanned: {results['scan_metadata']['symbols_scanned']}
Opportunities Found: {len(results['opportunities'])}

🏆 TOP 3 EXPLOSIVE PICKS:
"""
        
        for i, pick in enumerate(results['top_picks'][:3], 1):
            summary += f"""
{i}. {pick['option']} @ ${pick['entry_price']:.2f}
   Score: {pick['score']:.1f}/100 | Confidence: {pick['confidence']}%
   Target: ${pick['target_1']:.2f} (+{((pick['target_1']/pick['entry_price'])-1)*100:.1f}%)
   Stop: ${pick['stop_loss']:.2f} ({((pick['stop_loss']/pick['entry_price'])-1)*100:.1f}%)
   {pick['recommendation']}
"""
        
        # Category summary
        summary += f"\n📈 OPPORTUNITIES BY CATEGORY:\n"
        for category, items in results['by_category'].items():
            if items:
                summary += f"• {category.replace('_', ' ').title()}: {len(items)} found\n"
        
        return summary
    
    def _adapt_from_history(self):
        """Adapt scanner based on historical performance"""
        try:
            # Load performance data
            perf_data = self.tracker.load_performance_data()
            
            if perf_data:
                # Adapt grader thresholds
                self.grader.adapt_thresholds(perf_data)
                
        except Exception as e:
            print(f"Could not adapt from history: {e}")
    
    def _get_active_positions(self) -> Dict:
        """Get active positions from tracker"""
        # This would integrate with your position tracking
        # For now, return empty dict
        return {}
    
    def _generate_summary_actions(self, monitoring_results: Dict) -> List[str]:
        """Generate summary actions from monitoring results"""
        actions = []
        
        # Critical exit signals
        critical_exits = [s for s in monitoring_results['exit_signals'] 
                         if s.get('urgency') == 'CRITICAL']
        if critical_exits:
            actions.append(f"🚨 IMMEDIATE ACTION: {len(critical_exits)} positions require immediate exit")
        
        # High priority alerts
        high_alerts = [a for a in monitoring_results['alerts']
                      if a.get('severity') == 'HIGH']
        if high_alerts:
            actions.append(f"⚠️ HIGH PRIORITY: {len(high_alerts)} positions have high-severity alerts")
        
        return actions
    
    def _save_scan_results(self, results: Dict):
        """Save scan results to file"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        
        filename = os.path.join(self.base_dir, f'explosive_scan_{date_str}_{timestamp}.json')
        
        # Convert numpy types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            return obj
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=convert_types)
        
        print(f"💾 Results saved to {filename}")
    
    def _save_monitoring_results(self, results: Dict):
        """Save monitoring results"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        
        filename = os.path.join(self.base_dir, f'monitoring_{date_str}_{timestamp}.json')
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
