import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import yfinance as yf
from tabulate import tabulate
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy import stats
import warnings
import time
import os
import json
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

# Initialize Google Drive connection
print("Mounting Google Drive...")

# Create TradingPlans directory if it doesn't exist
base_dir = './TradingPlans'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)
    print(f"Created directory: {base_dir}")
else:
    print(f"Using existing directory: {base_dir}")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Define timeframe configurations
TIMEFRAMES = {
    '1m': {
        'function': 'TIME_SERIES_INTRADAY',
        'interval': '1min',
        'key_prefix': 'Time Series (1min)'
    },
    '5m': {
        'function': 'TIME_SERIES_INTRADAY',
        'interval': '5min',
        'key_prefix': 'Time Series (5min)'
    },
    '15m': {
        'function': 'TIME_SERIES_INTRADAY',
        'interval': '15min',
        'key_prefix': 'Time Series (15min)'
    },
    '30m': {
        'function': 'TIME_SERIES_INTRADAY',
        'interval': '30min',
        'key_prefix': 'Time Series (30min)'
    },
    '1h': {
        'function': 'TIME_SERIES_INTRADAY',
        'interval': '60min',
        'key_prefix': 'Time Series (60min)'
    },
    'D': {
        'function': 'TIME_SERIES_DAILY_ADJUSTED',
        'key_prefix': 'Time Series (Daily)'
    },
    'W': {
        'function': 'TIME_SERIES_WEEKLY',
        'key_prefix': 'Weekly Time Series'
    }
}


