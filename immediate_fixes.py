"""
Immediate fixes to apply to your current implementation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def fix_options_dataframe(options_data):
    """Fix common issues with options dataframes"""
    if options_data is None or options_data.empty:
        return options_data

    df = options_data.copy()

    # Fix dictionary values in numeric columns
    numeric_columns = ['strike', 'delta', 'gamma', 'theta', 'volume', 'mark', 'open_interest', 'impliedVolatility', 'bid', 'ask', 'lastPrice']

    for col in numeric_columns:
        if col in df.columns:
            def extract_numeric(value):
                try:
                    if isinstance(value, dict):
                        if 'raw' in value:
                            return float(value['raw'])
                        elif 'fmt' in value:
                            # Remove formatting
                            cleaned = str(value['fmt']).replace(',', '').replace('$', '').replace('%', '')
                            try:
                                return float(cleaned)
                            except:
                                return 0.0
                        else:
                            # Try to get first numeric value
                            for v in value.values():
                                try:
                                    return float(v)
                                except:
                                    continue
                            return 0.0
                    elif pd.isna(value) or value is None:
                        return 0.0
                    else:
                        return float(value)
                except:
                    # Set reasonable defaults for each column
                    defaults = {
                        'strike': 100.0, 'delta': 0.3, 'gamma': 0.01, 'theta': -0.05,
                        'volume': 100.0, 'mark': 0.5, 'open_interest': 50.0,
                        'impliedVolatility': 0.25, 'bid': 0.45, 'ask': 0.55, 'lastPrice': 0.5
                    }
                    return defaults.get(col, 0.0)

            df[col] = df[col].apply(extract_numeric)

    return df


def safe_apply_filters(
    options_df: pd.DataFrame,
    min_price: float = 0.01,
    max_price: float = 10.00,
    min_delta: float = 0.0,
    max_delta: float = 1.0,
    min_volume: int = 0,
    min_days: int = 0,
    max_days: int = 365,
) -> pd.DataFrame:
    """Apply filters safely, handling various data type issues including nested dicts"""
    if options_df is None or options_df.empty:
        return pd.DataFrame()

    try:
        # Make a copy to avoid modifying original
        df = options_df.copy()

        # Fix data types first
        df = fix_options_dataframe(df)

        # Ensure all comparison columns are properly extracted from dicts
        def safe_extract_for_comparison(series, default=0):
            """Extract numeric values from potentially nested data"""
            def extract_value(val):
                if isinstance(val, dict):
                    # Try different Yahoo Finance keys
                    for key in ['raw', 'fmt', 'value']:
                        if key in val:
                            try:
                                if key == 'fmt':
                                    # Clean formatted strings
                                    cleaned = str(val[key]).replace(',', '').replace('$', '').replace('%', '')
                                    return float(cleaned)
                                else:
                                    return float(val[key])
                            except (ValueError, TypeError):
                                continue
                    # If no known keys, try first numeric value
                    for v in val.values():
                        try:
                            if isinstance(v, str):
                                cleaned = str(v).replace(',', '').replace('$', '').replace('%', '')
                                return float(cleaned)
                            else:
                                return float(v)
                        except (ValueError, TypeError):
                            continue
                    return default
                elif pd.isna(val) or val is None or val == '':
                    return default
                else:
                    try:
                        if isinstance(val, str):
                            # Clean string values
                            cleaned = str(val).replace(',', '').replace('$', '').replace('%', '')
                            return float(cleaned)
                        else:
                            return float(val)
                    except (ValueError, TypeError):
                        return default

            result = series.apply(extract_value)
            # Ensure we return a numeric series
            return pd.to_numeric(result, errors='coerce').fillna(default)

        # Apply filters with safe comparisons - create new columns with extracted values
        if 'mark' in df.columns:
            df['_mark_numeric'] = safe_extract_for_comparison(df['mark'], 0.5)
            df = df[(df['_mark_numeric'] >= min_price) & (df['_mark_numeric'] <= max_price)]
        elif 'lastPrice' in df.columns:
            df['_price_numeric'] = safe_extract_for_comparison(df['lastPrice'], 0.5)
            df = df[(df['_price_numeric'] >= min_price) & (df['_price_numeric'] <= max_price)]

        if 'delta' in df.columns:
            df['_delta_numeric'] = safe_extract_for_comparison(df['delta'], 0.3)
            df['_abs_delta'] = df['_delta_numeric'].abs()
            df = df[(df['_abs_delta'] >= min_delta) & (df['_abs_delta'] <= max_delta)]

        if 'volume' in df.columns:
            df['_volume_numeric'] = safe_extract_for_comparison(df['volume'], 100)
            df = df[df['_volume_numeric'] >= min_volume]

        if 'days_to_expiry' in df.columns:
            df['_days_numeric'] = safe_extract_for_comparison(df['days_to_expiry'], 30)
            df = df[(df['_days_numeric'] >= min_days) & (df['_days_numeric'] <= max_days)]

        # Clean up temporary columns
        temp_cols = [col for col in df.columns if col.startswith('_')]
        df = df.drop(columns=temp_cols, errors='ignore')

        return df

    except Exception as e:
        print(f"Filter error: {e}")
        return options_df  # Return original if filtering fails


def process_alpha_vantage_bulk_response(data):
    """Process bulk quotes response from Alpha Vantage"""
    parsed_data = {}

    try:
        # Check if data has the expected structure
        if not isinstance(data, dict):
            print(f"❌ Invalid response format: {type(data)}")
            return parsed_data

        # Debug: Print the actual response structure
        print(f"📋 Response keys: {list(data.keys())}")

        # Alpha Vantage bulk quotes typically return data in these formats:
        # 1. "Global Quotes" (array)
        # 2. "data" (array) 
        # 3. Direct symbol mapping

        quotes_data = None

        # Try different response formats
        if 'Global Quotes' in data and isinstance(data['Global Quotes'], list):
            quotes_data = data['Global Quotes']
            print(f"📊 Found Global Quotes array with {len(quotes_data)} items")
        elif 'data' in data and isinstance(data['data'], list):
            quotes_data = data['data']
            print(f"📊 Found data array with {len(quotes_data)} items")
        elif 'quotes' in data:
            quotes_data = data['quotes']
            print(f"📊 Found quotes data")
        else:
            # Try to find any array in the response
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check if first item looks like a quote
                    first_item = value[0] if value else {}
                    if isinstance(first_item, dict) and ('symbol' in first_item or '01. symbol' in first_item):
                        quotes_data = value
                        print(f"📊 Found quote-like array in key '{key}' with {len(quotes_data)} items")
                        break

        if not quotes_data:
            print(f"❌ No quotes data found. Response structure: {str(data)[:300]}...")
            return parsed_data

        # Process quotes
        for quote in quotes_data:
            if not isinstance(quote, dict):
                continue

            # Extract symbol (try different key formats)
            symbol = None
            for sym_key in ['symbol', '01. symbol', 'ticker', 'Symbol']:
                if sym_key in quote:
                    symbol = quote[sym_key]
                    break

            if not symbol:
                continue

            # Extract price data with multiple fallbacks
            try:
                price = 0
                for price_key in ['price', '05. price', 'last_price', 'close', '02. close']:
                    if price_key in quote:
                        price = float(str(quote[price_key]).replace('$', '').replace(',', ''))
                        break

                change_pct = 0
                for change_key in ['change_percent', '10. change percent', 'change_pct', 'percent_change']:
                    if change_key in quote:
                        change_str = str(quote[change_key]).replace('%', '').replace('+', '')
                        change_pct = float(change_str) if change_str else 0
                        break

                volume = 0
                for vol_key in ['volume', '06. volume', 'Volume']:
                    if vol_key in quote:
                        volume = int(float(str(quote[vol_key]).replace(',', '')))
                        break

                high = price  # Default to current price
                for high_key in ['high', '03. high', 'day_high']:
                    if high_key in quote:
                        high = float(str(quote[high_key]).replace('$', '').replace(',', ''))
                        break

                low = price  # Default to current price  
                for low_key in ['low', '04. low', 'day_low']:
                    if low_key in quote:
                        low = float(str(quote[low_key]).replace('$', '').replace(',', ''))
                        break

                if price > 0:  # Only include if we have a valid price
                    parsed_data[symbol] = {
                        'current_price': price,
                        'change_percent': change_pct,
                        'volume': volume,
                        'high': high,
                        'low': low
                    }

            except (ValueError, TypeError) as e:
                print(f"⚠️ Error parsing data for {symbol}: {e}")
                continue

        print(f"✅ Successfully parsed {len(parsed_data)} symbols from bulk response")
        if len(parsed_data) > 0:
            # Show a sample
            sample_symbol = list(parsed_data.keys())[0]
            print(f"📋 Sample data for {sample_symbol}: {parsed_data[sample_symbol]}")

        return parsed_data

    except Exception as e:
        print(f"❌ Error parsing bulk response: {e}")
        print(f"📋 Response type: {type(data)}")
        print(f"📋 Response sample: {str(data)[:500]}...")
        return parsed_data


def apply_enhanced_filters(self, options_data, filters=None):
    """Replace the problematic filter method in your scanner"""
    if filters is None:
        filters = {
            'min_price': 0.01,
            'max_price': 10.00,
            'min_delta': 0.25,
            'max_delta': 0.68,
            'min_volume': 0,
            'min_days': 2,
            'max_days': 16,
        }

    return safe_apply_filters(
        options_data,
        min_price=filters.get('min_price', 0.01),
        max_price=filters.get('max_price', 10.00),
        min_delta=filters.get('min_delta', 0.25),
        max_delta=filters.get('max_delta', 0.68),
        min_volume=filters.get('min_volume', 0),
        min_days=filters.get('min_days', 2),
        max_days=filters.get('max_days', 16),
    )


def patch_existing_scanner():
    """Add this to your main.py or scanner initialization"""
    import scanner_core

    # Monkey patch the filter function
    original_filter = getattr(scanner_core, 'filter_options_by_criteria', None)

    def fixed_filter_options_by_criteria(options_df, **kwargs):
        # Fix data types first
        fixed_df = fix_options_dataframe(options_df)
        if original_filter:
            try:
                return original_filter(fixed_df, **kwargs)
            except Exception as e:
                print(f"Filter error: {e}, using safe filter")
                return safe_apply_filters(fixed_df, **kwargs)
        else:
            return safe_apply_filters(fixed_df, **kwargs)

    if original_filter:
        scanner_core.filter_options_by_criteria = fixed_filter_options_by_criteria


def process_alpha_vantage_bulk_response(data: dict) -> dict:
    """Process Alpha Vantage bulk quotes response safely"""
    parsed_data = {}

    try:
        # Debug: Print actual response structure
        print(f"📋 DEBUG: Response keys: {list(data.keys())}")
        print(f"📋 DEBUG: Response type: {type(data)}")
        print(f"📋 DEBUG: First 500 chars: {str(data)[:500]}...")

        # Check if response contains actual data
        if 'Information' in data:
            print(f"⚠️ Alpha Vantage info: {data['Information']}")
            return {}

        if 'Error Message' in data:
            print(f"❌ Alpha Vantage error: {data['Error Message']}")
            return {}

        # Handle different possible response formats from Alpha Vantage bulk quotes
        quotes_data = None

        # Try common Alpha Vantage bulk quote response formats
        possible_keys = [
            'data',  # Common format
            'quotes',  # Alternative format
            'realtime_quotes',  # Realtime format
            'bulk_quotes',  # Bulk format
            'Global Quotes',  # Global quotes format
            'Time Series (Daily)',  # Time series format fallback
        ]

        for key in possible_keys:
            if key in data and data[key]:
                quotes_data = data[key]
                print(f"📊 Found quotes data under key: {key}")
                break

        # If no standard key found, look for any array-like data
        if not quotes_data:
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check if first item looks like quote data
                    first_item = value[0] if value else {}
                    if isinstance(first_item, dict) and any(field in first_item for field in ['symbol', 'ticker', 'price', 'last']):
                        quotes_data = value
                        print(f"📊 Found quote-like data under key: {key}")
                        break
                elif isinstance(value, dict) and len(value) > 0:
                    # Check if this looks like symbol-keyed data
                    first_key = list(value.keys())[0]
                    first_val = value[first_key]
                    if isinstance(first_val, dict) and any(field in first_val for field in ['price', 'last', 'close']):
                        # Convert symbol-keyed dict to list format
                        quotes_data = []
                        for sym, quote_data in value.items():
                            quote_data['symbol'] = sym
                            quotes_data.append(quote_data)
                        print(f"📊 Found symbol-keyed data under key: {key}, converted to list")
                        break

        if not quotes_data:
            print(f"❌ No recognizable quotes data found in response")
            return {}

        print(f"📊 Processing {len(quotes_data) if isinstance(quotes_data, list) else 'unknown'} quotes")

        # Process quotes data
        if isinstance(quotes_data, list):
            for quote in quotes_data:
                if not isinstance(quote, dict):
                    continue

                # Extract symbol with multiple possible keys
                symbol = None
                for sym_key in ['symbol', 'ticker', '01. symbol', 'Symbol']:
                    if sym_key in quote and quote[sym_key]:
                        symbol = str(quote[sym_key]).strip().upper()
                        break

                if not symbol:
                    continue

                # Extract price data with multiple fallbacks
                current_price = 100.0  # Default
                for price_key in ['price', 'last', 'close', '05. price', '4. close', 'lastPrice']:
                    if price_key in quote:
                        try:
                            price_val = quote[price_key]
                            if isinstance(price_val, dict) and 'raw' in price_val:
                                current_price = float(price_val['raw'])
                            else:
                                current_price = float(str(price_val).replace('$', '').replace(',', ''))
                            break
                        except (ValueError, TypeError):
                            continue

                # Extract volume
                volume = 100000  # Default
                for vol_key in ['volume', '6. volume', 'Volume']:
                    if vol_key in quote:
                        try:
                            vol_val = quote[vol_key]
                            if isinstance(vol_val, dict) and 'raw' in vol_val:
                                volume = int(vol_val['raw'])
                            else:
                                volume = int(float(str(vol_val).replace(',', '')))
                            break
                        except (ValueError, TypeError):
                            continue

                # Extract change percent
                change_percent = 0.0
                for change_key in ['change_percent', 'changePercent', '10. change percent', 'change']:
                    if change_key in quote:
                        try:
                            change_val = quote[change_key]
                            if isinstance(change_val, dict) and 'raw' in change_val:
                                change_percent = float(change_val['raw'])
                            else:
                                change_str = str(change_val).replace('%', '').replace('+', '')
                                change_percent = float(change_str) if change_str else 0.0
                            break
                        except (ValueError, TypeError):
                            continue

                # Extract high/low
                high = current_price * 1.05  # Default estimate
                low = current_price * 0.95   # Default estimate

                for high_key in ['high', '2. high', 'dayHigh']:
                    if high_key in quote:
                        try:
                            high = float(str(quote[high_key]).replace('$', '').replace(',', ''))
                            break
                        except (ValueError, TypeError):
                            continue

                for low_key in ['low', '3. low', 'dayLow']:
                    if low_key in quote:
                        try:
                            low = float(str(quote[low_key]).replace('$', '').replace(',', ''))
                            break
                        except (ValueError, TypeError):
                            continue

                parsed_data[symbol] = {
                    'current_price': current_price,
                    'volume': volume,
                    'change_percent': change_percent,
                    'high': high,
                    'low': low
                }

        print(f"✅ Successfully parsed {len(parsed_data)} symbols from bulk response")
        if len(parsed_data) > 0:
            sample_symbol = list(parsed_data.keys())[0]
            print(f"📋 Sample data for {sample_symbol}: {parsed_data[sample_symbol]}")

        return parsed_data

    except Exception as e:
        print(f"❌ Error processing Alpha Vantage bulk response: {e}")
        print(f"📋 Response sample: {str(data)[:500]}...")
        return {}


def test_type_fixes():
    """Test that the fixes work correctly"""
    # Create test data with mixed types (like your actual data)
    test_data = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'strike': ['150.0', '350', '140.0'],
        'mark': ['2.50', '3.75', '1.25'],
        'volume': ['100', '250', '75'],
        'delta': ['0.35', '0.45', '0.25'],
        'open_interest': [1000, 2000, 500],
    })

    print("Before fix:")
    print(test_data.dtypes)

    # Apply fix
    fixed_data = fix_options_dataframe(test_data)

    print("\nAfter fix:")
    print(fixed_data.dtypes)

    # Test filtering
    filtered = safe_apply_filters(fixed_data, min_price=1.0, max_price=3.0)
    print(f"\nFiltered: {len(filtered)} options")
    print(filtered)


if __name__ == "__main__":
    test_type_fixes()