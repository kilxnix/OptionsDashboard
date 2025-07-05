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


def process_alpha_vantage_bulk_response(response: Dict) -> Dict[str, Dict]:
    """Process Alpha Vantage REALTIME_BULK_QUOTES response correctly"""
    market_data = {}

    # Check different possible response formats
    if 'data' in response:
        data_list = response['data']
    elif 'quotes' in response:
        data_list = response['quotes']
    elif isinstance(response, list):
        data_list = response
    else:
        print(f"Unknown response format: {list(response.keys())}")
        return {}

    for item in data_list:
        try:
            symbol = item.get('symbol', item.get('01. symbol', ''))
            if not symbol:
                continue

            # Try different field names Alpha Vantage might use
            price = float(item.get('price', item.get('05. price', item.get('02. price', 0))))

            if price > 0:  # Valid price
                market_data[symbol] = {
                    'symbol': symbol,
                    'current_price': price,
                    'volume': int(item.get('volume', item.get('06. volume', 0))),
                    'timestamp': item.get('timestamp', item.get('07. latest trading day', '')),
                }
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    return market_data


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