class CompleteOptionsScanner:

    def __init__(self, api_key, min_delta=0.2, max_delta=0.7):
        self.api_key = api_key
        self.min_delta = min_delta
        self.max_delta = max_delta
        self.min_volume = 6
        self.min_pattern_quality = 0.65
        self.request_count = 0
        self.last_request_time = 0
        self.requests_per_minute = 75

    def fetch_alpha_vantage_data(self, symbol, timeframe):
        """Fetch price data using Alpha Vantage API with support for all timeframes"""
        self._check_rate_limit()

        try:
            tf_config = TIMEFRAMES[timeframe]
            function = tf_config['function']

            # Build URL based on timeframe type
            if function == 'TIME_SERIES_INTRADAY':
                url = (f'https://www.alphavantage.co/query?function={function}'
                       f'&symbol={symbol}&interval={tf_config["interval"]}'
                       f'&outputsize=compact&apikey={self.api_key}')  # Use compact for faster response
            elif function == 'TIME_SERIES_DAILY_ADJUSTED':
                url = (
                    f'https://www.alphavantage.co/query?function={function}'
                    f'&symbol={symbol}&outputsize=compact&apikey={self.api_key}')
            else:  # Weekly
                url = (f'https://www.alphavantage.co/query?function={function}'
                       f'&symbol={symbol}&apikey={self.api_key}')

            response = requests.get(url, timeout=15)  # Add timeout
            response.raise_for_status()  # Raise exception for bad status codes
            data = response.json()

            if 'Error Message' in data:
                print(
                    f"Error fetching data for {symbol}: {data['Error Message']}"
                )
                return None

            key_prefix = tf_config['key_prefix']
            if key_prefix not in data:
                print(
                    f"No data available for {symbol} at {timeframe} timeframe")
                return None

            # Convert to DataFrame
            df = pd.DataFrame.from_dict(data[key_prefix], orient='index')

            # Handle different column names based on timeframe
            if function == 'TIME_SERIES_DAILY_ADJUSTED':
                df.columns = [
                    'Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume',
                    'Dividend_Amount', 'Split_Coefficient'
                ]
            else:
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            # Convert types
            for col in df.columns:
                if col != 'Volume':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

            # Sort index
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)

            print(f"Successfully fetched {timeframe} data for {symbol}")
            return df

        except Exception as e:
            print(f"Error fetching {timeframe} data for {symbol}: {e}")
            return None

    def fetch_multi_timeframe_data(self, symbol):
        """Fetch price data for all timeframes using Alpha Vantage"""
        timeframe_data = {}

        for tf in TIMEFRAMES.keys():
            df = self.fetch_alpha_vantage_data(symbol, tf)
            if df is not None and not df.empty:
                timeframe_data[tf] = df
            time.sleep(0.5)  # Small delay between requests

        return timeframe_data

    def analyze_timeframes(self, symbol, price_data):
        """Analyze patterns across all timeframes with extended candlestick support"""
        analysis_results = {}

        for timeframe, data in price_data.items():
            try:
                # Use Adjusted_Close for daily data if available
                if 'Adjusted_Close' in data.columns:
                    data['Close'] = data['Adjusted_Close']

                gaps = self.analyze_gaps(data)
                patterns = self.detect_patterns(data)
                volume_analysis = self.analyze_volume(data)
                candle_patterns = self.check_candlestick_conditions(data)

                latest_gap = gaps.iloc[-1]
                latest_patterns = patterns.iloc[-1]
                latest_candles = candle_patterns.iloc[-1]
                latest_volume = volume_analysis.iloc[-1]

                analysis_results[timeframe] = {
                    'gap_percent': latest_gap['gap_percent'],
                    'gap_direction': latest_gap['gap_direction'],
                    'gap_mitigated': latest_gap['gap_mitigated'],
                    'unmitigated_gap_price':
                    latest_gap['unmitigated_gap_price'],
                    'patterns': {
                        'falling_wedge':
                        bool(latest_patterns['falling_wedge']),
                        'rising_wedge': bool(latest_patterns['rising_wedge']),
                        'high_slope': latest_patterns['high_slope'],
                        'low_slope': latest_patterns['low_slope']
                    },
                    'candles': {
                        'bullish':
                        bool(latest_candles['matching_candle_bullish']),
                        'bearish':
                        bool(latest_candles['matching_candle_bearish']),
                        'bullish_engulfing':
                        bool(latest_candles['bullish_engulfing']),
                        'bearish_engulfing':
                        bool(latest_candles['bearish_engulfing']),
                        'hammer':
                        bool(latest_candles['hammer']),
                        'inverted_hammer':
                        bool(latest_candles['inverted_hammer']),
                        'shooting_star':
                        bool(latest_candles['shooting_star']),
                        'doji':
                        bool(latest_candles['doji']),
                    },
                    'volume': {
                        'relative_volume': latest_volume['relative_volume'],
                        'unusual_volume': bool(latest_volume['unusual_volume'])
                    }
                }

            except Exception as e:
                print(f"Error analyzing {timeframe} for {symbol}: {e}")
                continue

        return analysis_results

    def calculate_pattern_confluence(self, analysis_results):
        """Calculate pattern confluence with weighted timeframe importance"""
        confluence_score = 0
        bullish_signals = 0
        bearish_signals = 0

        # Define timeframe weights (higher weight for longer timeframes)
        timeframe_weights = {
            '5m': 0.5,
            '15m': 0.75,
            '30m': 1.0,
            '1h': 1.25,
            'D': 1.5,
            'W': 2.0
        }

        for tf, results in analysis_results.items():
            weight = timeframe_weights.get(tf, 1.0)

            # === Gap Analysis ===
            if abs(results['gap_percent']
                   ) > 0 and not results['gap_mitigated']:
                if results['gap_direction'] == 'Up':
                    bullish_signals += weight
                else:
                    bearish_signals += weight

            # === Pattern Analysis ===
            if results['patterns']['falling_wedge']:
                bullish_signals += weight
            if results['patterns']['rising_wedge']:
                bearish_signals += weight

            # === Candlestick Patterns ===
            candles = results['candles']

            if candles.get('bullish'):
                bullish_signals += weight
            if candles.get('bearish'):
                bearish_signals += weight

            # New candlestick logic
            if candles.get('bullish_engulfing'):
                bullish_signals += weight
            if candles.get('hammer') or candles.get('inverted_hammer'):
                bullish_signals += 0.5 * weight

            if candles.get('bearish_engulfing'):
                bearish_signals += weight
            if candles.get('shooting_star'):
                bearish_signals += 0.5 * weight

            if candles.get('doji'):
                # Doji = indecision — light weight to both sides
                bullish_signals += 0.2 * weight
                bearish_signals += 0.2 * weight

            # === Volume Confirmation ===
            if results['volume']['unusual_volume']:
                if bullish_signals > bearish_signals:
                    bullish_signals += 0.5 * weight
                elif bearish_signals > bullish_signals:
                    bearish_signals += 0.5 * weight

        # === Final Score ===
        total_signals = bullish_signals + bearish_signals
        if total_signals > 0:
            if bullish_signals > bearish_signals:
                confluence_score = (bullish_signals / total_signals) * 10
                bias = 'Bullish'
            else:
                confluence_score = (bearish_signals / total_signals) * 10
                bias = 'Bearish'
        else:
            confluence_score = 0
            bias = 'Neutral'

        return {
            'score': round(confluence_score, 2),
            'bias': bias,
            'bullish_signals': round(bullish_signals, 2),
            'bearish_signals': round(bearish_signals, 2)
        }

    def fetch_price_data(self, symbol, period='1mo', interval='15m'):
        """Fetch price data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period=period, interval=interval)
            if df.empty:
                print(f"No price data available for {symbol}")
                return None
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            print(f"Error fetching price data for {symbol}: {e}")
            return None

    def _check_rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        if current_time - self.last_request_time < 60:  # Within the same minute
            if self.request_count >= self.requests_per_minute:
                sleep_time = 60 - (current_time - self.last_request_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:  # New minute
            self.request_count = 0
            self.last_request_time = current_time

        self.request_count += 1

    def fetch_options_data(self, symbol):
        """Fetch options data with rate limiting"""
        self._check_rate_limit()

        url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={self.api_key}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if 'Information' in data and 'rate limit' in data[
                    'Information'].lower():
                print(f"Rate limit reached - waiting for reset...")
                time.sleep(60)  # Wait for rate limit reset
                return self.fetch_options_data(symbol)  # Retry

            if 'data' in data and data['data']:
                return pd.DataFrame(data['data'])

            print(f"No valid data for {symbol}")
            return None

        except Exception as e:
            print(f"Error fetching options data for {symbol}: {e}")
            return None

    def analyze_gaps(self, price_data):
        """Identify and track gap mitigation"""
        df = price_data.copy()

        # Get prior candle values for comparison
        df['prev_close'] = df['Close'].shift(1)
        df['prev_open'] = df['Open'].shift(1)

        # Calculate gaps
        df['gap'] = df['Open'] - df['prev_close']
        df['gap_percent'] = (df['gap'] / df['prev_close']) * 100

        # Track gap direction
        df['gap_direction'] = np.where(df['gap'] > 0, 'Up', 'Down')

        # Track gap mitigation
        df['gap_mitigated'] = False
        df['unmitigated_gap_price'] = np.nan

        # For each row, check if gap is mitigated
        for i in range(1, len(df)):
            if df.iloc[i]['gap'] != 0:  # If there's a gap
                if df.iloc[i]['gap'] > 0:  # Bullish gap
                    # Gap is mitigated if price falls back to previous close
                    df.iloc[i, df.columns.get_loc('gap_mitigated')] = df.iloc[
                        i]['Low'] <= df.iloc[i - 1]['Close']
                    if not df.iloc[i]['gap_mitigated']:
                        df.iloc[i,
                                df.columns.get_loc('unmitigated_gap_price'
                                                   )] = df.iloc[i - 1]['Close']
                else:  # Bearish gap
                    # Gap is mitigated if price rises back to previous close
                    df.iloc[i, df.columns.get_loc('gap_mitigated')] = df.iloc[
                        i]['High'] >= df.iloc[i - 1]['Close']
                    if not df.iloc[i]['gap_mitigated']:
                        df.iloc[i,
                                df.columns.get_loc('unmitigated_gap_price'
                                                   )] = df.iloc[i - 1]['Close']

        # Track number of bars since last unmitigated gap
        df['bars_since_gap'] = 0
        last_gap_idx = None
        for i in range(len(df) - 1, -1, -1):
            if pd.notna(df.iloc[i]['unmitigated_gap_price']):
                last_gap_idx = i
                df.iloc[i, df.columns.get_loc('bars_since_gap')] = 0
            elif last_gap_idx is not None:
                df.iloc[
                    i, df.columns.get_loc('bars_since_gap')] = last_gap_idx - i

        return df

    def check_candlestick_conditions(self, price_data):
        """Check various candlestick patterns"""
        df = price_data.copy()

        # Previous candle values
        df['prev_open'] = df['Open'].shift(1)
        df['prev_close'] = df['Close'].shift(1)
        df['prev_high'] = df['High'].shift(1)
        df['prev_low'] = df['Low'].shift(1)

        # Real body and shadows
        df['body'] = abs(df['Close'] - df['Open'])
        df['upper_shadow'] = df['High'] - df[['Close', 'Open']].max(axis=1)
        df['lower_shadow'] = df[['Close', 'Open']].min(axis=1) - df['Low']
        df['range'] = df['High'] - df['Low']

        # === Pattern Conditions === #

        # Bullish Engulfing
        df['bullish_engulfing'] = ((df['prev_close'] < df['prev_open'])
                                   &  # Previous red
                                   (df['Close'] > df['Open'])
                                   &  # Current green
                                   (df['Open'] < df['prev_close']) &
                                   (df['Close'] > df['prev_open']))

        # Bearish Engulfing
        df['bearish_engulfing'] = ((df['prev_close'] > df['prev_open'])
                                   &  # Previous green
                                   (df['Close'] < df['Open']) &  # Current red
                                   (df['Open'] > df['prev_close']) &
                                   (df['Close'] < df['prev_open']))

        # Hammer
        df['hammer'] = ((df['body'] <= df['range'] * 0.3) &
                        (df['lower_shadow'] >= df['body'] * 2) &
                        (df['upper_shadow'] <= df['body'] * 0.5))

        # Inverted Hammer
        df['inverted_hammer'] = ((df['body'] <= df['range'] * 0.3) &
                                 (df['upper_shadow'] >= df['body'] * 2) &
                                 (df['lower_shadow'] <= df['body'] * 0.5))

        # Shooting Star (bearish inverted hammer)
        df['shooting_star'] = ((df['body'] <= df['range'] * 0.3) &
                               (df['upper_shadow'] >= df['body'] * 2) &
                               (df['lower_shadow'] <= df['body'] * 0.2))

        # Doji
        df['doji'] = (df['body'] <= df['range'] * 0.1)

        # === Existing Matching Candle Logic === #
        df['is_prev_green'] = df['prev_close'] > df['prev_open']
        df['is_prev_red'] = df['prev_close'] < df['prev_open']
        df['bull_cond1'] = df['prev_close'] <= df['Open']
        df['bull_cond2'] = df['Open'] >= df['Low']
        df['bull_cond3'] = df['prev_close'] <= df['Low']
        df['matching_candle_bullish'] = (df['is_prev_green'] & df['bull_cond1']
                                         & df['bull_cond2'] & df['bull_cond3'])

        df['bear_cond1'] = df['prev_close'] >= df['Open']
        df['bear_cond2'] = df['Open'] <= df['High']
        df['bear_cond3'] = df['prev_close'] >= df['High']
        df['matching_candle_bearish'] = (df['is_prev_red'] & df['bear_cond1']
                                         & df['bear_cond2'] & df['bear_cond3'])

        return df

    def detect_patterns(self, price_data):
        df = price_data.copy()
        patterns = pd.DataFrame(index=df.index)

        x = np.arange(len(df))
        high_trend = stats.linregress(x, df['High'])
        low_trend = stats.linregress(x, df['Low'])

        patterns['high_slope'] = high_trend.slope
        patterns['low_slope'] = low_trend.slope
        patterns['high_r2'] = high_trend.rvalue**2
        patterns['low_r2'] = low_trend.rvalue**2

        patterns['falling_wedge'] = (
            (patterns['high_slope'] < -0.0001) &
            (patterns['low_slope'] < -0.0001) &
            (patterns['high_slope'] < patterns['low_slope']) &
            (patterns['high_r2'] > self.min_pattern_quality) &
            (patterns['low_r2'] > self.min_pattern_quality))

        patterns['rising_wedge'] = (
            (patterns['high_slope'] > 0.0001) &
            (patterns['low_slope'] > 0.0001) &
            (patterns['high_slope'] > patterns['low_slope']) &
            (patterns['high_r2'] > self.min_pattern_quality) &
            (patterns['low_r2'] > self.min_pattern_quality))

        return patterns

    def analyze_volume(self, price_data):
        df = price_data.copy()
        df['volume_sma'] = df['Volume'].expanding().mean()
        df['volume_std'] = df['Volume'].expanding().std()
        df['relative_volume'] = df['Volume'] / df['volume_sma']
        df['unusual_volume'] = df['Volume'] > (df['volume_sma'] +
                                               2 * df['volume_std'])
        return df

    def fetch_volume_profile(self,
                             symbol,
                             interval='15min',
                             price_levels=20,
                             lookback_days=10):
        """
        Volume profile using OHLC distribution (upgrade), fully backward-compatible.
        """
        self._check_rate_limit()

        try:
            url = (
                f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY'
                f'&symbol={symbol}&interval={interval}&outputsize=full&apikey={self.api_key}'
            )
            response = requests.get(url)
            data = response.json()

            if 'Error Message' in data:
                print(
                    f"Error fetching data for {symbol}: {data['Error Message']}"
                )
                return None

            key_prefix = f'Time Series ({interval})'
            if key_prefix not in data:
                print(f"No intraday data available for {symbol}")
                return None

            df = pd.DataFrame.from_dict(data[key_prefix], orient='index')
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df.apply(pd.to_numeric, errors='coerce')
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)

            df = df[df.index >= datetime.now() - timedelta(days=lookback_days)]

            if df.empty:
                print(
                    f"No data available for {symbol} in the specified time period"
                )
                return None

            price_min = df['Low'].min()
            price_max = df['High'].max()
            price_range = price_max - price_min

            if price_range == 0:
                print(f"Flat price range for {symbol}, skipping")
                return None

            level_size = price_range / price_levels
            price_levels_array = [
                price_min + (level_size * i) for i in range(price_levels + 1)
            ]

            volume_profile = {
                'price_levels': price_levels_array,
                'volumes': [0] * price_levels,
                'relative_volumes': [0] * price_levels,
                'dominant_levels': []
            }

            # More accurate distribution: split volume across OHLC range
            for _, row in df.iterrows():
                prices = [row['Open'], row['High'], row['Low'], row['Close']]
                valid_prices = [p for p in prices if not pd.isna(p)]
                if not valid_prices:
                    continue

                spread = np.linspace(min(valid_prices),
                                     max(valid_prices),
                                     num=len(valid_prices))
                volume_share = row['Volume'] / len(
                    spread) if row['Volume'] > 0 else 0

                for price in spread:
                    for i in range(price_levels):
                        if price_levels_array[i] <= price < price_levels_array[
                                i + 1]:
                            volume_profile['volumes'][i] += volume_share
                            break

            total_volume = sum(volume_profile['volumes'])
            if total_volume > 0:
                volume_profile['relative_volumes'] = [
                    (v / total_volume) * 100 for v in volume_profile['volumes']
                ]

            mean_volume = np.mean(volume_profile['volumes'])
            std_volume = np.std(volume_profile['volumes'])
            threshold = mean_volume + (1.5 * std_volume)

            for i, volume in enumerate(volume_profile['volumes']):
                if volume > threshold:
                    price_level = (price_levels_array[i] +
                                   price_levels_array[i + 1]) / 2
                    volume_profile['dominant_levels'].append({
                        'price':
                        round(price_level, 2),
                        'volume':
                        int(volume),
                        'percentage':
                        round(volume_profile['relative_volumes'][i], 2)
                    })

            return volume_profile

        except Exception as e:
            print(f"Error creating volume profile for {symbol}: {e}")
            return None

    def analyze_with_volume_profile(self, symbol, analysis_results):
        """
      Enhance analysis with volume profile data
      """
        # Get volume profile for intraday timeframes from TIMEFRAMES dict
        volume_profiles = {}

        # Extract intraday timeframes only (daily/weekly don't work with volume profiles)
        intraday_timeframes = [
            tf for tf, config in TIMEFRAMES.items()
            if config['function'] == 'TIME_SERIES_INTRADAY'
        ]

        for tf in intraday_timeframes:
            # Convert timeframe key to interval format
            interval = TIMEFRAMES[tf]['interval']
            volume_profiles[interval] = self.fetch_volume_profile(
                symbol, interval=interval)

        # Rest of the function remains the same
        confluences = []

        # Check if any key levels from volume profile match gap levels
        for tf, results in analysis_results.items():
            if 'gap_percent' in results and abs(results['gap_percent']) > 0:
                gap_price = results['unmitigated_gap_price']
                if pd.isna(gap_price):
                    continue

                # Check if gap aligns with a high volume node
                for profile_tf, profile in volume_profiles.items():
                    if profile and 'dominant_levels' in profile:
                        for level in profile['dominant_levels']:
                            # If gap price is near a high volume node (+/- 1%)
                            price_diff_percent = abs(
                                (level['price'] - gap_price) / gap_price * 100)
                            if price_diff_percent < 1.0:
                                confluences.append({
                                    'type':
                                    'gap_volume_confluence',
                                    'gap_timeframe':
                                    tf,
                                    'volume_timeframe':
                                    profile_tf,
                                    'gap_price':
                                    gap_price,
                                    'volume_level':
                                    level['price'],
                                    'volume_strength':
                                    level['percentage']
                                })

        return {'volume_profiles': volume_profiles, 'confluences': confluences}

    def print_multi_timeframe_analysis(self, symbol, analysis_results,
                                       confluence):
        """Print detailed multi-timeframe analysis"""
        print(f"\n=== {symbol} Multi-Timeframe Analysis ===")
        print(
            f"Overall Confluence Score: {confluence['score']}/10 ({confluence['bias']})"
        )
        print(f"Bullish Signals: {confluence['bullish_signals']}")
        print(f"Bearish Signals: {confluence['bearish_signals']}\n")

        headers = [
            'Timeframe', 'Gap %', 'Direction', 'Patterns', 'Candles', 'Volume'
        ]
        rows = []

        for tf, data in analysis_results.items():
            patterns = []
            if data['patterns']['falling_wedge']:
                patterns.append('Falling Wedge')
            if data['patterns']['rising_wedge']:
                patterns.append('Rising Wedge')

            candles = []
            if data['candles']['bullish']:
                candles.append('Bullish')
            if data['candles']['bearish']:
                candles.append('Bearish')

            rows.append([
                tf, f"{data['gap_percent']:.2f}%", data['gap_direction'],
                ', '.join(patterns) if patterns else 'None',
                ', '.join(candles) if candles else 'None',
                'Unusual' if data['volume']['unusual_volume'] else 'Normal'
            ])

        print(tabulate(rows, headers=headers, tablefmt='pretty'))

    def screen_options(self,
                       options_data,
                       price_analysis,
                       min_price=None,
                       max_price=None,
                       iv_percentile_threshold=None,
                       time_to_expiry_range=None):
        """
        Filters options by price, delta, IV percentile, and days to expiration.
        Returns scored candidates.
        """
        if options_data is None or options_data.empty:
            return pd.DataFrame()

        required_cols = {
            'strike', 'type', 'expiration', 'delta', 'gamma', 'theta',
            'implied_volatility', 'mark'
        }
        if not required_cols.issubset(options_data.columns):
            print(
                f"Error: Options data missing required columns. Found columns: {list(options_data.columns)}"
            )
            return pd.DataFrame()

        # Convert expiration to datetime
        options_data['expiration'] = pd.to_datetime(options_data['expiration'],
                                                    errors='coerce')

        # Start with a copy before filtering
        filtered_data = options_data.copy()

        # === Time to expiry filter ===
        if time_to_expiry_range:
            filtered_data['days_to_expiration'] = (
                filtered_data['expiration'] - datetime.now()).dt.days
            filtered_data = filtered_data[(
                filtered_data['days_to_expiration'] >= time_to_expiry_range[0]
            ) & (filtered_data['days_to_expiration'] <= time_to_expiry_range[1]
                 )]

        # === IV percentile filter ===
        if iv_percentile_threshold is not None and 'iv_percentile' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['iv_percentile'] >=
                                          iv_percentile_threshold]

        # Field normalization
        field_mapping = {'implied_volatility': 'implied_vol', 'mark': 'price'}
        for old_name, new_name in field_mapping.items():
            if old_name in filtered_data.columns and new_name not in filtered_data.columns:
                filtered_data[new_name] = filtered_data[old_name]

        # Convert numeric fields
        numeric_cols = [
            'strike', 'delta', 'gamma', 'theta', 'vega', 'implied_vol', 'price'
        ]
        for col in numeric_cols:
            if col in filtered_data.columns:
                filtered_data[col] = pd.to_numeric(filtered_data[col],
                                                   errors='coerce')

        # Price filtering
        if min_price is not None:
            filtered_data = filtered_data[filtered_data['price'] >= min_price]
        if max_price is not None:
            filtered_data = filtered_data[filtered_data['price'] <= max_price]

        # Delta filtering
        mask = ((filtered_data['delta'].abs() >= self.min_delta) &
                (filtered_data['delta'].abs() <= self.max_delta))
        candidates = filtered_data[mask].copy()

        if not candidates.empty:
            candidates['score'] = candidates.apply(
                lambda x: self._score_option(x, price_analysis), axis=1)
            return candidates.sort_values('score', ascending=False)

        return pd.DataFrame()

    def _score_option(self, option, price_analysis):
        """Score individual options"""
        try:
            # Delta score (preference for options closer to 0.4 delta)
            delta_score = 1 - abs(abs(float(option['delta'])) - 0.6)

            # Gamma/Theta ratio (preference for high gamma relative to theta)
            gamma = abs(float(option['gamma']))
            theta = abs(float(option['theta']))
            gamma_theta_ratio = gamma / theta if theta != 0 else 0

            # Volume score (preference for higher volume)
            volume = float(option['volume'])
            volume_score = min(volume / self.min_volume, 1.0)

            # Combine scores with weights
            total_score = (delta_score * 0.6 + gamma_theta_ratio * 0.4 +
                           volume_score * 0.2)

            return round(total_score, 4)
        except Exception as e:
            print(f"Error calculating option score: {e}")
            return 0.0

    def analyze_oi_skew(self, options_df):
        """
        Analyze Put/Call open interest ratio for directional sentiment.
        Returns skew ratio and bias interpretation.
        """
        if options_df is None or options_df.empty:
            return {'put_call_ratio': None, 'bias': 'Unknown'}

        # Normalize type field and open_interest to ensure numeric
        options_df = options_df.copy()
        options_df['type'] = options_df['type'].str.lower().fillna('')
        options_df['open_interest'] = pd.to_numeric(
            options_df['open_interest'], errors='coerce').fillna(0)

        total_put_oi = options_df[options_df['type'] ==
                                  'put']['open_interest'].sum()
        total_call_oi = options_df[options_df['type'] ==
                                   'call']['open_interest'].sum()

        if total_call_oi == 0:
            return {'put_call_ratio': None, 'bias': 'Invalid'}

        ratio = total_put_oi / total_call_oi

        if ratio > 1.3:
            bias = 'Bearish Skew'
        elif ratio < 0.7:
            bias = 'Bullish Skew'
        else:
            bias = 'Neutral Skew'

        return {'put_call_ratio': round(ratio, 2), 'bias': bias}


def print_volume_profile(symbol, volume_profile, tf='15min'):
    """Display simplified volume profile summary"""
    if not volume_profile or 'volume_profiles' not in volume_profile or tf not in volume_profile[
            'volume_profiles']:
        return

    profile = volume_profile['volume_profiles'][tf]
    if not profile or not profile.get('dominant_levels'):
        return

    print(f"\n📊 {symbol} Key Volume Levels ({tf}):")
    
    # Show only top 3 dominant levels
    top_levels = sorted(profile['dominant_levels'], 
                       key=lambda x: x['percentage'], reverse=True)[:3]
    
    for i, level in enumerate(top_levels, 1):
        print(f"  {i}. ${level['price']:.2f} ({level['percentage']:.1f}% volume)")
    
    # Show volume confluence if multiple timeframes agree
    if len(profile['dominant_levels']) > 2:
        print(f"  💡 Strong volume confluence at {len(profile['dominant_levels'])} levels")


def calculate_hold_time(days_to_expiry, delta, implied_vol):
    """Calculate maximum hold time based on option characteristics"""
    if days_to_expiry <= 2:  # This week's expiry
        base_hours = 4
    elif days_to_expiry <= 7:  # Next week's expiry
        base_hours = 6
    elif days_to_expiry <= 14:  # Two weeks out
        base_hours = 8
    else:
        base_hours = 12

    # Adjust for delta and volatility
    if delta > 0.5:
        base_hours = max(4, base_hours - 2)
    if implied_vol > 0.8:
        base_hours = max(4, base_hours - 2)

    return base_hours


def generate_trade_plan(option_data, symbol_data, capital_per_trade=50):
    """
    Generate a realistic and logical trading plan based on:
    - Option metrics
    - User-defined capital allocation
    - Technical price levels (if available)
    - Timeframe preference (intraday/swing)
    """
    if option_data is None or not isinstance(symbol_data, dict):
        print("Invalid input passed to generate_trade_plan")
        return None

    try:
        ask_price = float(option_data.get("ask", option_data.get("price",
                                                                 0.5)))
        strike_price = float(option_data.get("strike"))
        option_type = option_data.get("type", "call").lower()
        expiration = pd.to_datetime(
            option_data.get("expiration")).strftime("%Y-%m-%d")
        delta = float(option_data.get("delta", 0))
        gamma = float(option_data.get("gamma", 0))
        theta = float(option_data.get("theta", 0))
        score = float(option_data.get("score", 0))
        implied_vol = float(option_data.get("implied_volatility", 0))

        entry_price = round(ask_price, 2)
        stop_loss = round(entry_price * 0.75, 2)
        target_price = round(entry_price * 1.75, 2)
        final_target = round(entry_price * 3.5, 2)

        risk_per_contract = max(entry_price - stop_loss, 0.01) * 100
        position_size = max(1, int(capital_per_trade // risk_per_contract))

        days_to_expiry = (pd.to_datetime(expiration) -
                          pd.Timestamp.today()).days
        hold_hours = calculate_hold_time(days_to_expiry, abs(delta),
                                         implied_vol)
        max_hold_time = f"{hold_hours} hours" if hold_hours < 24 else f"{hold_hours // 24} day(s)"

        plan = {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "initial_target": target_price,
            "final_target": final_target,
            "position_size": position_size,
            "max_hold_time": max_hold_time,
            "support": symbol_data.get("support"),
            "resistance": symbol_data.get("resistance"),
            "skew": f"{symbol_data.get('skew', 'Neutral')} Skew",
            "strike": f"${strike_price}",
            "type": option_type.capitalize(),
            "expiration": expiration,
            "risk_metrics": {
                "delta_exposure": round(delta * position_size * 100, 2),
                "gamma_theta_ratio":
                round(gamma / abs(theta), 2) if theta else 0.0,
                "implied_vol": round(implied_vol * 100, 2)
            },
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "score": score,
            "bias": symbol_data.get("bias", "N/A"),
            "option_symbol": option_data.get("symbol", "N/A")
        }

        return plan

    except Exception as e:
        print(f"Error generating trade plan: {e}")
        return None


def process_stock_list(text):
    """Process input stock list"""
    symbols = []
    for delimiter in [',', '\n', ' ', ';', '\t']:
        if delimiter in text:
            symbols.extend([
                s.strip().upper() for s in text.split(delimiter) if s.strip()
            ])
    return list(dict.fromkeys(symbols))  # Remove duplicates


def print_analysis(symbol,
                   gap,
                   candidates,
                   trade_plan,
                   volume_profile=None,
                   skew=None):
    """Print detailed analysis with enhanced metrics and skew"""
    print(f"\n=== {symbol} Analysis ===")
    print(f"Gap: {gap['gap_percent']:.2f}%")

    if skew:
        print(f"Put/Call Skew: {skew['put_call_ratio']} ({skew['bias']})")

    if candidates is not None and not candidates.empty:
        print("\nTop Options Candidates:")
        print(
            tabulate(candidates[[
                'strike', 'type', 'expiration', 'delta', 'gamma', 'theta',
                'score'
            ]].head(),
                     headers='keys',
                     tablefmt='pretty',
                     floatfmt=".2f"))

        print("\nRecommended Trade Plan:")
        print(
            tabulate(
                [["Entry Price", f"${trade_plan['entry_price']:.2f}"],
                 ["Stop Loss", f"${trade_plan['stop_loss']:.2f}"],
                 ["Initial Target", f"${trade_plan['initial_target']:.2f}"],
                 ["Final Target", f"${trade_plan['final_target']:.2f}"],
                 ["Position Size", f"{trade_plan['position_size']} contracts"],
                 ["Max Hold Time", trade_plan['max_hold_time']],
                 [
                     "Delta Exposure",
                     f"${trade_plan['risk_metrics']['delta_exposure']:.2f}"
                 ],
                 [
                     "Gamma/Theta",
                     f"{trade_plan['risk_metrics']['gamma_theta_ratio']}"
                 ],
                 [
                     "Implied Vol",
                     f"{trade_plan['risk_metrics']['implied_vol']}%"
                 ]],
                tablefmt='pretty'))

        # Volume confluence output
        if volume_profile and 'volume_confluences' in trade_plan and trade_plan[
                'volume_confluences']:
            print("\nVolume Confluences:")
            for conf in trade_plan['volume_confluences']:
                print(
                    f"- {conf['type']} at ${conf['volume_level']:.2f} ({conf['volume_strength']:.1f}% of volume)"
                )
    else:
        print("No valid options found matching criteria")


def summarize_results(results):
    """Generate summary of all opportunities with enhanced metrics and OI skew"""
    if not results:
        print("\nNo valid opportunities found.")
        return

    summary = []
    for symbol, data in results.items():
        # Confluence
        bias = data['confluence']['bias'] if 'confluence' in data else 'N/A'
        score = f"{data['confluence']['score']:.1f}" if 'confluence' in data else 'N/A'

        # Gap analysis
        gap = "N/A"
        gap_price = "N/A"
        for tf in ['15m', '30m', '1h']:
            if tf in data['timeframe_analysis'] and 'gap_percent' in data[
                    'timeframe_analysis'][tf]:
                gap_val = data['timeframe_analysis'][tf]['gap_percent']
                if not pd.isna(gap_val):
                    gap = f"{gap_val:.1f}%"
                    gap_price_val = data['timeframe_analysis'][tf].get(
                        'unmitigated_gap_price')
                    gap_price = f"${gap_price_val:.2f}" if gap_price_val and not pd.isna(
                        gap_price_val) else "N/A"
                    break

        # Volume confluence
        vol_conf = "No"
        if ('volume_profile' in data
                and isinstance(data['volume_profile'], dict)
                and 'confluences' in data['volume_profile']
                and len(data['volume_profile']['confluences']) > 0):
            vol_conf = f"Yes ({len(data['volume_profile']['confluences'])})"

        # Trade Plan
        trade_plan = data.get('trade_plan', {})
        entry_price = f"${trade_plan['entry_price']:.2f}" if 'entry_price' in trade_plan else "N/A"
        rr = f"{trade_plan['risk_reward']:.2f}:1" if 'risk_reward' in trade_plan else "N/A"

        # OI Skew
        oi_skew = data.get('oi_skew', {})
        oi_bias = oi_skew.get('bias', 'N/A')
        oi_ratio = oi_skew.get('put_call_ratio', 'N/A')

        summary.append({
            'Symbol': symbol,
            'Bias': bias,
            'Score': score,
            'Gap %': gap,
            'Gap Price': gap_price,
            'Entry': entry_price,
            'R/R': rr,
            'Skew': oi_bias,
            'Put/Call': f"{oi_ratio}" if oi_ratio != 'N/A' else "N/A",
            'Confluence': f"{score}/10",
            'Vol Confirmation': vol_conf
        })

    print("\n=== Summary of Trading Opportunities ===")
    print(
        tabulate(summary,
                 headers='keys',
                 tablefmt='pretty',
                 numalign='right',
                 stralign='left'))

    return summary


def save_to_drive(results):
    """Enhanced save function with detailed options data"""
    try:
        base_dir = './TradingPlans'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save detailed data
        save_detailed_options_data(results, base_dir, timestamp)

        # Save summary
        summary_filepath = os.path.join(base_dir,
                                        f'trading_plans_{timestamp}.txt')
        save_summary_report(results, summary_filepath)

        # Convert numpy types and save as JSON
        json_filepath = os.path.join(base_dir,
                                     f'trading_plans_{timestamp}.json')
        converted_results = convert_numpy_types(results)

        with open(json_filepath, 'w') as f:
            json.dump(converted_results, f, indent=2, default=str)

        print(f"Successfully saved data to:\n{json_filepath}")
        return summary_filepath

    except Exception as e:
        print(f"Error saving to Google Drive: {e}")
        return None


def save_individual_result(symbol, result_data, base_dir='./TradingPlans'):
    """Save individual result immediately when found"""
    try:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # Create a filename with current date
        date_str = datetime.now().strftime('%Y-%m-%d')
        individual_file = os.path.join(base_dir, f'progressive_results_{date_str}.json')
        
        # Load existing data or create new
        if os.path.exists(individual_file):
            with open(individual_file, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}
        
        # Add the new result
        existing_data[symbol] = convert_numpy_types(result_data)
        
        # Save back to file
        with open(individual_file, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)
        
        print(f"✅ Saved {symbol} to {individual_file}")
        
        # Also append to human-readable format
        human_readable_file = os.path.join(base_dir, f'progressive_plans_{date_str}.txt')
        with open(human_readable_file, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Symbol: {symbol} - {datetime.now().strftime('%H:%M:%S')}\n")
            f.write(f"Confluence Score: {result_data.get('confluence', {}).get('score', 'N/A')}/10\n")
            f.write(f"Bias: {result_data.get('confluence', {}).get('bias', 'N/A')}\n")
            
            # Add options details
            if 'options' in result_data and not isinstance(result_data['options'], bool) and not result_data['options'].empty:
                f.write(f"\nTop Options Found: {len(result_data['options'])}\n")
                
                # Show top 3 options
                for i, option in enumerate(result_data['options'].head(3).itertuples(), 1):
                    f.write(f"\nOption {i}:\n")
                    f.write(f"  Strike: ${option.strike} {option.type.capitalize()}\n")
                    f.write(f"  Expiration: {option.expiration}\n")
                    f.write(f"  Delta: {option.delta:.4f}\n")
                    f.write(f"  Gamma: {option.gamma:.4f}\n")
                    f.write(f"  Theta: {option.theta:.4f}\n")
                    f.write(f"  Volume: {option.volume}\n")
                    f.write(f"  Score: {option.score:.2f}\n")
                    if hasattr(option, 'implied_volatility'):
                        f.write(f"  IV: {option.implied_volatility:.2%}\n")
            
            if 'trade_plan' in result_data and result_data['trade_plan']:
                tp = result_data['trade_plan']
                f.write(f"\nTrade Plan:\n")
                f.write(f"  Entry: ${tp.get('entry_price', 0):.2f}\n")
                f.write(f"  Stop: ${tp.get('stop_loss', 0):.2f}\n")
                f.write(f"  Target: ${tp.get('initial_target', 0):.2f}\n")
                f.write(f"  Position Size: {tp.get('position_size', 0)} contracts\n")
                f.write(f"  Strike: {tp.get('strike', 'N/A')} {tp.get('type', 'N/A').capitalize()}\n")
                f.write(f"  Expiration: {tp.get('expiration', 'N/A')}\n")
                f.write(f"  Max Hold: {tp.get('max_hold_time', 'N/A')}\n")
            
            f.write(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving individual result for {symbol}: {e}")
        return False


def save_detailed_options_data(results, base_dir, timestamp):
    """Save detailed options data to a separate file"""
    options_filepath = os.path.join(base_dir, f'options_data_{timestamp}.txt')

    with open(options_filepath, 'w') as f:
        f.write("=== Detailed Options Analysis ===\n\n")

        for symbol, data in results.items():
            f.write(f"\n{'='*50}\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Analysis Date: {timestamp}\n")

            # FIX: Check if options exists and is not empty
            if 'options' in data and not isinstance(
                    data['options'], bool) and not data['options'].empty:
                f.write("\nOptions Chain Analysis:\n")
                for idx, option in enumerate(data['options'].itertuples(), 1):
                    f.write(f"\nOption {idx}:\n")
                    f.write(f"Strike: ${option.strike}\n")
                    f.write(f"Type: {option.type}\n")
                    f.write(f"Expiration: {option.expiration}\n")
                    f.write(f"Delta: {option.delta:.4f}\n")
                    f.write(f"Gamma: {option.gamma:.4f}\n")
                    f.write(f"Theta: {option.theta:.4f}\n")
                    if hasattr(option, 'implied_vol'):
                        f.write(f"IV: {option.implied_vol:.2f}%\n")
                    elif hasattr(option, 'implied_volatility'):
                        f.write(f"IV: {option.implied_volatility:.2f}%\n")
                    f.write(f"Volume: {option.volume}\n")
                    f.write(f"Score: {option.score:.4f}\n")

            # Add volume profile data if available
            if ('volume_profile' in data
                    and isinstance(data['volume_profile'], dict)
                    and 'volume_profiles' in data['volume_profile']):

                f.write("\nVolume Profile Analysis:\n")
                for tf, profile in data['volume_profile'][
                        'volume_profiles'].items():
                    if profile and 'dominant_levels' in profile:
                        f.write(f"\n{tf} Timeframe Dominant Volume Levels:\n")
                        for level in profile['dominant_levels']:
                            f.write(
                                f"${level['price']:.2f} - {level['percentage']:.1f}% of total volume\n"
                            )

                if ('confluences' in data['volume_profile'] and isinstance(
                        data['volume_profile']['confluences'], list)
                        and data['volume_profile']['confluences']):

                    f.write("\nVolume-Price Confluences:\n")
                    for conf in data['volume_profile']['confluences']:
                        f.write(
                            f"- {conf['type']} at ${conf['volume_level']:.2f} ({conf['volume_strength']:.1f}% of volume)\n"
                        )


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    import numpy as np
    import pandas as pd

    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32,
                        np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj
                ]  # Fixed: 'item in obj' instead of 'item in item'
    elif pd.isna(obj):
        return None
    return obj


def format_trade_plan_for_output(symbol: str,
                                 plan: dict,
                                 save_path: str = None,
                                 verbose: bool = True) -> str:
    if not plan:
        return f"⚠️ No trade plan available for {symbol}"

    output = f"""
