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

from immediate_fixes import safe_apply_filters, process_alpha_vantage_bulk_response, fix_options_dataframe

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

        # Scan configuration optimized for your API plan
        self.scan_config = {
            'min_score': 35,  # Slightly higher to focus on best opportunities  
            'max_positions': 10,  # Max concurrent positions
            'scan_frequency': 'continuous',  # or 'daily', 'hourly'
            'focus_list': [],  # Symbols to prioritize
            'use_yahoo_fallback': True,  # Enable Yahoo Finance fallback
            'max_symbols_per_scan': 600,  # Optimize for your API limits
            'historical_options_preferred': True  # Prefer Alpha Vantage historical
        }

        # Results cache
        self.scan_results = {}
        self.last_scan_time = None

        # API usage tracking for your 150/minute limit
        self.api_calls_made = 0
        self.api_window_start = time.time()
        self.max_calls_per_minute = 150

    def _track_api_call(self):
        """Track API calls to stay within 150/minute limit"""
        current_time = time.time()

        # Reset counter if more than a minute has passed
        if current_time - self.api_window_start >= 60:
            self.api_calls_made = 0
            self.api_window_start = current_time

        self.api_calls_made += 1

        # If approaching limit, wait
        if self.api_calls_made >= self.max_calls_per_minute - 5:  # Leave buffer
            wait_time = 60 - (current_time - self.api_window_start) + 1
            if wait_time > 0:
                print(f"⏳ API rate limit protection: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self.api_calls_made = 0
                self.api_window_start = time.time()



    def run_explosive_scan(self,
                          symbols: List[str] = None,
                          scan_type: str = 'comprehensive',
                          filters: Dict = None,
                          market_data: Dict[str, Dict] = None) -> Dict:
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

        # STEP 1: Use provided market data or fetch via API
        self._bulk_market_cache = {}
        if market_data:
            self._bulk_market_cache.update({k.upper(): v for k, v in market_data.items()})
            print(f"📊 Using supplied market data for {len(self._bulk_market_cache)} symbols")

        remaining = [s for s in symbols if s not in self._bulk_market_cache]
        if remaining:
            print("📊 Fetching bulk market data using REALTIME_BULK_QUOTES API...")
            fetched = self._fetch_bulk_market_data(remaining)
            self._bulk_market_cache.update(fetched)

        # Filter symbols that have valid market data
        valid_symbols = [s for s in symbols if s in self._bulk_market_cache]
        print(f"✅ {len(valid_symbols)} symbols have valid market data")

        # Initialize results
        results = {
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'scan_type': scan_type,
                'symbols_scanned': len(valid_symbols),
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

        # Process symbols in parallel (now with cached market data)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_symbol = {}

            for symbol in valid_symbols:
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
                        rec = best.get('recommendation',
                                      best.get('score_analysis', {}).get('recommendation', 'N/A'))
                        print(
                            f"  ✅ {symbol}: Score {best['total_score']:.1f} - {rec}"
                        )

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
            if options_data is None or (hasattr(options_data, 'empty') and options_data.empty):
                return None

            # Fix data types first
            options_data = fix_options_dataframe(options_data)

            # Apply initial filters
            if filters:
                options_data = self._apply_filters(options_data, filters)
                if hasattr(options_data, 'empty') and options_data.empty:
                    return None

            # Score all options with better error handling
            scored_options = []
            if hasattr(options_data, 'iterrows'):
                for idx, option in options_data.iterrows():
                    try:
                        option_dict = option.to_dict()

                        # Ensure all required fields are present and properly typed
                        required_fields = ['strike', 'expiration', 'type', 'delta', 'gamma', 'theta', 'volume', 'mark', 'open_interest']
                        for field in required_fields:
                            if field not in option_dict or pd.isna(option_dict[field]):
                                if field == 'strike':
                                    option_dict[field] = 100.0
                                elif field == 'expiration':
                                    option_dict[field] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                                elif field == 'type':
                                    option_dict[field] = 'call'
                                elif field == 'delta':
                                    option_dict[field] = 0.3
                                elif field == 'gamma':
                                    option_dict[field] = 0.01
                                elif field == 'theta':
                                    option_dict[field] = -0.05
                                elif field == 'volume':
                                    option_dict[field] = 100
                                elif field == 'mark':
                                    option_dict[field] = 0.5
                                elif field == 'open_interest':
                                    option_dict[field] = 50

                        # Convert numeric fields to float with comprehensive error handling
                        numeric_fields = ['strike', 'delta', 'gamma', 'theta', 'volume', 'mark', 'open_interest']
                        for field in numeric_fields:
                            try:
                                val = option_dict[field]
                                # Handle string values that might contain non-numeric chars
                                if val is None or pd.isna(val):
                                    raise ValueError("None or NaN value")

                                import re
                                cleaned_val = re.sub(r'[^\d\.\-]', '', str(val))
                                if cleaned_val and cleaned_val != '-':
                                    option_dict[field] = float(cleaned_val)
                                else:
                                    raise ValueError("Empty after cleaning")
                            except (ValueError, TypeError, AttributeError):
                                # Set safe defaults for failed conversions
                                if field == 'strike':
                                    option_dict[field] = 100.0
                                elif field == 'delta':
                                    option_dict[field] = 0.3
                                elif field == 'gamma':
                                    option_dict[field] = 0.01
                                elif field == 'theta':
                                    option_dict[field] = -0.05
                                elif field == 'volume':
                                    option_dict[field] = 100.0
                                elif field == 'mark':
                                    option_dict[field] = 0.5
                                elif field == 'open_interest':
                                    option_dict[field] = 50.0

                        # Ensure expiration is properly formatted as string
                        if 'expiration' in option_dict:
                            exp_val = option_dict['expiration']
                            if pd.isna(exp_val) or exp_val == '' or exp_val is None:
                                option_dict['expiration'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                            else:
                                # Standardize expiration format
                                try:
                                    if hasattr(exp_val, 'strftime'):
                                        option_dict['expiration'] = exp_val.strftime('%Y-%m-%d')
                                    else:
                                        exp_str = str(exp_val).strip()
                                        # Try different formats
                                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                                            try:
                                                parsed_date = datetime.strptime(exp_str, fmt)
                                                option_dict['expiration'] = parsed_date.strftime('%Y-%m-%d')
                                                break
                                            except ValueError:
                                                continue
                                        else:
                                            # If no format works, default to 30 days from now
                                            option_dict['expiration'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                                except:
                                    option_dict['expiration'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        score, analysis = self.grader.calculate_option_score(option_dict, market_data)

                        if score >= self.scan_config['min_score']:
                            option_dict['score_analysis'] = analysis
                            option_dict['total_score'] = score
                            
                            # Ensure recommendation exists in analysis
                            if 'recommendation' not in analysis:
                                if score >= 70:
                                    analysis['recommendation'] = "🔥 STRONG BUY - High explosion potential"
                                elif score >= 60:
                                    analysis['recommendation'] = "✅ BUY - Good opportunity"
                                elif score >= 45:
                                    analysis['recommendation'] = "⚡ WATCH - Needs confirmation"
                                elif score >= 30:
                                    analysis['recommendation'] = "⚠️ WEAK - Better opportunities exist"
                                else:
                                    analysis['recommendation'] = "❌ REJECT - Does not meet criteria"
                            
                            scored_options.append(option_dict)
                    except Exception as e:
                        print(f"⚠️ Skipping option for {symbol}: {e}")
                        continue

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
            print(f"Error scanning {symbol}: {str(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
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
        Discover symbols efficiently using your upgraded Alpha Vantage plan
        """
        symbols = []

        if scan_type == 'earnings':
            # Get pre-earnings stocks (1 API call)
            symbols = self._get_pre_earnings_stocks()
            # Add high-volume liquid stocks as backup
            liquid_stocks = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD']
            symbols.extend([s for s in liquid_stocks if s not in symbols])

        elif scan_type == 'unusual_activity':
            # Focus on known active options symbols to save API calls
            symbols = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN', 'MSFT', 'GOOGL',
                      'GME', 'AMC', 'PLTR', 'COIN', 'SOXL', 'TQQQ', 'IWM', 'XLE', 'GLD', 'NFLX']

        elif scan_type == 'quick':
            # Get top movers (1 API call) but limit to 100 to stay efficient
            movers = self._get_top_movers()
            symbols = movers[:100]  # Limit for efficiency

        else:  # comprehensive
            print(f"📊 Running comprehensive scan with API optimization...")

            # Get earnings (1 API call)
            earnings = self._get_pre_earnings_stocks()
            print(f"📈 Earnings symbols found: {len(earnings)}")

            # Get top movers (1 API call) 
            movers = self._get_top_movers()
            print(f"📊 Top movers found: {len(movers)}")

            # Add high-volume optionable stocks (no API call needed)
            high_volume = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD', 
                          'NFLX', 'COIN', 'PLTR', 'GME', 'AMC', 'SOXL', 'TQQQ', 'IWM', 'XLE', 'GLD',
                          'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'PYPL', 'SQ', 'CRM', 'ORCL',
                          'DIS', 'UBER', 'LYFT', 'F', 'GM', 'BA', 'GE', 'XOM', 'CVX', 'KO', 'PEP']

            print(f"🔥 High-volume optionable stocks: {len(high_volume)}")

            # Combine and prioritize (earnings first, then movers, then high-volume)
            all_symbols = earnings.copy()
            all_symbols.extend([s for s in movers if s not in all_symbols])
            all_symbols.extend([s for s in high_volume if s not in all_symbols])

            # Limit total symbols to optimize API usage (bulk quotes can handle ~600-800 efficiently)
            symbols = all_symbols[:600]  # Balance between coverage and efficiency

        # Always include focus list first
        if self.scan_config['focus_list']:
            symbols = self.scan_config['focus_list'] + [s for s in symbols if s not in self.scan_config['focus_list']]

        # Filter out likely non-optionable symbols
        filtered_symbols = []
        for symbol in symbols:
            # Keep only likely optionable US stocks
            if (len(symbol) <= 4 and 
                symbol.isalpha() and 
                not any(char in symbol for char in ['.', '-']) and
                not symbol.endswith('F')):  # Avoid foreign stocks
                filtered_symbols.append(symbol)

        print(f"📊 Filtered from {len(symbols)} to {len(filtered_symbols)} quality optionable symbols")
        print(f"🎯 Optimized for your API limits: 2 discovery calls + efficient bulk processing")

        return filtered_symbols

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

            # Filter for quality US symbols only
            filtered_symbols = []
            for symbol in all_symbols:
                # Skip foreign/OTC symbols (> 4 chars, contains dots/dashes, ends with F)
                if (len(symbol) <= 4 and 
                    symbol.isalpha() and 
                    not symbol.endswith('F') and 
                    not any(char in symbol for char in ['.', '-'])):
                    filtered_symbols.append(symbol)

            return list(set(filtered_symbols))

        except:
            # Fallback to high-volume stocks
            return ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN']

    def _get_unusual_activity_stocks(self) -> List[str]:
        """Get stocks with unusual options activity"""
        # This would integrate with options flow data
        # For now, return stocks known for options activity
        return ['TSLA', 'NVDA', 'AMD', 'SPY', 'QQQ', 'AAPL', 'GME', 'AMC']

    def _fetch_bulk_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch market data efficiently using your upgraded Alpha Vantage plan"""
        bulk_data = {}

        print(f"📊 Processing {len(symbols)} symbols using REALTIME_BULK_QUOTES API...")
        print(f"🔑 Using API key: {self.av_key[:8]}...{self.av_key[-4:] if len(self.av_key) > 12 else 'INVALID'}")
        print(f"⚡ Rate limit: 150 requests/minute (upgraded plan)")

        # Process symbols in chunks of 100 (API limit) with optimized timing
        chunk_delay = 0.4  # 150 requests/min = 1 request every 0.4 seconds

        for i in range(0, len(symbols), 100):
            chunk = symbols[i:i+100]
            print(f"📊 Processing chunk {i//100 + 1}: symbols {i+1}-{min(i+100, len(symbols))}")
            symbol_string = ','.join(chunk)

            try:
                start_time = time.time()

                url = f'https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol={symbol_string}&apikey={self.av_key}'
                response = requests.get(url, timeout=30)
                data = response.json()

                print(f"📊 API Response Status: {response.status_code}")

                if 'Information' in data and 'rate limit' in data['Information'].lower():
                    print(f"⏳ Rate limit reached - waiting 60 seconds...")
                    time.sleep(60)
                    continue

                if 'Error Message' in data:
                    print(f"❌ Bulk quotes error: {data['Error Message']}")
                    continue

                if 'Information' in data and ('premium' in data.get('Information', '').lower() or 'upgrade' in data.get('Information', '').lower()):
                    print(f"❌ API access issue: {data['Information']}")
                    continue

                # Process successful response
                parsed = process_alpha_vantage_bulk_response(data)
                bulk_data.update(parsed)
                print(f"✅ Successfully parsed {len(parsed)} symbols from chunk {i//100 + 1}")

                # Rate limiting - ensure we don't exceed 150 requests/minute
                elapsed = time.time() - start_time
                if elapsed < chunk_delay and i + 100 < len(symbols):
                    sleep_time = chunk_delay - elapsed
                    print(f"⏱️ Rate limiting: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"❌ Error fetching bulk data for chunk {i//100 + 1}: {e}")
                continue

        print(f"✅ Successfully fetched bulk data for {len(bulk_data)} symbols")
        return bulk_data

    def _fetch_enhanced_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch comprehensive market data for a symbol using cached bulk data or individual call"""
        try:
            # Check if we have cached bulk data for this symbol
            if hasattr(self, '_bulk_market_cache') and symbol in self._bulk_market_cache:
                base_data = self._bulk_market_cache[symbol]

                # Calculate volatility from price changes
                change_percent = abs(base_data.get('change_percent', 0))
                volatility = max(change_percent * 10, 25.0)  # Estimate volatility

                # Get earnings info
                earnings_info = self._get_earnings_info(symbol)

                return {
                    'symbol': symbol,
                    'current_price': base_data['current_price'],
                    'volatility_30d': volatility,
                    'market_cap': 0,  # Would need separate API call
                    'sector': 'Unknown',  # Would need separate API call
                    'beta': 1.0,  # Default
                    'earnings_info': earnings_info,
                    'volume_avg': base_data.get('volume', 0),
                    'change_percent': base_data.get('change_percent', 0),
                    'high': base_data.get('high', 0),
                    'low': base_data.get('low', 0)
                }

            # Fallback to individual API call if not in cache
            print(f"⚠️ Using individual API call for {symbol} (not in bulk cache)")

            # Fetch daily data from Alpha Vantage
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={self.av_key}'
            response = requests.get(url, timeout=15)
            data = response.json()

            if 'Information' in data and 'premium@alphavantage.co' in data['Information']:
                print(f"⏳ API quota exceeded for {symbol}")
                return None

            if 'Information' in data and 'rate limit' in data['Information'].lower():
                print(f"⏳ Rate limit reached for {symbol} - waiting...")
                time.sleep(60)
                return None

            if 'Error Message' in data:
                print(f"Alpha Vantage error for {symbol}: {data['Error Message']}")
                return None

            if 'Time Series (Daily)' not in data:
                return None

            # Parse price data
            price_data = data['Time Series (Daily)']
            if not price_data:
                return None

            # Get recent prices
            dates = sorted(price_data.keys(), reverse=True)
            latest_data = price_data[dates[0]]
            current_price = float(latest_data['4. close'])

            # Calculate 30-day volatility
            prices = []
            for date in dates[:30]:  # Last 30 days
                prices.append(float(price_data[date]['4. close']))

            if len(prices) > 1:
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns) * np.sqrt(252) * 100
            else:
                volatility = 25.0  # Default volatility

            # Get earnings info from Alpha Vantage earnings calendar
            earnings_info = self._get_earnings_info(symbol)

            return {
                'symbol': symbol,
                'current_price': current_price,
                'volatility_30d': volatility,
                'market_cap': 0,
                'sector': 'Unknown',
                'beta': 1.0,
                'earnings_info': earnings_info,
                'volume_avg': 0
            }

        except Exception as e:
            print(f"Error fetching market data for {symbol}: {e}")
            return None

    def _get_earnings_info(self, symbol: str) -> Dict:
        """Get earnings information from Alpha Vantage"""
        try:
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)

            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return {'is_pre_earnings': False, 'days_to_earnings': None}

            headers = lines[0].split(',')
            symbol_idx = headers.index('symbol') if 'symbol' in headers else 0
            date_idx = headers.index('reportDate') if 'reportDate' in headers else 1

            current_date = datetime.now().date()

            for line in lines[1:]:
                try:
                    fields = line.split(',')
                    earnings_symbol = fields[symbol_idx].strip().strip('"')
                    earnings_date_str = fields[date_idx].strip().strip('"')

                    if earnings_symbol == symbol and earnings_date_str:
                        earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d').date()
                        days_to_earnings = (earnings_date - current_date).days

                        return {
                            'is_pre_earnings': 0 <= days_to_earnings <= 21,
                            'days_to_earnings': days_to_earnings,
                            'earnings_priority': 'critical' if days_to_earnings <= 3 else 'high' if days_to_earnings <= 7 else 'medium'
                        }
                except:
                    continue

            return {'is_pre_earnings': False, 'days_to_earnings': None}

        except:
            return {'is_pre_earnings': False, 'days_to_earnings': None}

    def _fetch_all_options(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch options data using Alpha Vantage historical + Yahoo Finance realtime"""
        try:
            # FIRST: Try Alpha Vantage historical options (you have access)
            print(f"📊 Fetching Alpha Vantage historical options for {symbol}...")
            url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={self.av_key}"
            response = requests.get(url, timeout=15)
            data = response.json()

            if 'Information' in data and 'rate limit' in data['Information'].lower():
                print(f"⏳ Alpha Vantage rate limit - falling back to Yahoo Finance for {symbol}")
                return self._fetch_yahoo_options(symbol)

            if 'Error Message' in data:
                print(f"❌ Alpha Vantage historical options error for {symbol}: {data['Error Message']}")
                return self._fetch_yahoo_options(symbol)

            if 'data' in data and data['data'] and len(data['data']) > 0:
                print(f"✅ Alpha Vantage historical options found for {symbol}: {len(data['data'])} contracts")
                df = pd.DataFrame(data['data'])

                # Filter for recent data only (last 30 days)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    cutoff_date = datetime.now() - timedelta(days=30)
                    df = df[df['date'] >= cutoff_date]

                if not df.empty:
                    print(f"✅ Historical options data found for {symbol}: {len(df)} contracts")

                    # Standardize column names
                    column_mapping = {
                        'contractID': 'contractSymbol',
                        'underlying_symbol': 'symbol',
                        'option_type': 'type',
                        'strike_price': 'strike',
                        'expiration_date': 'expiration',
                        'last_price': 'mark',
                        'open_interest': 'open_interest',
                        'openInterest': 'open_interest',
                        'implied_volatility': 'impliedVolatility'
                    }

                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns:
                            df[new_col] = df[old_col]

                    # Add symbol if not present
                    if 'symbol' not in df.columns:
                        df['symbol'] = symbol

                    # Add days to expiration with error handling
                    if 'expiration' in df.columns:
                        try:
                            # Handle different date formats
                            def parse_expiration(exp_str):
                                if pd.isna(exp_str) or exp_str == '' or exp_str is None:
                                    return 30  # Default to 30 days

                                try:
                                    # Convert to string first
                                    exp_str = str(exp_str).strip()

                                    # Try different formats
                                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                                        try:
                                            exp_date = datetime.strptime(exp_str, fmt)
                                            days_diff = (exp_date - datetime.now()).days
                                            return max(1, days_diff)
                                        except ValueError:
                                            continue

                                    # If no format works, try to extract just the date part
                                    if ' ' in exp_str:
                                        date_part = exp_str.split(' ')[0]
                                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
                                            try:
                                                exp_date = datetime.strptime(date_part, fmt)
                                                days_diff = (exp_date - datetime.now()).days
                                                return max(1, days_diff)
                                            except ValueError:
                                                continue

                                    return 30  # Default if no format works
                                except Exception:
                                    return 30

                            df['days_to_expiry'] = df['expiration'].apply(parse_expiration)
                        except Exception as e:
                            print(f"Error calculating days to expiry: {e}")
                            df['days_to_expiry'] = 30  # Default fallback

                    # Ensure required columns exist with defaults and proper data types
                    required_columns = ['volume', 'openInterest', 'delta', 'gamma', 'theta', 'impliedVolatility', 'mark']
                    for col in required_columns:
                        if col not in df.columns:
                            if col == 'volume':
                                df[col] = 100  # Default volume
                            elif col == 'openInterest':
                                df[col] = 50   # Default OI
                            elif col == 'delta':
                                df[col] = 0.3  # Default delta
                            elif col == 'gamma':
                                df[col] = 0.01 # Default gamma
                            elif col == 'theta':
                                df[col] = -0.05 # Default theta
                            elif col == 'impliedVolatility':
                                df[col] = 0.25 # Default IV
                            elif col == 'mark':
                                df[col] = 0.5  # Default mark

                    # Fix expiration date format first - this is causing the main errors
                    if 'expiration' in df.columns:
                        def standardize_expiration(exp_val):
                            if pd.isna(exp_val) or exp_val == '' or exp_val is None:
                                return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                            exp_str = str(exp_val).strip()
                            if not exp_str:
                                return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                            # Try to parse and standardize the date
                            for fmt in [
                                '%Y-%m-%d',
                                '%m/%d/%Y',
                                '%Y-%m-%d %H:%M:%S',
                                '%m-%d-%Y',
                            ]:
                                try:
                                    parsed_date = datetime.strptime(exp_str, fmt)
                                    return parsed_date.strftime('%Y-%m-%d')
                                except ValueError:
                                    continue

                            # If no format works, default to 30 days from now
                            return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        df['expiration'] = df['expiration'].apply(standardize_expiration)

                    # Convert all numeric columns to proper types with comprehensive error handling
                    numeric_cols = ['mark', 'strike', 'volume', 'open_interest', 'delta', 'gamma', 'theta', 'impliedVolatility']
                    for col in numeric_cols:
                        if col in df.columns:
                            try:
                                # Convert to numeric, handling strings and other types
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                # Fill NaN values with appropriate defaults
                                if col == 'mark':
                                    df[col] = df[col].fillna(0.5)
                                elif col == 'strike':
                                    df[col] = df[col].fillna(100)
                                elif col in ['volume', 'open_interest']:
                                    df[col] = df[col].fillna(50)
                                elif col == 'delta':
                                    df[col] = df[col].fillna(0.3)
                                elif col == 'gamma':
                                    df[col] = df[col].fillna(0.01)
                                elif col == 'theta':
                                    df[col] = df[col].fillna(-0.05)
                                elif col == 'impliedVolatility':
                                    df[col] = df[col].fillna(0.25)
                                else:
                                    df[col] = df[col].fillna(0)
                            except Exception as e:
                                print(f"Error converting column {col}: {e}")
                                # Set default values if conversion fails
                                if col == 'mark':
                                    df[col] = 0.5
                                elif col == 'strike':
                                    df[col] = 100
                                elif col in ['volume', 'openInterest']:
                                    df[col] = 50
                                elif col == 'delta':
                                    df[col] = 0.3
                                elif col == 'gamma':
                                    df[col] = 0.01
                                elif col == 'theta':
                                    df[col] = -0.05
                                elif col == 'impliedVolatility':
                                    df[col] = 0.25
                                else:
                                    df[col] = 0

                    return df

            # Fallback to Yahoo Finance if no Alpha Vantage data
            print(f"🔄 No Alpha Vantage data - trying Yahoo Finance for {symbol}...")
            return self._fetch_yahoo_options(symbol)

        except Exception as e:
            print(f"❌ Error fetching Alpha Vantage options for {symbol}: {e}")
            print(f"🔄 Falling back to Yahoo Finance for {symbol}...")
            return self._fetch_yahoo_options(symbol)

    def _fetch_yahoo_options(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch options data from Yahoo Finance as fallback"""
        try:
            import yfinance as yf

            print(f"🌐 Fetching Yahoo Finance options for {symbol}...")
            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            try:
                expirations = ticker.options
                if not expirations:
                    print(f"❌ No options available for {symbol} on Yahoo Finance")
                    return None
            except Exception as e:
                print(f"❌ Error getting expiration dates for {symbol}: {e}")
                return None

            # Fetch options data for all available expirations (limit to first 4 for performance)
            all_options = []
            for exp_date in expirations[:4]:  # Limit to avoid too many calls
                try:
                    option_chain = ticker.option_chain(exp_date)

                    # Process calls
                    calls = option_chain.calls.copy()
                    calls['type'] = 'call'
                    calls['expiration'] = exp_date
                    calls['symbol'] = symbol

                    # Process puts  
                    puts = option_chain.puts.copy()
                    puts['type'] = 'put'
                    puts['expiration'] = exp_date
                    puts['symbol'] = symbol

                    all_options.extend([calls, puts])

                except Exception as e:
                    print(f"⚠️ Error fetching {exp_date} options for {symbol}: {e}")
                    continue

            if not all_options:
                print(f"❌ No valid options data found for {symbol}")
                return None

            # Combine all options data
            df = pd.concat(all_options, ignore_index=True)
            print(f"✅ Yahoo Finance options found for {symbol}: {len(df)} contracts")

                # Standardize Yahoo Finance columns to match Alpha Vantage format
            column_mapping = {
                'lastPrice': 'mark',
                'openInterest': 'open_interest', 
                'impliedVolatility': 'impliedVolatility',
                'contractSymbol': 'contractSymbol'
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df[new_col] = df[old_col]

            # Calculate mark price from bid/ask if lastPrice not available
            if 'mark' not in df.columns:
                if 'ask' in df.columns and 'bid' in df.columns:
                    df['ask'] = pd.to_numeric(df['ask'], errors='coerce').fillna(0.5)
                    df['bid'] = pd.to_numeric(df['bid'], errors='coerce').fillna(0.5)
                    df['mark'] = (df['ask'] + df['bid']) / 2
                else:
                    df['mark'] = 0.5

            # Add required columns with defaults if missing
            required_defaults = {
                'volume': 100,
                'open_interest': 50,
                'delta': 0.3,
                'gamma': 0.01, 
                'theta': -0.05,
                'impliedVolatility': 0.25
            }

            for col, default_val in required_defaults.items():
                if col not in df.columns:
                    df[col] = default_val

            # Standardize expiration format and calculate days to expiry
            def calculate_days_to_expiry(exp_str):
                try:
                    if pd.isna(exp_str):
                        return 30
                    exp_date = pd.to_datetime(exp_str)
                    days = max(1, (exp_date - pd.Timestamp.now()).days)
                    return days
                except:
                    return 30

            df['days_to_expiry'] = df['expiration'].apply(calculate_days_to_expiry)

            # Ensure expiration is in YYYY-MM-DD format
            df['expiration'] = pd.to_datetime(df['expiration']).dt.strftime('%Y-%m-%d')

            # Convert numeric columns with error handling
            numeric_cols = ['mark', 'strike', 'volume', 'open_interest', 'delta', 'gamma', 'theta', 'impliedVolatility']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                    # Fill NaN values with appropriate defaults
                    defaults_map = {
                        'mark': 0.5, 'strike': 100, 'volume': 50, 'open_interest': 50,
                        'delta': 0.3, 'gamma': 0.01, 'theta': -0.05, 'impliedVolatility': 0.25
                    }
                    df[col] = df[col].fillna(defaults_map.get(col, 0))

            return df

        except Exception as e:
            print(f"❌ Yahoo Finance options fetch failed for {symbol}: {e}")
            return None

    def _apply_filters(self, options_data: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply filters to options data using safe helpers"""
        if options_data is None or options_data.empty:
            return pd.DataFrame()

        return safe_apply_filters(
            options_data,
            min_price=filters.get('min_price', 0.01),
            max_price=filters.get('max_price', 10.0),
            min_delta=filters.get('min_delta', 0.0),
            max_delta=filters.get('max_delta', 1.0),
            min_volume=filters.get('min_volume', 0),
            min_days=filters.get('min_days', 0),
            max_days=filters.get('max_days', 365),
        )

    def _categorize_opportunity(self, symbol_results: Dict, categories: Dict):
        """Categorize opportunity by type"""
        best = symbol_results['best_opportunity']
        score_components = best.get('score_analysis', {}).get('components', {})

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
                'option': f"{symbol} {best['strike']} {best['type'].upper()} exp {best['expiration']}",
                'expiration': best['expiration'],
                'score': best['total_score'],
                'confidence': best.get('score_analysis', {}).get('confidence', 0),
                'entry_price': best['mark'],
                'target_1': plan['targets']['target_1']['price'],
                'stop_loss': plan['stop_loss']['stop_price'],
                'recommendation': best.get('score_analysis', {}).get('recommendation', 'N/A'),
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
    
    def _calculate_score_analysis(self, option_data: Dict, market_data: Dict) -> Dict:
        """
        Calculate a comprehensive score analysis based on various factors.
        """
        # Extract relevant data
        strike_price = option_data['strike']
        current_price = market_data['current_price']
        days_to_expiry = option_data['days_to_expiry']
        implied_volatility = option_data['impliedVolatility']
        delta = option_data['delta']
        gamma = option_data['gamma']
        theta = option_data['theta']
        volume = option_data['volume']
        open_interest = option_data['open_interest']

        # Initialize scores
        profitability_score = 0
        risk_score = 0
        volatility_score = 0
        technical_score = 0
        unusual_activity_score = 0
        iv_opportunity_score = 0

        # Profitability Score (Higher is better)
        # Closer to the money is better, especially slightly OTM
        distance_from_itm = abs(current_price - strike_price) / current_price
        if distance_from_itm <= 0.05:
            profitability_score += 20  # Very close to the money
        elif 0.05 < distance_from_itm <= 0.15:
            profitability_score += 15  # Slightly out of the money

        # Days to expiry sweet spot is between 14-45 days
        if 14 <= days_to_expiry <= 45:
            profitability_score += 15
        elif 7 <= days_to_expiry < 14 or 45 < days_to_expiry <= 60:
            profitability_score += 8

        # Delta near 0.5 is ideal
        profitability_score += max(0, 15 - abs(delta - 0.5) * 30)

        # Risk Score (Lower is better)
        # Theta should be small (less negative)
        risk_score += min(10, abs(theta) * 100)  # Penalize high theta

        # Gamma should be small (lower risk)
        risk_score += min(10, abs(gamma) * 1000) # Penalize high gamma

        # Volatility Score (Higher can be better, depending)
        # IV within reasonable range (20-50%)
        if 0.20 <= implied_volatility <= 0.50:
            volatility_score += 15
        elif 0.15 <= implied_volatility < 0.20 or 0.50 < implied_volatility <= 0.60:
            volatility_score += 8

        # Technical Score (Based on volume/open interest)
        if volume > 100 and open_interest > 50:
            technical_score += 10  # Good liquidity
        elif volume > 50 or open_interest > 25:
            technical_score += 5

        # Unusual Activity Score (Spikes in volume/OI)
        volume_oi_ratio = (volume / (open_interest + 1e-6))  # Avoid division by zero
        if volume_oi_ratio > 5:
            unusual_activity_score += 18 # Significant activity
        elif volume_oi_ratio > 2:
            unusual_activity_score += 10

        # IV Opportunity Score (High IV relative to historical)
        # This requires historical IV data - using a simple estimate for now
        iv_relative_to_average = implied_volatility / 0.3  # Assuming average IV is 30%
        if iv_relative_to_average > 1.5:
            iv_opportunity_score += 12
        elif iv_relative_to_average > 1.2:
            iv_opportunity_score += 6

        # Combine scores
        total_score = (
            profitability_score +
            volatility_score +
            technical_score +
            unusual_activity_score +
            iv_opportunity_score -
            risk_score
        )

        # Confidence level (adjust weights as needed)
        confidence = (
            (profitability_score * 0.2) +
            (risk_score * -0.15) +
            (volatility_score * 0.15) +
            (technical_score * 0.2) +
            (unusual_activity_score * 0.15) +
            (iv_opportunity_score * 0.15)
        )
        confidence = min(100, max(0, confidence))  # Clamp between 0-100

        # Generate recommendation and confidence
        recommendation = self._generate_recommendation_from_score(total_score)

        return {
            'components': {
                'profitability_score': profitability_score,
                'risk_score': risk_score,
                'volatility_score': volatility_score,
                'technical_score': technical_score,
                'unusual_activity_score': unusual_activity_score,
                'iv_opportunity_score': iv_opportunity_score
            },
            'total_score': total_score,
            'confidence': round(confidence, 1),
            'recommendation': recommendation
        }
    
    def _generate_recommendation_from_score(self, score: float) -> str:
        """Generate recommendation based on score.

        Handles invalid inputs gracefully by returning a default message.
        """
        try:
            if not isinstance(score, (int, float)):
                # Attempt to extract numeric value from dictionaries or strings
                if isinstance(score, dict) and 'total_score' in score:
                    score = float(score['total_score'])
                else:
                    score = float(score)
        except Exception:
            return "No recommendation available"

        if score >= 70:
            return "🔥 STRONG BUY - Excellent setup"
        elif score >= 60:
            return "✅ BUY - Good opportunity"
        elif score >= 50:
            return "🤔 NEUTRAL - Consider with caution"
        elif score >= 40:
            return "⚠️ WEAK - Better opportunities exist"
        else:
            return "❌ AVOID - Poor risk/reward"

    def _generate_trade_plan(self, option_data: Dict, market_data: Dict, score: float) -> Dict:
        """
        Generate an intelligent trade plan based on option data, market data, and calculated score.
        """
        # Basic plan structure
        plan = {
            'entry_details': {},
            'targets': {},
            'stop_loss': {},
            'risk_analysis': {},
            'position_sizing': {},
            'contingency_plan': {},
            'formatted_text': ''
        }

        # 1. Entry Details
        entry_price = option_data['mark']  # Use the mark price as the entry
        plan['entry_details'] = {
            'entry_price': entry_price,
            'description': f"Enter position at mark price: ${entry_price:.2f}"
        }

        # 2. Profit Targets (Scaling out)
        # Define 3 targets based on potential profit percentage
        target_1_percent = 0.20  # 20% profit
        target_2_percent = 0.50  # 50% profit
        target_3_percent = 1.00  # 100% profit

        target_1_price = entry_price * (1 + target_1_percent)
        target_2_price = entry_price * (1 + target_2_percent)
        target_3_price = entry_price * (1 + target_3_percent)

        plan['targets'] = {
            'target_1': {'price': target_1_price, 'percent': target_1_percent, 'action': 'Take partial profit (30%)'},
            'target_2': {'price': target_2_price, 'percent': target_2_percent, 'action': 'Take partial profit (30%)'},
            'target_3': {'price': target_3_price, 'percent': target_3_percent, 'action': 'Close remaining position (40%)'}
        }

        # 3. Stop Loss (Protect Capital)
        # Define a stop loss at a percentage below the entry price
        stop_loss_percent = 0.10  # 10% loss
        stop_price = entry_price * (1 - stop_loss_percent)
        plan['stop_loss'] = {
            'stop_price': stop_price,
            'percent': stop_loss_percent,
            'action': 'Exit position to limit losses'
        }

        # 4. Risk Analysis
        # Basic risk metrics (more detailed analysis can be added)
        risk_per_share = entry_price - stop_price
        max_risk = risk_per_share  # Assuming 1 share/contract for simplicity
        plan['risk_analysis'] = {
            'risk_per_share': risk_per_share,
            'max_risk': max_risk,
            'risk_description': f"Max risk per contract: ${risk_per_share:.2f}"
        }

        # 5. Position Sizing (Determine Contracts)
        # Example: Risk no more than 1% of trading capital
        trading_capital = 10000  # Example
        risk_allowance = trading_capital * 0.01
        max_contracts = int(risk_allowance / risk_per_share)
        plan['position_sizing'] = {
            'trading_capital': trading_capital,
            'risk_allowance': risk_allowance,
            'max_contracts': max_contracts,
            'sizing_description': f"Risk 1% of capital (${trading_capital:.2f}), max {max_contracts} contracts"
        }

        # 6. Contingency Plan
        # What to do if the market moves against you quickly
        plan['contingency_plan'] = {
            'scenario': 'Rapid adverse movement',
            'action': 'Evaluate market conditions, consider early exit if stop loss is breached significantly'
        }

        # 7. Formatted Plan Text
        plan['formatted_text'] = f"""
        --- INTELLIGENT TRADE PLAN ---
        Entry: {plan['entry_details']['description']}
        
        Targets:
        - Target 1: ${plan['targets']['target_1']['price']:.2f} (+{plan['targets']['target_1']['percent'] * 100:.1f}%) - {plan['targets']['target_1']['action']}
        - Target 2: ${plan['targets']['target_2']['price']:.2f} (+{plan['targets']['target_2']['percent'] * 100:.1f}%) - {plan['targets']['target_2']['action']}
        - Target 3: ${plan['targets']['target_3']['price']:.2f} (+{plan['targets']['target_3']['percent'] * 100:.1f}%) - {plan['targets']['target_3']['action']}
        
        Stop Loss: ${plan['stop_loss']['stop_price']:.2f} (-{plan['stop_loss']['percent'] * 100:.1f}%) - {plan['stop_loss']['action']}
        
        Risk: {plan['risk_analysis']['risk_description']}
        
        Position Sizing: {plan['position_sizing']['sizing_description']}
        
        Contingency: {plan['contingency_plan']['scenario']} - {plan['contingency_plan']['action']}
        """

        return plan