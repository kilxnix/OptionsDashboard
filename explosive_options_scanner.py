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
            'min_score': 30,  # Minimum score to consider (lowered to find more opportunities)
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
            if options_data is None or (hasattr(options_data, 'empty') and options_data.empty):
                return None

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
                        required_fields = ['strike', 'expiration', 'type', 'delta', 'gamma', 'theta', 'volume', 'mark']
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

                        # Convert numeric fields to float with comprehensive error handling
                        numeric_fields = ['strike', 'delta', 'gamma', 'theta', 'volume', 'mark']
                        for field in numeric_fields:
                            try:
                                val = option_dict[field]
                                # Handle string values that might contain non-numeric chars
                                import re
                                cleaned_val = re.sub(r'[^\d\.\-]', '', val)
                                if cleaned_val and cleaned_val != '-':
                                    option_dict[field] = float(cleaned_val)
                                else:
                                    raise ValueError("Empty after cleaning")
                            else:
                                option_dict[field] = float(val)
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
                                        # Try to parse and reformat
                                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                                            try:
                                                parsed_date = datetime.strptime(exp_str, fmt)
                                                option_dict['expiration'] = parsed_date.strftime('%Y-%m-%d')
                                                break
                                            except ValueError:
                                                continue
                                        else:
                                            option_dict['expiration'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                                except:
                                    option_dict['expiration'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        score, analysis = self.grader.calculate_option_score(option_dict, market_data)

                        if score >= self.scan_config['min_score']:
                            option_dict['score_analysis'] = analysis
                            option_dict['total_score'] = score
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
        Discover symbols based on scan type
        """
        symbols = []

        if scan_type == 'earnings':
            # Get pre-earnings stocks
            symbols = self._get_pre_earnings_stocks()
            # Add high-volume liquid stocks as backup
            liquid_stocks = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD']
            symbols.extend([s for s in liquid_stocks if s not in symbols])

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

        # Filter out likely non-optionable symbols
        filtered_symbols = []
        for symbol in symbols:
            # Skip symbols with more than 4 characters (likely foreign/OTC)
            if len(symbol) <= 4 and symbol.isalpha() and not any(char in symbol for char in ['.', '-']):
                filtered_symbols.append(symbol)

        print(f"📊 Filtered from {len(symbols)} to {len(filtered_symbols)} quality symbols")
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

    def _fetch_enhanced_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch comprehensive market data for a symbol using Alpha Vantage"""
        try:
            # Add rate limiting delay
            time.sleep(1.0)  # Increased delay to avoid rate limits

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

            # Get company overview for additional data
            overview_url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={self.av_key}'
            try:
                overview_response = requests.get(overview_url, timeout=10)
                overview_data = overview_response.json()

                market_cap = float(overview_data.get('MarketCapitalization', 0)) if overview_data.get('MarketCapitalization') else 0
                sector = overview_data.get('Sector', 'Unknown')
                beta = float(overview_data.get('Beta', 1.0)) if overview_data.get('Beta') else 1.0

            except:
                market_cap = 0
                sector = 'Unknown'
                beta = 1.0

            # Get earnings info from Alpha Vantage earnings calendar
            earnings_info = self._get_earnings_info(symbol)

            return {
                'symbol': symbol,
                'current_price': current_price,
                'volatility_30d': volatility,
                'market_cap': market_cap,
                'sector': sector,
                'beta': beta,
                'earnings_info': earnings_info,
                'volume_avg': 0  # Would need separate API call for volume
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
        """Fetch all options for a symbol using Alpha Vantage"""
        try:
            # Try Alpha Vantage historical options first
            url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={self.av_key}"
            response = requests.get(url, timeout=15)
            data = response.json()

            if 'Information' in data and 'rate limit' in data['Information'].lower():
                print(f"⏳ Rate limit reached for {symbol} - waiting...")
                time.sleep(60)
                return self._fetch_all_options(symbol)

            if 'Error Message' in data:
                print(f"❌ Alpha Vantage historical options error for {symbol}: {data['Error Message']}")
                # Try real-time options as fallback
                return self._fetch_realtime_options_av(symbol)

            if 'data' in data and data['data'] and len(data['data']) > 0:
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
                        'open_interest': 'openInterest',
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
                                if pd.isna(exp_str) or exp_str == '':
                                    return 30  # Default to 30 days

                                # Try different formats
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                                    try:
                                        exp_date = datetime.strptime(str(exp_str), fmt)
                                        return max(1, (exp_date - datetime.now()).days)
                                    except ValueError:
                                        continue
                                return 30  # Default if no format works

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
                            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                                try:
                                    parsed_date = datetime.strptime(exp_str, fmt)
                                    return parsed_date.strftime('%Y-%m-%d')
                                except ValueError:
                                    continue

                            # If no format works, default to 30 days from now
                            return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        df['expiration'] = df['expiration'].apply(standardize_expiration)

                    # Convert all numeric columns to proper types with comprehensive error handling
                    numeric_cols = ['mark', 'strike', 'volume', 'openInterest', 'delta', 'gamma', 'theta', 'impliedVolatility']
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
                                elif col in ['volume', 'openInterest']:
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

            # Fallback to real-time options
            print(f"🔄 Trying real-time options for {symbol}...")
            return self._fetch_realtime_options_av(symbol)

        except Exception as e:
            print(f"❌ Error fetching options for {symbol}: {e}")
            return None

    def _fetch_realtime_options_av(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fallback method for real-time options data from Alpha Vantage"""
        try:
            url = f"https://www.alphavantage.co/query?function=REALTIME_OPTIONS&symbol={symbol}&apikey={self.av_key}"
            response = requests.get(url, timeout=15)
            data = response.json()

            # Check for rate limiting
            if 'Information' in data and 'rate limit' in data['Information'].lower():
                print(f"⏳ Rate limit reached for {symbol} - waiting...")
                time.sleep(60)
                return None

            if 'Information' in data and 'premium@alphavantage.co' in data['Information']:
                print(f"⏳ API quota exceeded for {symbol}")
                return None

            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                print(f"✅ Real-time options found for {symbol}: {len(df)} contracts")

                # Standardize columns with proper data type conversion
                if 'last_price' in df.columns:
                    df['mark'] = pd.to_numeric(df['last_price'], errors='coerce').fillna(0.5)
                elif 'ask' in df.columns and 'bid' in df.columns:
                    df['ask'] = pd.to_numeric(df['ask'], errors='coerce').fillna(0.5)
                    df['bid'] = pd.to_numeric(df['bid'], errors='coerce').fillna(0.5)
                    df['mark'] = (df['ask'] + df['bid']) / 2
                else:
                    df['mark'] = 0.5

                # Add required columns with defaults if missing
                defaults = {
                    'symbol': symbol,
                    'volume': 100,
                    'openInterest': 50,
                    'delta': 0.3,
                    'gamma': 0.01,
                    'theta': -0.05,
                    'impliedVolatility': 0.25
                }

                for col, default_val in defaults.items():
                    if col not in df.columns:
                        df[col] = default_val

                # Fix expiration date format first - this is causing the main errors
                if 'expiration' in df.columns:
                    def standardize_expiration(exp_val):
                        if pd.isna(exp_val) or exp_val == '' or exp_val is None:
                            return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        exp_str = str(exp_val).strip()
                        if not exp_str:
                            return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                        # Try to parse and standardize the date
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                            try:
                                parsed_date = datetime.strptime(exp_str, fmt)
                                return parsed_date.strftime('%Y-%m-%d')
                            except ValueError:
                                continue

                        # If no format works, default to 30 days from now
                        return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

                    df['expiration'] = df['expiration'].apply(standardize_expiration)

                # Convert all numeric columns to proper types with comprehensive error handling
                numeric_cols = ['mark', 'strike', 'volume', 'openInterest', 'delta', 'gamma', 'theta', 'impliedVolatility']
                for col in numeric_cols:
                    if col in df.columns:
                        # Convert to numeric, handling strings and other types
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        # Fill NaN values with appropriate defaults
                        if col == 'mark':
                            df[col] = df[col].fillna(0.5)
                        elif col == 'strike':
                            df[col] = df[col].fillna(100)
                        elif col in ['volume', 'openInterest']:
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

                return df

            print(f"❌ No options data available for {symbol}")
            return None

        except Exception as e:
            print(f"❌ Real-time options fetch failed for {symbol}: {e}")
            return None

    def _apply_filters(self, options_data: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply filters to options data"""
        if options_data is None or options_data.empty:
            return pd.DataFrame()

        filtered = options_data.copy()

        # Ensure numeric columns are properly converted
        numeric_cols = ['mark', 'delta', 'volume', 'days_to_expiry', 'strike']
        for col in numeric_cols:
            if col in filtered.columns:
                filtered[col] = pd.to_numeric(filtered[col], errors='coerce')

        # Price filters
        if 'min_price' in filters and 'mark' in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered['mark'], errors='coerce') >= filters['min_price']]
        if 'max_price' in filters and 'mark' in filtered.columns:
            filtered = filtered[pd.to_numeric(filtered['mark'], errors='coerce') <= filters['max_price']]

        # Delta filters
        if 'min_delta' in filters and 'delta' in filtered.columns:
            delta_numeric = pd.to_numeric(filtered['delta'], errors='coerce').abs()
            filtered = filtered[delta_numeric >= filters['min_delta']]
        if 'max_delta' in filters and 'delta' in filtered.columns:
            delta_numeric = pd.to_numeric(filtered['delta'], errors='coerce').abs()
            filtered = filtered[delta_numeric <= filters['max_delta']]

        # Days to expiry
        if 'min_days' in filters and 'days_to_expiry' in filtered.columns:
            days_numeric = pd.to_numeric(filtered['days_to_expiry'], errors='coerce')
            filtered = filtered[days_numeric >= filters['min_days']]
        if 'max_days' in filters and 'days_to_expiry' in filtered.columns:
            days_numeric = pd.to_numeric(filtered['days_to_expiry'], errors='coerce')
            filtered = filtered[days_numeric <= filters['max_days']]

        # Volume filter
        if 'min_volume' in filters and 'volume' in filtered.columns:
            volume_numeric = pd.to_numeric(filtered['volume'], errors='coerce')
            filtered = filtered[volume_numeric >= filters['min_volume']]

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