
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from scanner_core import CompleteOptionsScanner, is_likely_optionable
from performance_tracker import PerformanceTracker

class EnhancedOptionsScanner(CompleteOptionsScanner):
    """Enhanced scanner with better data validation and additional metrics"""
    
    def __init__(self, api_key, min_delta=0.2, max_delta=0.7):
        super().__init__(api_key, min_delta, max_delta)
        self.performance_tracker = PerformanceTracker()
        
    def enhanced_fetch_options_data(self, symbol):
        """
        Enhanced options data fetching with multiple sources and validation
        """
        print(f"🔍 Fetching enhanced options data for {symbol}...")
        
        # Try Alpha Vantage first
        av_options = self.fetch_options_data(symbol)
        
        # Try yfinance as backup/supplement
        yf_options = self.fetch_yfinance_options(symbol)
        
        # Combine and validate data
        if av_options is not None and not av_options.empty:
            if yf_options is not None and not yf_options.empty:
                # Cross-validate pricing data
                validated_options = self.cross_validate_options(av_options, yf_options, symbol)
                return validated_options
            return av_options
        elif yf_options is not None and not yf_options.empty:
            return yf_options
        
        return None
    
    def fetch_yfinance_options(self, symbol):
        """
        Fetch options data using yfinance for cross-validation
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get all expiration dates
            expirations = ticker.options
            if not expirations:
                return None
            
            all_options = []
            
            # Process first 3 expirations to avoid overloading
            for exp_date in expirations[:3]:
                try:
                    option_chain = ticker.option_chain(exp_date)
                    
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
                    
                    time.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error fetching {exp_date} for {symbol}: {e}")
                    continue
            
            if all_options:
                combined_df = pd.concat(all_options, ignore_index=True)
                
                # Standardize column names
                column_mapping = {
                    'contractSymbol': 'contractID',
                    'lastPrice': 'mark',
                    'impliedVolatility': 'implied_volatility',
                    'openInterest': 'open_interest',
                    'contractSize': 'multiplier'
                }
                
                for old_name, new_name in column_mapping.items():
                    if old_name in combined_df.columns:
                        combined_df[new_name] = combined_df[old_name]
                
                # Add missing columns with defaults
                required_columns = ['delta', 'gamma', 'theta', 'vega', 'rho']
                for col in required_columns:
                    if col not in combined_df.columns:
                        combined_df[col] = np.nan
                
                print(f"✅ YFinance: {len(combined_df)} options for {symbol}")
                return combined_df
            
            return None
            
        except Exception as e:
            print(f"YFinance options fetch failed for {symbol}: {e}")
            return None
    
    def cross_validate_options(self, av_data, yf_data, symbol):
        """
        Cross-validate options data between sources
        """
        if av_data is None or yf_data is None:
            return av_data if av_data is not None else yf_data
        
        print(f"🔍 Cross-validating options data for {symbol}...")
        
        # Use Alpha Vantage as primary (has better Greeks)
        # Use yfinance for price validation
        validated_data = av_data.copy()
        
        # Add validation flags
        validated_data['price_validated'] = False
        validated_data['yf_last_price'] = np.nan
        validated_data['price_difference'] = np.nan
        
        try:
            for idx, row in validated_data.iterrows():
                # Find matching option in yfinance data
                matching_yf = yf_data[
                    (yf_data['strike'] == row['strike']) &
                    (yf_data['type'] == row['type']) &
                    (pd.to_datetime(yf_data['expiration']).dt.date == 
                     pd.to_datetime(row['expiration']).date())
                ]
                
                if not matching_yf.empty:
                    yf_price = matching_yf.iloc[0].get('lastPrice', np.nan)
                    av_price = row.get('mark', row.get('lastPrice', np.nan))
                    
                    if not pd.isna(yf_price) and not pd.isna(av_price):
                        price_diff = abs(yf_price - av_price) / max(yf_price, av_price) * 100
                        
                        validated_data.at[idx, 'yf_last_price'] = yf_price
                        validated_data.at[idx, 'price_difference'] = price_diff
                        
                        # Mark as validated if prices are within 20%
                        if price_diff <= 20:
                            validated_data.at[idx, 'price_validated'] = True
        
        except Exception as e:
            print(f"Cross-validation error for {symbol}: {e}")
        
        return validated_data
    
    def get_comprehensive_market_data(self, symbol):
        """
        Get comprehensive market data including fundamentals
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get basic info
            info = ticker.info
            
            # Get recent price action
            hist = ticker.history(period="1mo", interval="1d")
            
            if hist.empty:
                return None
            
            # Calculate additional metrics
            recent_price = hist['Close'].iloc[-1]
            volume_avg = hist['Volume'].mean()
            price_change_30d = ((recent_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            
            # Volatility metrics
            returns = hist['Close'].pct_change().dropna()
            volatility_30d = returns.std() * np.sqrt(252) * 100  # Annualized
            
            market_data = {
                'symbol': symbol,
                'current_price': recent_price,
                'market_cap': info.get('marketCap', 0),
                'volume_avg_30d': volume_avg,
                'price_change_30d': price_change_30d,
                'volatility_30d': volatility_30d,
                'beta': info.get('beta', 1.0),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'earnings_date': info.get('earningsDate', None),
                'analyst_targets': {
                    'mean': info.get('targetMeanPrice', 0),
                    'high': info.get('targetHighPrice', 0),
                    'low': info.get('targetLowPrice', 0)
                }
            }
            
            return market_data
            
        except Exception as e:
            print(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def enhanced_option_scoring(self, option_data, market_data, analysis_results):
        """
        Enhanced option scoring with additional market factors
        """
        try:
            base_score = self._score_option(option_data, analysis_results)
            
            if market_data is None:
                return base_score
            
            # Volume factor
            volume_factor = 1.0
            if float(option_data.get('volume', 0)) > 100:
                volume_factor = 1.2
            elif float(option_data.get('volume', 0)) > 50:
                volume_factor = 1.1
            
            # Volatility factor
            vol_factor = 1.0
            market_vol = market_data.get('volatility_30d', 50)
            option_iv = float(option_data.get('implied_volatility', 0.5)) * 100
            
            if option_iv > market_vol * 1.5:  # High IV
                vol_factor = 1.15
            elif option_iv < market_vol * 0.8:  # Low IV
                vol_factor = 0.9
            
            # Earnings proximity factor
            earnings_factor = 1.0
            if market_data.get('earnings_date'):
                try:
                    earnings_date = pd.to_datetime(market_data['earnings_date'])
                    option_exp = pd.to_datetime(option_data.get('expiration'))
                    days_to_earnings = (earnings_date - datetime.now()).days
                    days_to_exp = (option_exp - datetime.now()).days
                    
                    # Boost if option expires after earnings
                    if 0 <= days_to_earnings <= days_to_exp <= 30:
                        earnings_factor = 1.3
                except:
                    pass
            
            # Market cap factor (favor liquid stocks)
            market_cap = market_data.get('market_cap', 0)
            cap_factor = 1.0
            if market_cap > 10e9:  # > $10B
                cap_factor = 1.1
            elif market_cap > 1e9:  # > $1B
                cap_factor = 1.05
            
            enhanced_score = base_score * volume_factor * vol_factor * earnings_factor * cap_factor
            
            return min(enhanced_score, 10.0)  # Cap at 10
            
        except Exception as e:
            print(f"Error in enhanced scoring: {e}")
            return base_score
    
    def validate_trade_plan(self, trade_plan, market_data, option_data):
        """
        Validate and improve trade plan based on market conditions
        """
        if not trade_plan or not market_data:
            return trade_plan
        
        validated_plan = trade_plan.copy()
        
        try:
            # Adjust position sizing based on market cap
            market_cap = market_data.get('market_cap', 0)
            if market_cap < 1e9:  # Small cap - reduce position
                validated_plan['position_size'] = max(1, validated_plan['position_size'] // 2)
                validated_plan['risk_level'] = 'HIGH'
            elif market_cap > 100e9:  # Mega cap - can increase slightly
                validated_plan['position_size'] = min(20, int(validated_plan['position_size'] * 1.2))
                validated_plan['risk_level'] = 'LOW'
            else:
                validated_plan['risk_level'] = 'MEDIUM'
            
            # Adjust targets based on volatility
            market_vol = market_data.get('volatility_30d', 50)
            if market_vol > 80:  # High volatility
                # Tighter stops, wider targets
                validated_plan['stop_loss'] = validated_plan['entry_price'] * 0.8
                validated_plan['final_target'] = validated_plan['entry_price'] * 4.0
            elif market_vol < 30:  # Low volatility
                # Normal stops, conservative targets
                validated_plan['final_target'] = validated_plan['entry_price'] * 2.5
            
            # Add market context
            validated_plan['market_context'] = {
                'sector': market_data.get('sector'),
                'volatility_regime': 'HIGH' if market_vol > 60 else 'MEDIUM' if market_vol > 30 else 'LOW',
                'analyst_target': market_data.get('analyst_targets', {}).get('mean', 0),
                'beta': market_data.get('beta', 1.0)
            }
            
            # Add validation timestamp
            validated_plan['validation_timestamp'] = datetime.now().isoformat()
            validated_plan['validation_score'] = self.calculate_plan_confidence(validated_plan, market_data)
            
        except Exception as e:
            print(f"Error validating trade plan: {e}")
        
        return validated_plan
    
    def calculate_plan_confidence(self, trade_plan, market_data):
        """
        Calculate confidence score for the trade plan
        """
        confidence = 50  # Base confidence
        
        try:
            # Market cap confidence
            market_cap = market_data.get('market_cap', 0)
            if market_cap > 10e9:
                confidence += 15
            elif market_cap > 1e9:
                confidence += 10
            
            # Volume confidence
            if trade_plan.get('risk_level') == 'LOW':
                confidence += 10
            elif trade_plan.get('risk_level') == 'HIGH':
                confidence -= 10
            
            # Volatility alignment
            market_vol = market_data.get('volatility_30d', 50)
            option_iv = trade_plan.get('risk_metrics', {}).get('implied_vol', 50)
            
            if abs(option_iv - market_vol) < 20:  # IV aligned with historical vol
                confidence += 10
            
            # Beta factor
            beta = market_data.get('beta', 1.0)
            if 0.8 <= beta <= 1.2:  # Moderate beta
                confidence += 5
            
        except Exception:
            pass
        
        return min(max(confidence, 0), 100)  # Clamp between 0-100

def run_enhanced_scanner(symbols=None, **kwargs):
    """
    Run the enhanced scanner with improved data collection
    """
    from scanner_core import ALPHA_VANTAGE_API_KEY
    
    enhanced_scanner = EnhancedOptionsScanner(
        ALPHA_VANTAGE_API_KEY,
        min_delta=kwargs.get('min_delta', 0.25),
        max_delta=kwargs.get('max_delta', 0.68)
    )
    
    if symbols is None:
        from scanner_core import get_optionable_stocks_with_volume
        symbols = get_optionable_stocks_with_volume()
    
    print(f"🚀 Running enhanced scanner on {len(symbols)} symbols...")
    
    enhanced_results = {}
    
    for symbol in symbols[:20]:  # Limit for testing
        try:
            print(f"\n🔍 Enhanced analysis for {symbol}...")
            
            # Get comprehensive market data
            market_data = enhanced_scanner.get_comprehensive_market_data(symbol)
            
            # Get multi-timeframe price analysis
            multi_tf_data = enhanced_scanner.fetch_multi_timeframe_data(symbol)
            if not multi_tf_data:
                continue
            
            analysis_results = enhanced_scanner.analyze_timeframes(symbol, multi_tf_data)
            confluence = enhanced_scanner.calculate_pattern_confluence(analysis_results)
            
            if confluence['score'] >= 6.0:
                # Enhanced options data
                options_data = enhanced_scanner.enhanced_fetch_options_data(symbol)
                
                if options_data is not None and not options_data.empty:
                    # Enhanced scoring
                    for idx, option in options_data.iterrows():
                        enhanced_score = enhanced_scanner.enhanced_option_scoring(
                            option, market_data, analysis_results
                        )
                        options_data.at[idx, 'enhanced_score'] = enhanced_score
                    
                    # Re-sort by enhanced score
                    options_data = options_data.sort_values('enhanced_score', ascending=False)
                    
                    # Generate and validate trade plan
                    top_option = options_data.iloc[0]
                    symbol_context = {
                        "support": None,
                        "resistance": None,
                        "skew": "Neutral",
                        "bias": confluence["bias"]
                    }
                    
                    from scanner_core import generate_trade_plan
                    trade_plan = generate_trade_plan(top_option, symbol_context)
                    
                    if trade_plan:
                        validated_plan = enhanced_scanner.validate_trade_plan(
                            trade_plan, market_data, top_option
                        )
                        
                        enhanced_results[symbol] = {
                            'market_data': market_data,
                            'timeframe_analysis': analysis_results,
                            'confluence': confluence,
                            'options': options_data.head(5),  # Top 5 options
                            'trade_plan': validated_plan,
                            'enhancement_timestamp': datetime.now().isoformat()
                        }
                        
                        print(f"✅ {symbol}: Enhanced score {confluence['score']:.1f}/10, Plan confidence: {validated_plan.get('validation_score', 'N/A')}%")
        
        except Exception as e:
            print(f"❌ Enhanced analysis failed for {symbol}: {e}")
            continue
    
    return enhanced_results

if __name__ == "__main__":
    results = run_enhanced_scanner()
    print(f"\n✅ Enhanced scan complete: {len(results)} high-quality opportunities found")