📈 Trade Plan for {symbol} ({plan.get("bias", "N/A").capitalize()} Bias)

🔹 Option: ${plan.get("strike")} {plan.get("type", "").capitalize()} expiring {plan.get("expiration")}
🔹 Entry Price: ${plan.get("entry_price", 0):.2f}
🔹 Stop Loss: ${plan.get("stop_loss", 0):.2f}
🔹 Initial Target: ${plan.get("initial_target", 0):.2f}
🔹 Final Target: ${plan.get("final_target", 0):.2f}
🔹 Position Size: {plan.get("position_size", 0)} contracts
🔹 Max Hold Time: {plan.get("max_hold_time", "N/A")}
🔹 Delta Exposure: ${plan.get("delta_exposure", 0):,.2f}
🔹 Gamma/Theta Ratio: {plan.get("gamma_theta_ratio", "N/A")}
🔹 Implied Volatility: {plan.get("implied_vol", "N/A")}

🧠 Option Metrics:
Delta: {plan.get("delta", 0):.5f} | Gamma: {plan.get("gamma", 0):.5f} | Theta: {plan.get("theta", 0):.5f} | Score: {plan.get("score", 0):.2f}
""".strip()

    if verbose:
        print(output)

    if save_path:
        with open(save_path, "a") as f:
            f.write(output + "\n\n" + "=" * 80 + "\n\n")

    return output


def discover_optionable_explosive_stocks(limit=50):
    """
    Discover high-momentum stocks by scraping a screener site.
    Returns a filtered list of tickers.
    """
    url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers&f=optionable"
    print("Fetching stock screener data...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    try:
        tables = pd.read_html(str(soup))
    except Exception as e:
        print("pandas.read_html failed:", e)
        return []

    if not tables:
        print("No tables found.")
        return []

    df = tables[0]
    print("Table columns:", df.columns.tolist())
    print("Table preview:\n", df.head())

    expected_cols = ['Ticker', 'Change', 'Volume', 'Price']
    available_cols = df.columns.tolist()
    matched_cols = [col for col in expected_cols if col in available_cols]

    if not matched_cols or 'Ticker' not in matched_cols:
        print("Required columns not found. Aborting.")
        return []

    df = df[matched_cols]
    tickers = df['Ticker'].dropna().unique().tolist()
    tickers = tickers[:limit]

    print(f"{len(tickers)} tickers discovered.")
    return tickers


def run_scanner(symbols=None,
                min_delta=0.2,
                max_delta=0.45,
                min_price=None,
                max_price=None,
                time_to_expiry_range=(1, 30),
                iv_percentile_threshold=None):
    """Enhanced scanner with expiration selection and volume profile analysis"""
    scanner = CompleteOptionsScanner(ALPHA_VANTAGE_API_KEY,
                                     min_delta=min_delta,
                                     max_delta=max_delta)
    
    # Filter out problematic symbols upfront
    if symbols:
        # Remove symbols with special characters that cause API issues
        filtered_symbols = []
        skip_patterns = ['+', 'W', 'WS', 'WT']  # Warrants and rights often cause issues
        
        for symbol in symbols:
            if not any(pattern in symbol for pattern in skip_patterns):
                filtered_symbols.append(symbol)
            else:
                print(f"⏭️  Skipping {symbol} (warrant/right)")
        
        symbols = filtered_symbols[:30]  # Limit to 30 symbols for faster processing
        print(f"🔍 Processing {len(symbols)} filtered symbols...")

    if symbols is None:
        print("Paste your stock list (any format):")
        stock_text = input()
        symbols = process_stock_list(stock_text)

    print(
        f"\nAnalyzing {len(symbols)} symbols across {len(TIMEFRAMES)} timeframes..."
    )
    print(f"Looking for options expiring: {time_to_expiry_range}")

    results = {}

    for symbol in tqdm(symbols, desc="Scanning"):
        try:
            # Quick pre-filter: try to fetch just daily data first
            daily_data = scanner.fetch_alpha_vantage_data(symbol, 'D')
            if daily_data is None or daily_data.empty:
                print(f"⚠️  No daily data for {symbol}, skipping...")
                continue
            
            # If daily data exists, proceed with full analysis
            multi_tf_data = scanner.fetch_multi_timeframe_data(symbol)
            if not multi_tf_data or len(multi_tf_data) < 2:  # Need at least 2 timeframes
                continue

            analysis_results = scanner.analyze_timeframes(symbol, multi_tf_data)
            confluence = scanner.calculate_pattern_confluence(analysis_results)

            # Skip volume analysis for low-scoring symbols to save time
            volume_analysis = None
            if confluence['score'] >= 6.0:
                volume_analysis = scanner.analyze_with_volume_profile(symbol, analysis_results)

            # Integrate volume profile with confluence score
            if volume_analysis and 'confluences' in volume_analysis:
                # Adjust confluence score based on volume profile analysis
                volume_confluence_count = len(volume_analysis['confluences'])
                if volume_confluence_count > 0:
                    # Increase confluence score if volume supports the same bias
                    if confluence['bias'] == 'Bullish':
                        confluence[
                            'bullish_signals'] += volume_confluence_count * 0.5
                    elif confluence['bias'] == 'Bearish':
                        confluence[
                            'bearish_signals'] += volume_confluence_count * 0.5

                    # Recalculate overall score
                    total_signals = confluence['bullish_signals'] + confluence[
                        'bearish_signals']
                    if total_signals > 0:
                        if confluence['bullish_signals'] > confluence[
                                'bearish_signals']:
                            confluence['score'] = (
                                confluence['bullish_signals'] /
                                total_signals) * 10
                            confluence['bias'] = 'Bullish'
                        else:
                            confluence['score'] = (
                                confluence['bearish_signals'] /
                                total_signals) * 10
                            confluence['bias'] = 'Bearish'
                    confluence['score'] = round(confluence['score'], 2)

            # Only show detailed analysis for high-scoring symbols
            if confluence['score'] >= 7.0:
                scanner.print_multi_timeframe_analysis(symbol, analysis_results, confluence)
                
                # Show gap info more concisely
                gap_info = "No gap"
                if '15m' in analysis_results and analysis_results['15m']['gap_percent'] != 0:
                    gap_info = f"{analysis_results['15m']['gap_percent']:.2f}% gap"
                elif 'D' in analysis_results and analysis_results['D']['gap_percent'] != 0:
                    gap_info = f"{analysis_results['D']['gap_percent']:.2f}% daily gap"
                
                print(f"\n🎯 {symbol}: {confluence['score']:.1f}/10 {confluence['bias']} | {gap_info}")

                # Show only the most relevant volume profile (15m or 1h)
                if volume_analysis and 'volume_profiles' in volume_analysis:
                    for tf in ['15m', '1h']:  # Priority order
                        if tf in volume_analysis['volume_profiles'] and volume_analysis['volume_profiles'][tf]:
                            print_volume_profile(symbol, volume_analysis, tf=tf)
                            break
            else:
                # Just show a brief summary for lower scoring symbols
                print(f"⚪ {symbol}: {confluence['score']:.1f}/10 {confluence['bias']} (below threshold)")

            if confluence['score'] >= 7.0:
                options_data = scanner.fetch_options_data(symbol)
                oi_skew = scanner.analyze_oi_skew(options_data)
                options_count = len(options_data) if (
                    options_data is not None and not options_data.empty) else 0
                print(f"Options Data Fetched: {options_count} contracts")

                if options_data is not None and not options_data.empty:
                    candidates = scanner.screen_options(options_data,
                                                        analysis_results,
                                                        min_price=min_price,
                                                        max_price=max_price)

                    if not candidates.empty:
                        expected_cols = [
                            'strike', 'type', 'expiration', 'delta', 'gamma',
                            'theta', 'score'
                        ]
                        if set(expected_cols).issubset(candidates.columns):
                            print("\nTop Options Candidates:")
                            print(
                                tabulate(candidates[expected_cols].head(),
                                         headers='keys',
                                         tablefmt='pretty',
                                         floatfmt=".2f"))
                        else:
                            print(
                                "Candidates DataFrame is missing some expected columns. Available columns:",
                                list(candidates.columns))

                        # Generate trade plan for the top candidate
                        symbol_context = {
                            "support": None,
                            "resistance": None,
                            "skew": oi_skew["bias"] if oi_skew else "Neutral",
                            "bias": confluence["bias"]
                        }

                        trade_plan = generate_trade_plan(
                            candidates.iloc[0], symbol_context)
                        output_file = "./TradingPlans/human_readable_plans.txt"
                        formatted = format_trade_plan_for_output(
                            symbol, trade_plan, save_path=output_file)
                        if trade_plan is None:
                            print(
                                f"Trade plan could not be generated for {symbol}"
                            )
                        print("\nRecommended Trade Plan:")
                        print(
                            tabulate([
                                [
                                    "Entry Price",
                                    f"${trade_plan['entry_price']:.2f}"
                                ],
                                [
                                    "Stop Loss",
                                    f"${trade_plan['stop_loss']:.2f}"
                                ],
                                [
                                    "Initial Target",
                                    f"${trade_plan['initial_target']:.2f}"
                                ],
                                [
                                    "Final Target",
                                    f"${trade_plan['final_target']:.2f}"
                                ],
                                [
                                    "Position Size",
                                    f"{trade_plan['position_size']} contracts"
                                ],
                                ["Max Hold Time", trade_plan['max_hold_time']],
                                [
                                    "Delta Exposure",
                                    f"${trade_plan['risk_metrics']['delta_exposure']:.2f}"
                                ],
                                [
                                    "Gamma/Theta",
                                    f"{trade_plan['risk_metrics']['gamma_theta_ratio']}"
                                ],
                                [
                                    "Implied Vol",
                                    f"{trade_plan['risk_metrics']['implied_vol']}%"
                                ]
                            ],
                                     tablefmt='pretty'))

                        result_data = {
                            'timeframe_analysis': analysis_results,
                            'confluence': confluence,
                            'volume_profile': volume_analysis,
                            'options': candidates,
                            'trade_plan': trade_plan,
                            'oi_skew': oi_skew
                        }
                        
                        results[symbol] = result_data
                        
                        # Save this result immediately
                        save_individual_result(symbol, result_data)
                    else:
                        print("No valid options found matching criteria")
                else:
                    print("No options data found for", symbol)

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            continue

    return results


def filter_options_by_bias(candidates_df, symbol_bias):
    """
    Filters the options DataFrame to match the directional bias.
    - Bullish bias -> Call options only
    - Bearish bias -> Put options only
    - Neutral -> No filtering
    """
    if candidates_df is None or candidates_df.empty:
        return candidates_df

    bias = symbol_bias.lower()
    if "bullish" in bias:
        return candidates_df[candidates_df["type"] == "call"]
    elif "bearish" in bias:
        return candidates_df[candidates_df["type"] == "put"]
    return candidates_df  # For neutral or unknown, return all


def select_top_option_candidate(candidates_df, analysis_results, symbol):
    """
    Select the best option candidate matching the symbol bias.
    Falls back to highest scoring if none match.
    """
    bias = analysis_results.get("bias", "neutral").lower()
    filtered_candidates = filter_options_by_bias(candidates_df, bias)

    if not filtered_candidates.empty:
        top_option = filtered_candidates.sort_values(by="score",
                                                     ascending=False).iloc[0]
    else:
        top_option = candidates_df.sort_values(by="score",
                                               ascending=False).iloc[0]
        print(
            f"⚠️ No {bias} option found for {symbol}. Using fallback ({top_option['type']}) with score {top_option['score']:.2f}"
        )

    return top_option


def save_summary_report(results, filepath):
    """Save a summary report of trading plans with volume profile data"""
    with open(filepath, 'w') as f:
        f.write("=== Trading Plans Summary ===\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Symbols Analyzed: {len(results)}\n\n")

        f.write(
            "Symbol | Bias | Score | Pattern | Gap % | Vol Conf | Option | Strike | Exp | Price\n"
        )
        f.write(
            "-------|------|-------|---------|-------|----------|--------|--------|-----|------\n"
        )

        for symbol, data in results.items():
            # Get basic data
            bias = data['confluence']['bias'] if 'confluence' in data else 'N/A'
            score = f"{data['confluence']['score']:.1f}" if 'confluence' in data else 'N/A'

            # Get pattern data
            patterns = []
            for tf, tf_data in data['timeframe_analysis'].items():
                if 'patterns' in tf_data:
                    if tf_data['patterns']['falling_wedge']:
                        patterns.append(f"{tf}: Falling Wedge")
                    if tf_data['patterns']['rising_wedge']:
                        patterns.append(f"{tf}: Rising Wedge")
            pattern_str = "; ".join(patterns[:2])  # Limit to 2 patterns

            # Get gap data
            gap = "N/A"
            for tf in ['15m', '30m', '1h']:
                if tf in data['timeframe_analysis'] and 'gap_percent' in data[
                        'timeframe_analysis'][tf]:
                    gap_val = data['timeframe_analysis'][tf]['gap_percent']
                    if not pd.isna(gap_val):
                        gap = f"{gap_val:.1f}%"
                        break

            # Volume confirmation
            vol_conf = "No"
            if ('volume_profile' in data
                    and isinstance(data['volume_profile'], dict)
                    and 'confluences' in data['volume_profile']
                    and len(data['volume_profile']['confluences']) > 0):
                vol_conf = "Yes"

            # Options data
            option_type = "N/A"
            strike = "N/A"
            expiry = "N/A"
            price = "N/A"

            if ('options' in data and not isinstance(data['options'], bool)
                    and not data['options'].empty
                    and len(data['options']) > 0):

                top_option = select_top_option_candidate(
                    data['options'], data['confluence'], symbol)
                option_type = top_option[
                    'type'] if 'type' in top_option else "N/A"
                strike = f"${top_option['strike']:.2f}" if 'strike' in top_option else "N/A"

                # Handle Timestamp objects for expiration
                if 'expiration' in top_option:
                    if isinstance(top_option['expiration'], pd.Timestamp):
                        expiry = top_option['expiration'].strftime('%Y-%m-%d')
                    else:
                        # Handle string type
                        expiry = str(top_option['expiration']).split()[0]

                price = f"${top_option['lastPrice']:.2f}" if 'lastPrice' in top_option else "N/A"

            # Write the line
            f.write(
                f"{symbol} | {bias} | {score} | {pattern_str[:20]} | {gap} | {vol_conf} | {option_type} | {strike} | {expiry} | {price}\n"
            )

        # Add detailed volume profile section
        f.write("\n\n=== Volume Profile Details ===\n\n")
        for symbol, data in results.items():
            if ('volume_profile' in data
                    and isinstance(data['volume_profile'], dict)
                    and 'volume_profiles' in data['volume_profile']):

                f.write(f"\n{symbol} Volume Levels:\n")
                f.write("Timeframe | Price Level | Volume % | Dominant\n")
                f.write("----------|-------------|----------|----------\n")

                for tf, profile in data['volume_profile'][
                        'volume_profiles'].items():
                    if profile and 'price_levels' in profile and 'relative_volumes' in profile:
                        # Get dominant levels for quick reference
                        dominant_prices = []
                        if 'dominant_levels' in profile:
                            dominant_prices = [
                                level['price']
                                for level in profile['dominant_levels']
                            ]

                        # Show top 5 volume levels by percentage
                        price_vol_pairs = []
                        for i in range(len(profile['relative_volumes'])):
                            mid_price = (profile['price_levels'][i] +
                                         profile['price_levels'][i + 1]) / 2
                            price_vol_pairs.append(
                                (mid_price, profile['relative_volumes'][i]))

                        # Sort by volume percentage descending
                        sorted_pairs = sorted(price_vol_pairs,
                                              key=lambda x: x[1],
                                              reverse=True)

                        # Output top 5
                        for idx, (price,
                                  vol_pct) in enumerate(sorted_pairs[:5]):
                            is_dominant = "YES" if price in dominant_prices else "No"
                            f.write(
                                f"{tf} | ${price:.2f} | {vol_pct:.1f}% | {is_dominant}\n"
                            )

        f.write("\n=== End of Summary ===\n")
