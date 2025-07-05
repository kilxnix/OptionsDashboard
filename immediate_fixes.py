"""
Immediate fixes to apply to your current implementation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def fix_options_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Fix data types in options DataFrame before filtering"""
    if df.empty:
        return df

    # Define numeric columns
    numeric_columns = {
        'strike': float,
        'mark': float,
        'lastPrice': float,
        'bid': float,
        'ask': float,
        'volume': int,
        'openInterest': int,
        'open_interest': int,
        'delta': float,
        'gamma': float,
        'theta': float,
        'vega': float,
        'rho': float,
        'implied_volatility': float,
        'impliedVolatility': float,
    }

    for col, dtype in numeric_columns.items():
        if col in df.columns:
            # Handle dict values first
            def extract_numeric_value(val):
                if isinstance(val, dict):
                    # Try to extract numeric value from dict
                    if 'raw' in val:
                        return val['raw']
                    elif 'fmt' in val:
                        try:
                            return float(val['fmt'].replace(',', '').replace('$', '').replace('%', ''))
                        except:
                            return 0.0
                    else:
                        return 0.0
                elif pd.isna(val) or val == '' or val is None:
                    return 0.0
                else:
                    return val
            
            # Apply extraction first
            df[col] = df[col].apply(extract_numeric_value)
            
            # Convert to numeric, replacing errors with NaN
            if dtype == float:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0.0)
            elif dtype == int:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Ensure mark price exists (use lastPrice as fallback)
    if 'mark' not in df.columns and 'lastPrice' in df.columns:
        df['mark'] = df['lastPrice']
    elif 'mark' in df.columns and 'lastPrice' in df.columns:
        # Use lastPrice where mark is 0
        df.loc[df['mark'] == 0, 'mark'] = df.loc[df['mark'] == 0, 'lastPrice']
    
    return df

    # Standardize column names
    column_mapping = {
        'openInterest': 'open_interest',
        'impliedVolatility': 'implied_volatility',
        'lastPrice': 'mark',  # Use as backup for mark
    }

    for old_name, new_name in column_mapping.items():
        if old_name in df.columns and new_name not in df.columns:
            df[new_name] = df[old_name]

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
    """Safely apply filters with type checking"""
    # Fix data types first
    df = fix_options_dataframe(options_df.copy())

    if df.empty:
        return df

    # Apply filters with explicit type conversion
    try:
        # Price filter
        if 'mark' in df.columns:
            df = df[(df['mark'] >= float(min_price)) & (df['mark'] <= float(max_price))]

        # Volume filter
        if 'volume' in df.columns:
            df = df[df['volume'] >= int(min_volume)]

        # Delta filter (use absolute value)
        if 'delta' in df.columns:
            df = df[(df['delta'].abs() >= float(min_delta)) & (df['delta'].abs() <= float(max_delta))]

        # Days to expiry filter
        if 'days_to_expiry' in df.columns:
            df = df[(df['days_to_expiry'] >= int(min_days)) & (df['days_to_expiry'] <= int(max_days))]

        # Remove options with 0 open interest
        if 'open_interest' in df.columns:
            df = df[df['open_interest'] > 0]

        # Remove options with invalid prices
        if 'mark' in df.columns:
            df = df[df['mark'] > 0]

    except Exception as e:
        print(f"Error in filtering: {e}")
        # Return original if filtering fails
        return options_df

    return df


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