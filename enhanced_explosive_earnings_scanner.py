
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import yfinance as yf
import time
from scanner_core import get_optionable_stocks_with_volume
from explosive_options_scanner import ExplosiveOptionsScanner
from enhanced_scanner import discover_pre_earnings_stocks

class EnhancedEarningsScanner:
    """Enhanced earnings scanner for discovering pre-earnings opportunities"""
    
    def __init__(self, alpha_vantage_key: str):
        self.av_key = alpha_vantage_key
        
    def _fetch_real_earnings_calendar(self, days_ahead: int = 21) -> Dict[str, Dict]:
        """Fetch real earnings calendar from Alpha Vantage"""
        try:
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)
            
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return {}
                
            headers = lines[0].split(',')
            symbol_idx = headers.index('symbol') if 'symbol' in headers else 0
            date_idx = headers.index('reportDate') if 'reportDate' in headers else 1
            
            current_date = datetime.now().date()
            earnings_stocks = {}
            
            for line in lines[1:]:
                try:
                    fields = line.split(',')
                    if len(fields) < max(symbol_idx + 1, date_idx + 1):
                        continue
                        
                    symbol = fields[symbol_idx].strip().strip('"')
                    earnings_date_str = fields[date_idx].strip().strip('"')
                    
                    if symbol and earnings_date_str:
                        earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d').date()
                        days_to_earnings = (earnings_date - current_date).days
                        
                        if 0 <= days_to_earnings <= days_ahead:
                            earnings_stocks[symbol] = {
                                'earnings_date': earnings_date_str,
                                'days_to_earnings': days_to_earnings
                            }
                            
                except Exception:
                    continue
                    
            return earnings_stocks
            
        except Exception as e:
            print(f"Error fetching earnings calendar: {e}")
            return {}
    
    def _detect_volume_surges(self, min_surge_ratio: float = 1.5) -> Dict[str, Dict]:
        """Detect stocks with volume surges"""
        try:
            # Get top movers from Alpha Vantage
            url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={self.av_key}'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            volume_surges = {}
            
            for category in ['top_gainers', 'top_losers', 'most_actively_traded']:
                if category in data:
                    for item in data[category]:
                        symbol = item['ticker']
                        volume = float(item.get('volume', 0))
                        price = float(item.get('price', 0))
                        change_percent = float(item.get('change_percentage', '0%').replace('%', ''))
                        
                        # Estimate volume surge (simplified)
                        avg_volume = volume / max(abs(change_percent) / 10, 1)  # Rough estimate
                        surge_ratio = volume / max(avg_volume, 1)
                        
                        if surge_ratio >= min_surge_ratio:
                            volume_surges[symbol] = {
                                'current_volume': volume,
                                'avg_volume': avg_volume,
                                'surge_ratio': surge_ratio,
                                'price': price,
                                'change_percent': change_percent
                            }
            
            return volume_surges
            
        except Exception as e:
            print(f"Error detecting volume surges: {e}")
            return {}
    
    def _get_intraday_movers(self) -> Dict[str, Dict]:
        """Get intraday moving stocks"""
        try:
            url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={self.av_key}'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            movers = {}
            
            for category in ['top_gainers', 'top_losers']:
                if category in data:
                    for item in data[category][:10]:  # Top 10 each
                        symbol = item['ticker']
                        movers[symbol] = {
                            'price': float(item.get('price', 0)),
                            'change_percent': float(item.get('change_percentage', '0%').replace('%', '')),
                            'volume': float(item.get('volume', 0)),
                            'category': category
                        }
            
            return movers
            
        except Exception:
            return {}

class EnhancedOptionsEvaluator:
    """Enhanced options evaluator for earnings plays"""
    
    def __init__(self, alpha_vantage_key: str):
        self.av_key = alpha_vantage_key
        self.scanner = ExplosiveOptionsScanner(alpha_vantage_key)
    
    def evaluate_options_for_symbol(self, symbol: str, filters: Dict) -> Optional[Dict]:
        """Evaluate options for a specific symbol"""
        try:
            # Get market data
            market_data = self.scanner._fetch_enhanced_market_data(symbol)
            if not market_data:
                return None
            
            # Get options data
            options_data = self.scanner._fetch_all_options(symbol)
            if options_data is None or options_data.empty:
                return None
            
            # Apply filters
            filtered_options = self.scanner._apply_filters(options_data, filters)
            if filtered_options.empty:
                return None
            
            # Score options
            best_option = None
            best_score = 0
            
            for idx, option in filtered_options.iterrows():
                try:
                    option_dict = option.to_dict() if hasattr(option, 'to_dict') else dict(option)
                    score, analysis = self.scanner.grader.calculate_option_score(option_dict, market_data)
                    
                    if isinstance(score, dict):
                        score = score.get('total_score', 0)
                    
                    if score > best_score:
                        best_score = score
                        best_option = option_dict
                        best_option['explosion_score'] = score
                        best_option['analysis'] = analysis
                
                except Exception as e:
                    continue
            
            if best_option:
                # Generate trade plan
                trade_plan = self.scanner.planner.generate_intelligent_plan(
                    best_option, best_option.get('analysis', {}), market_data
                )
                
                return {
                    'symbol': symbol,
                    'option': best_option,
                    'trade_plan': trade_plan,
                    'market_data': market_data
                }
            
            return None
            
        except Exception as e:
            print(f"Error evaluating options for {symbol}: {e}")
            return None

