# In file: quantitative_analyzer.py

import pandas as pd
import numpy as np
import requests
from datetime import datetime, time
import pytz

def is_in_bollinger_squeeze(symbol: str, api_key: str, lookback: int = 20, squeeze_factor: float = 1.5) -> bool:
    """
    Checks if a stock is in a Bollinger Band Squeeze using the Alpha Vantage API.
    """
    try:
        # URL for the Alpha Vantage BBANDS technical indicator
        url = (f'https://www.alphavantage.co/query?function=BBANDS&symbol={symbol}'
               f'&interval=daily&time_period={lookback}&series_type=close&nbdevup=2&nbdevdn=2&apikey={api_key}')

        response = requests.get(url)
        data = response.json()

        if 'Technical Analysis: BBANDS' not in data:
            print(f"Could not retrieve BBANDS for {symbol} from Alpha Vantage.")
            return False

        # Convert the API response to a pandas DataFrame
        df = pd.DataFrame.from_dict(data['Technical Analysis: BBANDS'], orient='index')
        df = df.apply(pd.to_numeric, errors='coerce')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=True)

        if len(df) < 120: # Need ~6 months of data for a reliable average
            return False

        # Calculate Band Width as a percentage of the middle band (the SMA)
        df['band_width'] = (df['Real Upper Band'] - df['Real Lower Band']) / df['Real Middle Band']

        # Average band width over the last 6 months (approx 120 days)
        average_width = df['band_width'].rolling(window=120).mean().iloc[-1]
        current_width = df['band_width'].iloc[-1]

        if pd.isna(current_width) or pd.isna(average_width) or average_width == 0:
            return False

        if current_width < (average_width / squeeze_factor):
            print(f"✅ SQUEEZE DETECTED: {symbol} band width ({current_width:.2%}) is tighter than threshold ({average_width/squeeze_factor:.2%}).")
            return True

    except Exception as e:
        print(f"Error in is_in_bollinger_squeeze for {symbol}: {e}")
        return False

    return False

def calculate_relative_volume(symbol: str, api_key: str, lookback: int = 20) -> float:
    """
    Calculates RVOL by comparing today's cumulative intraday volume to the historical
    average daily volume, adjusted for the time of day. Uses Alpha Vantage API.
    """
    try:
        # --- Get historical average daily volume ---
        url_daily = (f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED'
                     f'&symbol={symbol}&outputsize=compact&apikey={api_key}')
        response_daily = requests.get(url_daily)
        data_daily = response_daily.json()

        if 'Time Series (Daily)' not in data_daily:
            print(f"Could not retrieve daily volume for {symbol}.")
            return 0.0

        df_daily = pd.DataFrame.from_dict(data_daily['Time Series (Daily)'], orient='index')
        df_daily['6. volume'] = pd.to_numeric(df_daily['6. volume'], errors='coerce')
        # Calculate the average volume over the lookback period (excluding today)
        avg_daily_volume = df_daily['6. volume'].head(lookback).mean()

        # --- Get today's cumulative intraday volume ---
        url_intraday = (f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY'
                        f'&symbol={symbol}&interval=5min&outputsize=full&apikey={api_key}')
        response_intraday = requests.get(url_intraday)
        data_intraday = response_intraday.json()

        if 'Time Series (5min)' not in data_intraday:
            print(f"Could not retrieve intraday volume for {symbol}.")
            return 0.0

        df_intraday = pd.DataFrame.from_dict(data_intraday['Time Series (5min)'], orient='index')
        df_intraday['5. volume'] = pd.to_numeric(df_intraday['5. volume'], errors='coerce')
        df_intraday.index = pd.to_datetime(df_intraday.index)

        # Filter for today's data
        today_date = datetime.now(pytz.timezone('America/New_York')).date()
        today_data = df_intraday[df_intraday.index.date == today_date]

        if today_data.empty:
            return 0.0

        today_cumulative_volume = today_data['5. volume'].sum()

        # --- Calculate RVOL adjusted for time of day ---
        # 6.5 trading hours in a day (390 minutes)
        market_open = time(9, 30)
        now_time = datetime.now(pytz.timezone('America/New_York')).time()

        if now_time < market_open:
            return 0.0 # Pre-market

        minutes_since_open = (now_time.hour - market_open.hour) * 60 + (now_time.minute - market_open.minute)
        fraction_of_day_passed = min(minutes_since_open / 390.0, 1.0) # Cap at 1.0 for end of day

        if fraction_of_day_passed == 0:
            return 0.0

        # Expected volume so far = average daily volume * fraction of day passed
        expected_volume = avg_daily_volume * fraction_of_day_passed

        if expected_volume == 0:
            return 1.0

        rvol = today_cumulative_volume / expected_volume
        print(f"📈 RVOL for {symbol}: {rvol:.2f} (Current: {today_cumulative_volume:,}, Expected: {int(expected_volume):,})")
        return rvol

    except Exception as e:
        print(f"Could not calculate RVOL for {symbol}: {e}")
        return 0.0