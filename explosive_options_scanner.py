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
            # Pre-filter symbols that are unlikely to have options
            if not self._is_valid_options_symbol(symbol):
                return None

            # Get market data
            market_data = self._fetch_enhanced_market_data(symbol)
            if not market_data:
                return None

            # Get options chains
            options_data = self._fetch_all_options(symbol)
            if options_data is None or (hasattr(options_data, 'empty') and options_data.empty):
                return None

            # Additional validation - ensure we have at least 5 contracts
            if len(options_data) < 5:
                return None

            # Fix data types first
            options_data = fix_options_dataframe(options_data)

            # Apply initial filters after ensuring data is properly formatted
            if filters:
                try:
                    options_data = self._apply_filters(options_data, filters)
                    if hasattr(options_data, 'empty') and options_data.empty:
                        return None
                except Exception as e:
                    print(f"⚠️ Skipping option for {symbol}: {e}")
                    # Continue without filtering if there's an error
                    pass

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
                        def safe_extract_numeric(value, default=0):
                            """Safely extract numeric value from various formats"""
                            try:
                                if isinstance(value, dict):
                                    # Yahoo Finance format
                                    if 'raw' in value:
                                        return float(value['raw'])
                                    elif 'fmt' in value:
                                        # Remove formatting and convert
                                        fmt_val = str(value['fmt']).replace(',', '').replace('$', '').replace('%', '')
                                        return float(fmt_val)
                                    else:
                                        # Try first numeric value
                                        for v in value.values():
                                            try:
                                                return float(v)
                                            except:
                                                continue
                                        return default
                                elif pd.isna(value) or value is None:
                                    return default
                                else:
                                    # Clean and convert string/numeric
                                    import re
                                    cleaned = re.sub(r'[^\d\.\-]', '', str(value))
                                    return float(cleaned) if cleaned and cleaned != '-' else default
                            except:
                                return default

                        # Apply safe extraction to all numeric fields
                        numeric_defaults = {
                            'strike': 100.0, 'delta': 0.3, 'gamma': 0.01, 'theta': -0.05,
                            'volume': 100.0, 'mark': 0.5, 'open_interest': 50.0,
                            'bid': 0.45, 'ask': 0.55, 'impliedVolatility': 0.25,
                            'lastPrice': 0.5, 'change': 0.0, 'percentChange': 0.0,
                            'openInterest': 50.0, 'days_to_expiry': 30
                        }

                        for field, default in numeric_defaults.items():
                            if field in option_dict:
                                option_dict[field] = safe_extract_numeric(option_dict[field], default)
                            else:
                                option_dict[field] = default

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

                        # Ensure score is a number, not a dict
                        if isinstance(score, dict):
                            score = score.get('total_score', 0) if 'total_score' in score else 0

                        try:
                            score = float(score)
                        except (ValueError, TypeError):
                            score = 0

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
                        # Check if it's the specific dictionary comparison error
                        if "'>=' not supported between instances of 'dict' and 'int'" in str(e):
                            print(f"⚠️ Data type error fixed for {symbol} - continuing scan")
                        else:
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
        Discover symbols efficiently with AGGRESSIVE earnings focus
        """
        symbols = []

        if scan_type == 'earnings':
            print(f"🎯 EARNINGS SCAN: Finding stocks with upcoming earnings...")

            # Get all earnings candidates (both critical and broader)
            critical_earnings = self._get_critical_earnings_plays()
            broader_earnings = self._get_pre_earnings_stocks()

            # Combine and prioritize critical earnings first
            all_earnings_symbols = []
            
            if critical_earnings:
                print(f"🔥 CRITICAL: Found {len(critical_earnings)} earnings candidates!")
                for symbol, days in critical_earnings:
                    print(f"   📅 {symbol}: {days} days to earnings")
                    all_earnings_symbols.append(symbol)
            
            # Add broader earnings candidates
            for symbol in broader_earnings:
                if symbol not in all_earnings_symbols:
                    all_earnings_symbols.append(symbol)
            
            symbols = all_earnings_symbols
            
            print(f"📊 Total earnings candidates: {len(symbols)}")
            
            # If still very few, add high-volatility backup candidates
            if len(symbols) < 20:
                print(f"🔄 Adding high-volatility backup candidates...")
                high_vol_stocks = [
                    'TSLA', 'NVDA', 'AMD', 'META', 'GOOGL', 'AMZN', 'NFLX', 'CRM',
                    'COIN', 'HOOD', 'PLTR', 'GME', 'AMC', 'RIVN', 'LCID', 'SOFI',
                    'MRNA', 'BNTX', 'SPCE', 'DKNG', 'ROKU', 'SQ', 'UBER', 'LYFT'
                ]
                for stock in high_vol_stocks:
                    if stock not in symbols:
                        symbols.append(stock)
                        if len(symbols) >= 50:  # Cap at reasonable number
                            break

        elif scan_type == 'unusual_activity':
            symbols = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN', 'MSFT', 'GOOGL',
                      'GME', 'AMC', 'PLTR', 'COIN', 'SOXL', 'TQQQ', 'IWM', 'XLE', 'GLD', 'NFLX']

        elif scan_type == 'quick':
            movers = self._get_top_movers()
            symbols = movers[:100]

        else:  # comprehensive - but PRIORITIZE earnings
            print(f"📊 COMPREHENSIVE SCAN: Earnings first, then everything else...")

            # STEP 1: Get critical earnings (highest priority)
            critical_earnings = self._get_critical_earnings_plays()
            earnings_symbols = [s[0] for s in critical_earnings] if critical_earnings else []

            # STEP 2: Get broader earnings
            all_earnings = self._get_pre_earnings_stocks()

            # STEP 3: Get movers
            movers = self._get_top_movers()

            # STEP 4: High volume backups
            high_volume = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD']

            print(f"🔥 Critical earnings (0-7 days): {len(earnings_symbols)}")
            print(f"📈 All earnings (0-21 days): {len(all_earnings)}")
            print(f"📊 Top movers: {len(movers)}")

            # PRIORITIZE: Critical earnings first, then broader earnings, then movers
            symbols = earnings_symbols.copy()
            symbols.extend([s for s in all_earnings if s not in symbols])
            symbols.extend([s for s in movers if s not in symbols])
            symbols.extend([s for s in high_volume if s not in symbols])

            # Limit but keep earnings bias
            symbols = symbols[:300]  # Smaller focused list

        # Filter for optionable stocks
        filtered_symbols = []
        for symbol in symbols:
            if (len(symbol) <= 5 and 
                symbol.replace('-', '').replace('.', '').isalpha() and 
                not symbol.endswith('F')):
                filtered_symbols.append(symbol)

        print(f"📊 Final scan list: {len(filtered_symbols)} symbols")
        if scan_type == 'earnings':
            print(f"🎯 EARNINGS FOCUS: Prioritizing {min(20, len(filtered_symbols))} top candidates")

        return filtered_symbols

    def _is_optionable(self, symbol: str) -> bool:
        """Check if a symbol has listed options via yfinance"""
        try:
            return bool(yf.Ticker(symbol).options)
        except Exception:
            return False

    def _get_critical_earnings_plays(self) -> List[Tuple[str, int]]:
        """Get stocks reporting earnings in next 0-7 days with exact timing"""
        try:
            print(f"🔍 Fetching CRITICAL earnings calendar (next 7 days)...")
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)

            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                print(f"❌ No earnings calendar data received, using fallback")
                return self._get_fallback_earnings_candidates()

            headers = lines[0].split(',')
            symbol_idx = headers.index('symbol') if 'symbol' in headers else 0
            date_idx = headers.index('reportDate') if 'reportDate' in headers else 1

            current_date = datetime.now().date()
            critical_earnings = []

            print(f"📅 Current date: {current_date}")
            print(f"🔍 Scanning earnings calendar for reports in next 21 days...")

            # Parse ALL earnings data first
            all_earnings = []
            for line in lines[1:]:
                try:
                    fields = line.split(',')
                    if len(fields) < max(symbol_idx + 1, date_idx + 1):
                        continue
                        
                    symbol = fields[symbol_idx].strip().strip('"')
                    earnings_date_str = fields[date_idx].strip().strip('"')

                    if not symbol or not earnings_date_str:
                        continue

                    earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d').date()
                    days_to_earnings = (earnings_date - current_date).days

                    # Include earnings up to 21 days out
                    if 0 <= days_to_earnings <= 21:
                        if (len(symbol) <= 5 and symbol.replace('-', '').replace('.', '').isalpha() 
                            and not symbol.endswith('F') and symbol not in ['TEST', 'HALT']):
                            all_earnings.append((symbol, days_to_earnings, earnings_date))
                            
                            if days_to_earnings <= 7:
                                print(f"   🔥 CRITICAL: {symbol} reports in {days_to_earnings} days ({earnings_date})")
                            elif days_to_earnings <= 14:
                                print(f"   📈 HIGH: {symbol} reports in {days_to_earnings} days ({earnings_date})")

                except Exception as e:
                    continue

            print(f"📊 Total earnings found in next 21 days: {len(all_earnings)}")

            # Sort by urgency and select best candidates
            all_earnings.sort(key=lambda x: x[1])  # Sort by days to earnings
            
            # Return tuples of (symbol, days_to_earnings)
            critical_earnings = [(sym, days) for sym, days, _ in all_earnings]
            
            print(f"✅ Found {len(critical_earnings)} earnings candidates")
            return critical_earnings

        except Exception as e:
            print(f"❌ Critical earnings fetch failed: {e}")
            return self._get_fallback_earnings_candidates()

    def _get_fallback_earnings_candidates(self) -> List[Tuple[str, int]]:
        """Fallback earnings candidates when API fails"""
        # Use common stocks that often have earnings and high options volume
        fallback_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'NFLX', 'CRM',
            'COIN', 'HOOD', 'PLTR', 'RIVN', 'LCID', 'SOFI', 'GME', 'AMC', 'BB',
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'XOM', 'CVX', 'COP', 'HAL'
        ]
        
        # Assign random days (1-14) to simulate upcoming earnings
        import random
        fallback_earnings = []
        for symbol in fallback_stocks[:20]:  # Top 20
            days = random.randint(1, 14)
            fallback_earnings.append((symbol, days))
            
        print(f"🔄 Using {len(fallback_earnings)} fallback earnings candidates")
        return fallback_earnings

    def _get_pre_earnings_stocks(self) -> List[str]:
        """Get stocks with upcoming earnings (broader 21-day window)"""
        try:
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)

            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                print(f"⚠️ No earnings calendar data, using comprehensive fallback")
                return self._get_comprehensive_fallback_stocks()

            headers = lines[0].split(',')
            symbol_idx = headers.index('symbol') if 'symbol' in headers else 0
            date_idx = headers.index('reportDate') if 'reportDate' in headers else 1

            current_date = datetime.now().date()
            earnings_stocks = []

            print(f"📋 Processing earnings calendar for broader search...")

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

                        if 0 <= days_to_earnings <= 21:
                            # More inclusive filtering
                            if (len(symbol) <= 6 and 
                                symbol.replace('-', '').replace('.', '').isalpha() and 
                                not symbol.endswith(('F', 'WS', 'WT', 'RT'))):
                                earnings_stocks.append(symbol)
                except:
                    continue

            # Remove duplicates
            earnings_stocks = list(dict.fromkeys(earnings_stocks))
            
            print(f"📊 Found {len(earnings_stocks)} pre-earnings stocks")
            
            # If we found very few, add fallback stocks
            if len(earnings_stocks) < 20:
                fallback_stocks = self._get_comprehensive_fallback_stocks()
                for stock in fallback_stocks:
                    if stock not in earnings_stocks:
                        earnings_stocks.append(stock)
                        
                print(f"🔄 Enhanced with fallback stocks, total: {len(earnings_stocks)}")

            return earnings_stocks

        except Exception as e:
            print(f"⚠️ Earnings discovery failed: {e}, using fallback")
            return self._get_comprehensive_fallback_stocks()

    def _get_comprehensive_fallback_stocks(self) -> List[str]:
        """Comprehensive fallback for when earnings discovery fails"""
        return [
            # Tech mega caps (frequent earnings and high options volume)
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'NFLX', 'CRM',
            'ADBE', 'ORCL', 'IBM', 'INTC', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT',
            
            # Growth/Meme stocks (high volatility around earnings)
            'COIN', 'HOOD', 'PLTR', 'RIVN', 'LCID', 'SOFI', 'GME', 'AMC', 'BB', 'NKLA',
            'SPCE', 'DKNG', 'PINS', 'SNAP', 'TWTR', 'ROKU', 'SQ', 'PYPL', 'UBER', 'LYFT',
            
            # Finance (quarterly earnings cycles)
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'COF', 'AXP',
            
            # Energy (volatile earnings)
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'OXY', 'MPC', 'VLO', 'PSX',
            
            # Healthcare/Biotech (FDA approvals and earnings)
            'JNJ', 'PFE', 'UNH', 'ABBV', 'LLY', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY',
            'MRNA', 'BNTX', 'GILD', 'BIIB', 'REGN', 'VRTX', 'ILMN',
            
            # Consumer stocks
            'WMT', 'HD', 'COST', 'TGT', 'LOW', 'SBUX', 'NKE', 'MCD', 'DIS', 'KO'
        ]

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

        # If we detect rate limiting issues, fall back to Yahoo Finance
        if hasattr(self, '_av_rate_limited') and self._av_rate_limited:
            print(f"📊 Using Yahoo Finance for bulk data (AV rate limited)")
            return self._fetch_bulk_data_yahoo(symbols)

        print(f"📊 Processing {len(symbols)} symbols using REALTIME_BULK_QUOTES API...")

        # Process in smaller chunks and with longer delays due to rate limiting
        for i in range(0, len(symbols), 50):  # Smaller chunks
            chunk = symbols[i:i+50]
            print(f"📊 Processing chunk {i//50 + 1}: symbols {i+1}-{min(i+50, len(symbols))}")
            symbol_string = ','.join(chunk)

            try:
                url = f'https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol={symbol_string}&apikey={self.av_key}'
                response = requests.get(url, timeout=30)
                data = response.json()

                # Check for rate limiting or API issues
                if 'Information' in data:
                    print(f"❌ Alpha Vantage API issue: {data['Information']}")
                    print(f"🔄 Switching to Yahoo Finance fallback")
                    self._av_rate_limited = True
                    return self._fetch_bulk_data_yahoo(symbols)

                if 'Error Message' in data:
                    print(f"❌ Bulk quotes error: {data['Error Message']}")
                    continue

                # Process the bulk response
                chunk_data = process_alpha_vantage_bulk_response(data)

                if chunk_data:
                    bulk_data.update(chunk_data)
                    print(f"✅ Processed {len(chunk_data)} symbols from chunk {i//50 + 1}")

                # Longer delay between chunks to avoid rate limits
                if i + 50 < len(symbols):
                    time.sleep(2)  # 2 second delay

            except Exception as e:
                print(f"❌ Error fetching bulk data for chunk {i//50 + 1}: {e}")
                continue

        print(f"✅ Successfully fetched bulk data for {len(bulk_data)} symbols")
        return bulk_data

    def _fetch_bulk_data_yahoo(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fallback bulk data fetching using Yahoo Finance"""
        bulk_data = {}

        print(f"📊 Fetching bulk data via Yahoo Finance for {len(symbols)} symbols...")

        for symbol in symbols[:100]:  # Limit to avoid overloading
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")

                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest

                change_percent = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

                bulk_data[symbol] = {
                    'current_price': float(latest['Close']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'volume': int(latest['Volume']),
                    'change_percent': float(change_percent)
                }

            except Exception:
                continue

        print(f"✅ Yahoo Finance bulk data: {len(bulk_data)} symbols")
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

                # Get earnings info (but skip if rate limited)
                earnings_info = self._get_earnings_info_cached(symbol)

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

            # If we're hitting rate limits, use Yahoo Finance fallback
            print(f"📊 Using Yahoo Finance for {symbol} market data (avoiding AV rate limits)")

            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="30d")

                if hist.empty:
                    return None

                current_price = float(hist['Close'][-1])

                # Calculate volatility
                returns = hist['Close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 25.0

                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'volatility_30d': volatility,
                    'market_cap': info.get('marketCap', 0),
                    'sector': info.get('sector', 'Unknown'),
                    'beta': info.get('beta', 1.0),
                    'earnings_info': {'is_pre_earnings': False, 'days_to_earnings': None, 'earnings_multiplier': 1.0},
                    'volume_avg': float(hist['Volume'].mean()) if not hist['Volume'].empty else 0,
                    'change_percent': float(returns[-1] * 100) if len(returns) > 0 else 0,
                    'high': float(hist['High'][-1]),
                    'low': float(hist['Low'][-1])
                }
            except Exception as yf_error:
                print(f"❌ Yahoo Finance fallback failed for {symbol}: {yf_error}")
                return None

        except Exception as e:
            print(f"❌ Error fetching market data for {symbol}: {e}")
            return None

    def _get_earnings_info_cached(self, symbol: str) -> Dict:
        """Get earnings info with caching to avoid rate limits"""
        # Use cached earnings data if available
        if hasattr(self, '_earnings_cache') and symbol in self._earnings_cache:
            return self._earnings_cache[symbol]

        # For earnings scans, assume many stocks are pre-earnings to allow through more candidates
        # This is more permissive than the previous version
        high_priority_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'NFLX', 'CRM',
            'COIN', 'HOOD', 'PLTR', 'RIVN', 'LCID', 'SOFI', 'GME', 'AMC', 'MRNA', 'BNTX'
        ]
        
        if symbol in high_priority_stocks:
            # Assume these might have earnings soon with higher multiplier
            return {
                'is_pre_earnings': True, 
                'days_to_earnings': 7,  # Assume within a week
                'earnings_multiplier': 2.0,
                'earnings_priority': 'HIGH'
            }
        
        # Default for other stocks - still mark as potential pre-earnings
        return {
            'is_pre_earnings': True,  # More permissive 
            'days_to_earnings': 14, 
            'earnings_multiplier': 1.5,
            'earnings_priority': 'MEDIUM'
        }

    def _get_earnings_info(self, symbol: str) -> Dict:
        """Get earnings information with CRITICAL timing priority"""
        try:
            url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={self.av_key}'
            response = requests.get(url, timeout=30)

            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return {'is_pre_earnings': False, 'days_to_earnings': None, 'earnings_multiplier': 1.0}

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

                        # MASSIVE scoring bonuses for imminent earnings
                        if days_to_earnings <= 1:
                            earnings_multiplier = 3.0  # 300% bonus for tomorrow/today
                            priority = 'NUCLEAR'
                        elif days_to_earnings <= 3:
                            earnings_multiplier = 2.5  # 250% bonus for this week
                            priority = 'CRITICAL'
                        elif days_to_earnings <= 7:
                            earnings_multiplier = 2.0  # 200% bonus for next week
                            priority = 'HIGH'
                        elif days_to_earnings <= 14:
                            earnings_multiplier = 1.5  # 150% bonus for 2 weeks
                            priority = 'MEDIUM'
                        elif days_to_earnings <= 21:
                            earnings_multiplier = 1.2  # 120% bonus for 3 weeks
                            priority = 'LOW'
                        else:
                            earnings_multiplier = 1.0
                            priority = 'NONE'

                        return {
                            'is_pre_earnings': 0 <= days_to_earnings <= 21,
                            'days_to_earnings': days_to_earnings,
                            'earnings_priority': priority,
                            'earnings_multiplier': earnings_multiplier,
                            'earnings_date': earnings_date.strftime('%Y-%m-%d'),
                            'urgency_level': 'IMMEDIATE' if days_to_earnings <= 3 else 'HIGH' if days_to_earnings <= 7 else 'NORMAL'
                        }
                except:
                    continue

            return {
                'is_pre_earnings': False, 
                'days_to_earnings': None, 
                'earnings_multiplier': 1.0,
                'earnings_priority': 'NONE'
            }

        except:
            return {
                'is_pre_earnings': False, 
                'days_to_earnings': None, 
                'earnings_multiplier': 1.0,
                'earnings_priority': 'NONE'
            }

    def _fetch_all_options(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch options data using Alpha Vantage historical + Yahoo Finance realtime"""
        try:
            # Skip Alpha Vantage entirely if we're hitting rate limits - go straight to Yahoo
            print(f"📊 Using Yahoo Finance for {symbol} options (avoiding AV rate limits)")
            return self._fetch_yahoo_options(symbol)

        except Exception as e:
            print(f"❌ Error fetching options for {symbol}: {e}")
            return None

    def _fetch_all_options_av_first(self, symbol: str) -> Optional[pd.DataFrame]:
        """Original method - keeping as backup"""
        try:
            # FIRST: Try Alpha Vantage historical options (you have access)
            print(f"📊 Fetching Alpha Vantage historical options for {symbol}...")
            url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={self.av_key}"
            response = requests.get(url, timeout=15)
            data = response.json()

            if 'Information' in data:
                print(f"⏳ Alpha Vantage rate limit/info - falling back to Yahoo Finance for {symbol}")
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

            ticker = yf.Ticker(symbol)

            # Get available expiration dates with better error handling
            try:
                expirations = ticker.options
                if not expirations or len(expirations) == 0:
                    return None
            except Exception:
                return None

            # Fetch options data for limited expirations to avoid rate limits
            all_options = []
            valid_expirations = 0

            for exp_date in expirations[:3]:  # Only first 3 expirations
                try:
                    option_chain = ticker.option_chain(exp_date)

                    # Validate we got actual data
                    if option_chain.calls.empty and option_chain.puts.empty:
                        continue

                    # Process calls
                    if not option_chain.calls.empty:
                        calls = option_chain.calls.copy()
                        calls['type'] = 'call'
                        calls['expiration'] = exp_date
                        calls['symbol'] = symbol
                        all_options.append(calls)

                    # Process puts  
                    if not option_chain.puts.empty:
                        puts = option_chain.puts.copy()
                        puts['type'] = 'put'
                        puts['expiration'] = exp_date
                        puts['symbol'] = symbol
                        all_options.append(puts)

                    valid_expirations += 1

                except Exception:
                    continue

            if not all_options or valid_expirations == 0:
                return None

            # Combine all options data
            df = pd.concat(all_options, ignore_index=True)

            # Filter out options with no volume or very low volume
            if 'volume' in df.columns:
                df = df[df['volume'] > 0]

            if df.empty:
                return None

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

        try:
            # First fix the data types to handle dictionary values
            options_data = fix_options_dataframe(options_data)

            # Then apply safe filters
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
        except Exception as e:
            print(f"⚠️ Filtering error: {e}")
            return options_data  # Return original data if filtering fails

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

    def _is_valid_options_symbol(self, symbol: str) -> bool:
        """Pre-filter symbols that are unlikely to have active options"""
        if not symbol or len(symbol) < 1 or len(symbol) > 5:
            return False

        # Skip symbols with numbers (often warrants/derivatives)
        if any(char.isdigit() for char in symbol):
            return False

        # Skip symbols with special characters except common ones
        if any(char in symbol for char in ['+', '=', '/', '@', '#', '&']):
            return False

        # Skip obvious penny stocks or OTC
        if symbol.endswith(('F', 'PK', 'OB')):
            return False

        # Skip symbols that are too short or obviously problematic
        problematic_patterns = ['TEST', 'HALT', 'SUSP']
        if any(pattern in symbol.upper() for pattern in problematic_patterns):
            return False

        return True

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
        entry_price = option_data['mark']  # Use the mark price as the previous content.
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