def enhanced_explosive_earnings_combo(request_data: Dict) -> Dict:
    """Enhanced explosive earnings combo scanner"""
    try:
        print("🚀 ENHANCED EXPLOSIVE EARNINGS COMBO SCANNER")
        print("=" * 60)
        
        # Initialize scanners
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        earnings_scanner = EnhancedEarningsScanner(api_key)
        options_evaluator = EnhancedOptionsEvaluator(api_key)
        
        # Get parameters
        days_ahead = request_data.get('days_ahead', 21)
        min_volume_surge = request_data.get('min_volume_surge', 1.5)
        min_avg_volume = request_data.get('min_avg_volume', 1000000)
        
        # Option filters
        filters = {
            'min_delta': request_data.get('min_delta', 0.15),
            'max_delta': request_data.get('max_delta', 0.45),
            'min_price': request_data.get('min_price', 0.05),
            'max_price': request_data.get('max_price', 5.00),
            'min_days': request_data.get('min_days', 1),
            'max_days': request_data.get('max_days', 30)
        }
        
        print(f"📊 Stock Discovery - Days ahead: {days_ahead}, Min volume surge: {min_volume_surge}x")
        print(f"⚡ Option Filters - Delta: {filters['min_delta']}-{filters['max_delta']}, Price: ${filters['min_price']}-${filters['max_price']}")
        
        # Phase 1: Discover explosive stocks
        earnings_stocks = earnings_scanner._fetch_real_earnings_calendar(days_ahead)
        volume_surges = earnings_scanner._detect_volume_surges(min_volume_surge)
        intraday_movers = earnings_scanner._get_intraday_movers()
        
        # Combine and prioritize stocks
        all_explosive_stocks = {}
        
        # Add earnings stocks (highest priority)
        for symbol, data in earnings_stocks.items():
            if symbol not in all_explosive_stocks:
                all_explosive_stocks[symbol] = {
                    'sources': ['earnings'],
                    'earnings_data': data,
                    'priority_score': 100 - data['days_to_earnings']  # Closer = higher priority
                }
        
        # Add volume surges
        for symbol, data in volume_surges.items():
            if data['current_volume'] >= min_avg_volume:
                if symbol in all_explosive_stocks:
                    all_explosive_stocks[symbol]['sources'].append('volume_surge')
                    all_explosive_stocks[symbol]['volume_data'] = data
                    all_explosive_stocks[symbol]['priority_score'] += data['surge_ratio'] * 10
                else:
                    all_explosive_stocks[symbol] = {
                        'sources': ['volume_surge'],
                        'volume_data': data,
                        'priority_score': data['surge_ratio'] * 10
                    }
        
        # Add intraday movers
        for symbol, data in intraday_movers.items():
            if symbol in all_explosive_stocks:
                all_explosive_stocks[symbol]['sources'].append('intraday_mover')
                all_explosive_stocks[symbol]['mover_data'] = data
                all_explosive_stocks[symbol]['priority_score'] += abs(data['change_percent'])
            else:
                all_explosive_stocks[symbol] = {
                    'sources': ['intraday_mover'],
                    'mover_data': data,
                    'priority_score': abs(data['change_percent'])
                }
        
        # Sort by priority
        sorted_symbols = sorted(all_explosive_stocks.items(), 
                               key=lambda x: x[1]['priority_score'], reverse=True)
        
        print(f"🔥 Phase 1 Complete: {len(all_explosive_stocks)} explosive stocks identified")
        
        # Phase 2: Evaluate options for top candidates
        top_opportunities = []
        symbols_to_analyze = [symbol for symbol, _ in sorted_symbols[:50]]  # Top 50
        
        print(f"⚡ Phase 2: Analyzing options for top {len(symbols_to_analyze)} candidates...")
        
        for i, symbol in enumerate(symbols_to_analyze):
            try:
                print(f"📊 [{i+1}/{len(symbols_to_analyze)}] Analyzing {symbol}...")
                
                result = options_evaluator.evaluate_options_for_symbol(symbol, filters)
                if result:
                    # Add explosive stock data
                    result['explosive_analysis'] = all_explosive_stocks[symbol]
                    top_opportunities.append(result)
                    
                    score = result['option'].get('explosion_score', 0)
                    print(f"✅ {symbol}: Found opportunity with score {score:.1f}")
                else:
                    print(f"⚠️ {symbol}: No suitable options found")
                
                # Rate limiting
                if i % 10 == 0 and i > 0:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ {symbol}: Error - {str(e)}")
                continue
        
        # Sort opportunities by combined score
        top_opportunities.sort(key=lambda x: x['option'].get('explosion_score', 0), reverse=True)
        
        # Generate results
        results = {
            'status': 'success',
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'scan_type': 'enhanced_explosive_earnings_combo',
                'phase_1_stocks': len(all_explosive_stocks),
                'phase_2_analyzed': len(symbols_to_analyze),
                'opportunities_found': len(top_opportunities),
                'filters': filters
            },
            'explosive_stocks': [{'symbol': k, **v} for k, v in sorted_symbols[:20]],
            'top_opportunities': top_opportunities[:10],
            'summary': f"Found {len(top_opportunities)} explosive options opportunities from {len(all_explosive_stocks)} explosive stocks"
        }
        
        if not top_opportunities:
            results['status'] = 'no_opportunities'
            results['message'] = 'No suitable options found meeting criteria'
        
        print(f"✅ Enhanced Explosive Earnings Combo Complete!")
        print(f"📊 {len(all_explosive_stocks)} explosive stocks → {len(top_opportunities)} option opportunities")
        
        return results
        
    except Exception as e:
        print(f"❌ Enhanced explosive earnings combo failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'scan_type': 'enhanced_explosive_earnings_combo'
            }
        }
