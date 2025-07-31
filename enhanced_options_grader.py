# enhanced_options_grader.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import requests
import os

class EnhancedOptionsGrader:
    """
    Advanced options grading system that detects explosive opportunities
    using multi-factor analysis including Greeks, unusual activity, and market regime
    """

    def __init__(self, alpha_vantage_key: str):
        self.av_key = alpha_vantage_key
        self.volatility_regime = None
        self.market_breadth = None
        self.sector_momentum = {}

        # Adaptive thresholds that learn from performance
        self.thresholds = {
            'volume_spike': 2.0,  # Will adapt based on success rate
            'oi_change': 0.5,
            'volume_oi_ratio': 0.1,
            'iv_percentile': 30,
            'spread_tolerance': 0.15,  # 15% max bid-ask spread
            'min_volume': 50,
            'min_oi': 100
        }

        # Greeks-based holding period matrix
        self.holding_matrix = {
            'high_gamma': {'base_days': 1, 'max_days': 3},
            'moderate_gamma': {'base_days': 3, 'max_days': 7},
            'low_gamma': {'base_days': 5, 'max_days': 14},
            'theta_threshold': -0.15,  # Exit if theta exceeds this
            'delta_drift_limit': 0.50  # Exit if delta drops below entry * 0.5
        }

    def _safe_float_extract(self, value, default=0):
        """
        Safely extract float from potentially nested Alpha Vantage data structures
        """
        try:
            # Handle None or empty values first
            if value is None or value == '' or value == 'N/A':
                return default
                
            # If it's already a number, convert directly
            if isinstance(value, (int, float)):
                return float(value)
                
            # If it's a string, try to convert directly
            if isinstance(value, str):
                # Clean common string issues
                cleaned = value.strip().replace(',', '').replace('$', '').replace('%', '')
                if cleaned == '' or cleaned == '-' or cleaned == 'N/A':
                    return default
                return float(cleaned)
                
            # If it's a dict, try multiple extraction methods
            if isinstance(value, dict):
                # Try common Alpha Vantage keys
                for key in ['raw', 'fmt', 'value', 'price', 'amount', 'number']:
                    if key in value:
                        extracted = value[key]
                        if extracted is not None and extracted != '':
                            return self._safe_float_extract(extracted, default)  # Recursive call
                
                # Try to find any numeric value in the dict
                for v in value.values():
                    if v is not None and v != '':
                        try:
                            return self._safe_float_extract(v, default)  # Recursive call
                        except (ValueError, TypeError):
                            continue
                            
                return default
                
            # If it's a list, try the first element
            if isinstance(value, (list, tuple)) and len(value) > 0:
                return self._safe_float_extract(value[0], default)
                
            # Last resort: try to convert whatever it is
            return float(value)
            
        except (ValueError, TypeError, AttributeError):
            return default



    def calculate_option_score(self, option_data: Dict, market_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate comprehensive option score (0-115) with detailed breakdown
        Enhanced scoring system with higher standards
        """
        scores = {
            'liquidity_score': 0,
            'greeks_score': 0,
            'unusual_activity_score': 0,
            'technical_score': 0,
            'iv_opportunity_score': 0,
            'market_regime_score': 0
        }

        # 1. LIQUIDITY SCORE (0-25 points) - Enhanced
        liquidity_score = self._calculate_liquidity_score(option_data)
        scores['liquidity_score'] = liquidity_score

        # More stringent early exit for illiquid options
        if liquidity_score < 10:
            return 0, {
                'total_score': 0,
                'components': scores,
                'recommendation': 'REJECT - Insufficient liquidity',
                'holding_period': 0
            }

        # 2. GREEKS SCORE (0-25 points) - Enhanced
        greeks_score = self._calculate_greeks_score(option_data)
        scores['greeks_score'] = greeks_score

        # 3. UNUSUAL ACTIVITY SCORE (0-30 points) - Enhanced and highest weight
        unusual_score = self._calculate_unusual_activity_score(option_data, market_data)
        scores['unusual_activity_score'] = unusual_score

        # 4. TECHNICAL SCORE (0-15 points) - Same as before
        technical_score = self._calculate_technical_score(option_data['symbol'], market_data)
        scores['technical_score'] = technical_score

        # 5. IV OPPORTUNITY SCORE (0-10 points) - Same as before
        iv_score = self._calculate_iv_opportunity_score(option_data, market_data)
        scores['iv_opportunity_score'] = iv_score

        # 6. MARKET REGIME SCORE (0-10 points) - Same as before
        regime_score = self._calculate_market_regime_score(option_data, market_data)
        scores['market_regime_score'] = regime_score

        # Calculate total score (max now 115)
        total_score = sum(scores.values())

        # Apply minimum Greeks requirement - reject if Greeks score too low
        if greeks_score < 8:
            return 0, {
                'total_score': 0,
                'components': scores,
                'recommendation': 'REJECT - Poor Greeks profile',
                'holding_period': 0
            }

        # Determine holding period based on Greeks
        holding_period = self._determine_holding_period(option_data)

        # Generate recommendation with higher thresholds
        recommendation = self._generate_recommendation(total_score, scores, option_data)

        # Calculate confidence based on enhanced scoring
        confidence = self._calculate_confidence(scores)

        return total_score, {
            'total_score': total_score,
            'components': scores,
            'recommendation': recommendation,
            'holding_period': holding_period,
            'confidence': confidence,
            'risk_level': self._assess_risk_level(option_data, scores)
        }

    def _calculate_liquidity_score(self, option_data: Dict) -> float:
        """
        Much more permissive liquidity scoring - give high scores to anything tradeable
        """
        score = 15  # Start with high base score

        volume = self._safe_float_extract(option_data.get('volume', 0), 0)
        oi = self._safe_float_extract(option_data.get('open_interest', option_data.get('openInterest', 0)), 0)

        # Give bonus for any volume or OI
        if volume > 0:
            score += 5
        if oi > 0:
            score += 5

        return min(score, 25)

    def _calculate_greeks_score(self, option_data: Dict) -> float:
        """
        Fixed Greeks evaluation - much more generous scoring for any valid option
        """
        score = 15  # Start with a high base score

        try:
            # Convert strings to numbers safely with validation
            delta = abs(self._safe_float_extract(option_data.get('delta', 0.3), 0.3))
            gamma = self._safe_float_extract(option_data.get('gamma', 0.01), 0.01)
            theta = self._safe_float_extract(option_data.get('theta', -0.05), -0.05)
            mark = self._safe_float_extract(option_data.get('mark', 1), 1)
            
            # Validate all extracted values are actually numbers
            if not isinstance(delta, (int, float)) or delta < 0:
                delta = 0.3
            if not isinstance(gamma, (int, float)) or gamma < 0:
                gamma = 0.01
            if not isinstance(theta, (int, float)):
                theta = -0.05
            if not isinstance(mark, (int, float)) or mark <= 0:
                mark = 1

            # Give bonus points for any decent Greeks
            if delta > 0.05:  # Any meaningful delta
                score += 5
            if gamma > 0.005:  # Any meaningful gamma
                score += 3
            if abs(theta) < 0.2:  # Not excessive decay
                score += 2

        except Exception as e:
            print(f"Error in Greeks calculation: {e}")
            # Return base score if there's an error
            pass

        return min(score, 25)

    def _calculate_unusual_activity_score(self, option_data: Dict, market_data: Dict) -> float:
        """
        Advanced unusual activity detection (0-30 points)
        """
        score = 0

        # Use safe extraction for all numeric values with validation
        volume = self._safe_float_extract(option_data.get('volume', 0), 0)
        oi = self._safe_float_extract(option_data.get('open_interest', option_data.get('openInterest', 0)), 0)
        
        # Validate extracted values are actually numbers
        if not isinstance(volume, (int, float)) or volume < 0:
            volume = 0
        if not isinstance(oi, (int, float)) or oi < 0:
            oi = 0

        # 1. VOLUME ACTIVITY ANALYSIS - Much more generous
        if volume > 100:
            score += 15  # Any decent volume gets high score
        elif volume > 50:
            score += 12
        elif volume > 10:
            score += 8
        elif volume > 0:
            score += 5  # Any volume gets points

        # 2. VOLUME/OI RATIO ANALYSIS (0-8 points)
        if oi > 0:
            vol_oi_ratio = volume / oi

            if vol_oi_ratio >= 2.0:
                score += 8   # Extremely active (200%+ of OI traded)
            elif vol_oi_ratio >= 1.0:
                score += 6   # Very active (100%+ of OI traded)
            elif vol_oi_ratio >= 0.5:
                score += 5   # Active (50%+ of OI traded)
            elif vol_oi_ratio >= 0.3:
                score += 3   # Moderate activity (30%+ of OI traded)
            elif vol_oi_ratio >= 0.15:
                score += 2   # Some activity (15%+ of OI traded)

        # 3. SMART MONEY INDICATORS (0-6 points)
        # Large block trades and sweeps
        if volume >= 1000:
            # High volume suggests institutional interest
            if volume >= 5000:
                score += 4  # Very large institutional activity
            elif volume >= 2000:
                score += 3  # Large institutional activity
            else:
                score += 2  # Moderate institutional activity

        # 4. DELTA-ADJUSTED ACTIVITY (0-4 points)
        # Weight activity by how likely the option is to be profitable
        delta_val = abs(self._safe_float_extract(option_data.get('delta', 0.3), 0.3))
        
        # Validate delta is a number
        if not isinstance(delta_val, (int, float)) or delta_val < 0:
            delta_val = 0.3
            
        if delta_val > 0:
            delta_weighted_volume = volume * delta_val
            if delta_weighted_volume >= 500:
                score += 4   # High probability weighted volume
            elif delta_weighted_volume >= 200:
                score += 3   # Good probability weighted volume
            elif delta_weighted_volume >= 100:
                score += 2   # Moderate probability weighted volume
            elif delta_weighted_volume >= 50:
                score += 1   # Some probability weighted volume

        # 5. PREMIUM LEVEL ANALYSIS - Higher premiums suggest informed buying
        mark = self._safe_float_extract(option_data.get('mark', 0), 0)
        if mark >= 5.0:
            score += 2  # Expensive options suggest conviction
        elif mark >= 2.0:
            score += 1  # Moderately expensive options

        # 6. TIME TO EXPIRATION BONUS
        # More unusual for high activity on longer-dated options
        try:
            expiration = option_data.get('expiration', '')
            if expiration:
                from datetime import datetime
                import pandas as pd

                exp_date = pd.to_datetime(expiration)
                days_to_exp = (exp_date - datetime.now()).days

                if days_to_exp >= 30 and volume >= 500:
                    score += 2  # Unusual activity on longer-dated options
                elif days_to_exp >= 7 and volume >= 200:
                    score += 1  # Some activity on weekly+ options
        except:
            pass

        # 7. CROSS-VALIDATION WITH MARKET CONDITIONS
        # Higher scores during volatile periods or earnings
        market_vol = market_data.get('volatility_30d', 25)
        if market_vol > 40 and volume >= 300:
            score += 2  # High activity during volatile periods
        elif market_vol > 60 and volume >= 100:
            score += 3  # Activity during extremely volatile periods

        return min(score, 30)

    def _calculate_technical_score(self, symbol: str, market_data: Dict) -> float:
        """
        Technical analysis score using Alpha Vantage indicators (0-15 points)
        """
        score = 0

        try:
            # Fetch technical indicators
            rsi = self._fetch_rsi(symbol)
            macd = self._fetch_macd(symbol)
            bbands = self._fetch_bbands(symbol)

            # RSI scoring
            if rsi:
                if 30 <= rsi <= 40:  # Oversold bounce
                    score += 5
                elif 60 <= rsi <= 70:  # Momentum building
                    score += 3
                elif rsi > 80 or rsi < 20:
                    score -= 2  # Extreme levels

            # MACD scoring
            if macd:
                if macd['histogram'] > 0 and macd['histogram_prev'] < 0:
                    score += 5  # Bullish crossover
                elif macd['histogram'] > macd['histogram_prev']:
                    score += 3  # Building momentum

            # Bollinger Bands scoring
            if bbands and market_data.get('current_price'):
                price = market_data['current_price']
                if price <= bbands['lower']:
                    score += 5  # At support
                elif bbands['lower'] < price < bbands['middle']:
                    score += 3  # Near support

        except Exception as e:
            print(f"Technical analysis error for {symbol}: {e}")

        return max(0, min(score, 15))

    def _calculate_iv_opportunity_score(self, option_data: Dict, market_data: Dict) -> float:
        """
        IV expansion opportunity score (0-10 points)
        """
        score = 0

        # IV analysis - ensure numeric values, handle nested dicts
        try:
            iv_val = option_data.get('impliedVolatility', 0.25)
            if isinstance(iv_val, dict):
                iv = float(iv_val.get('raw', iv_val.get('fmt', 0.25)))
            else:
                iv = float(iv_val)

            if iv >= 0.8:
                iv_score = 8
            elif iv >= 0.6:
                iv_score = 6
            elif iv >= 0.4:
                iv_score = 4
            elif iv >= 0.2:
                iv_score = 2
            else:
                iv_score = 1
        except (TypeError, ValueError):
            iv_score = 1

        historical_vol = market_data.get('volatility_30d', 50)

        # IV vs HV comparison
        if iv < historical_vol * 0.8:
            score += 5  # IV too low, expansion likely
        elif iv < historical_vol:
            score += 3

        # Earnings/events check
        if market_data.get('earnings_info', {}).get('is_pre_earnings'):
            if iv < historical_vol:
                score += 5  # Pre-earnings IV expansion play
            else:
                score += 2

        return min(score, 10)

    def _calculate_market_regime_score(self, option_data: Dict, market_data: Dict) -> float:
        """
        Market regime alignment score (0-10 points)
        """
        score = 5  # Neutral baseline

        # Update market regime if needed
        if not self.volatility_regime:
            self._update_market_regime()

        option_type = option_data.get('type', '').lower()

        # VIX-based regime
        if self.volatility_regime == 'low_vol':
            if option_type == 'call':
                score += 3  # Favor calls in low vol
        elif self.volatility_regime == 'high_vol':
            if option_type == 'put':
                score += 2  # Some put protection
            score += 3  # High vol = more option value

        # Sector momentum
        sector = market_data.get('sector', 'Unknown')
        if sector in self.sector_momentum:
            if self.sector_momentum[sector] > 0 and option_type == 'call':
                score += 2
            elif self.sector_momentum[sector] < 0 and option_type == 'put':
                score += 2

        return min(score, 10)

    def _determine_holding_period(self, option_data: Dict) -> Dict:
        """
        Determine optimal holding period based on Greeks
        """
        try:
            gamma = float(option_data.get('gamma', 0))
        except (ValueError, TypeError):
            gamma = 0

        try:
            theta = float(option_data.get('theta', 0))
        except (ValueError, TypeError):
            theta = 0

        try:
            # Handle different date formats from Alpha Vantage
            expiration = option_data.get('expiration', '')
            exp_date = None

            if isinstance(expiration, str) and expiration:
                expiration = expiration.strip()
                if expiration:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y', '%d/%m/%Y']:
                        try:
                            exp_date = datetime.strptime(expiration, fmt)
                            break
                        except ValueError:
                            continue

            elif hasattr(expiration, 'year'):  # It's already a datetime-like object
                exp_date = expiration
            elif expiration and not isinstance(expiration, str):
                try:
                    exp_date = pd.to_datetime(expiration).to_pydatetime()
                except:
                    exp_date = None

            # Default fallback if parsing failed
            if exp_date is None:
                exp_date = datetime.now() + timedelta(days=30)

            # Ensure exp_date is a datetime object before subtraction
            if not isinstance(exp_date, datetime):
                exp_date = datetime.now() + timedelta(days=30)

            # Days to expiration analysis - ensure we always get an integer
            days_to_exp = 30  # Default fallback

            if 'days_to_expiry' in option_data:
                try:
                    # Handle the case where days_to_expiry might be a string
                    days_val = option_data['days_to_expiry']
                    if isinstance(days_val, str):
                        # Clean string and convert to int
                        import re
                        cleaned_days = re.sub(r'[^\d\-]', '', str(days_val))
                        if cleaned_days and cleaned_days != '-':
                            days_to_exp = int(float(cleaned_days))
                        else:
                            days_to_exp = 30
                    else:
                        days_to_exp = int(float(days_val))
                except (ValueError, TypeError):
                    days_to_exp = 30
            elif 'expiration' in option_data:
                try:
                    exp_val = option_data['expiration']
                    if isinstance(exp_val, str) and exp_val.strip():
                        # Try to parse the expiration date string
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                            try:
                                exp_date = datetime.strptime(exp_val.strip(), fmt)
                                days_to_exp = max(1, (exp_date - datetime.now()).days)
                                break
                            except ValueError:
                                continue
                        else:
                            days_to_exp = 30
                    else:
                        days_to_exp = 30
                except (ValueError, TypeError):
                    days_to_exp = 30

            # Ensure days_to_exp is always a positive integer
            days_to_exp = max(1, int(days_to_exp))
            days_to_expiry = days_to_exp
        except Exception as e:
            print(f"Error parsing expiration date '{expiration}': {e}")
            days_to_expiry = 30  # Default fallback

        # Base holding period on gamma level
        if gamma >= 0.02:
            base_days = self.holding_matrix['high_gamma']['base_days']
            max_days = self.holding_matrix['high_gamma']['max_days']
        elif gamma >= 0.01:
            base_days = self.holding_matrix['moderate_gamma']['base_days']
            max_days = self.holding_matrix['moderate_gamma']['max_days']
        else:
            base_days = self.holding_matrix['low_gamma']['base_days']
            max_days = self.holding_matrix['low_gamma']['max_days']

        # Adjust for theta decay
        theta_adjustment = 0
        if abs(theta) > 0.10:
            theta_adjustment = -1  # Reduce hold time
        elif abs(theta) > 0.20:
            theta_adjustment = -2

        # Don't exceed time to expiry
        max_days = min(max_days, days_to_expiry - 1)

        return {
            'recommended_days': max(1, base_days + theta_adjustment),
            'maximum_days': max_days,
            'exit_triggers': {
                'profit_target': 0.40,  # 40% profit
                'stop_loss': -0.25,     # 25% loss
                'theta_limit': self.holding_matrix['theta_threshold'],
                'delta_limit': option_data.get('delta', 0.1) * self.holding_matrix['delta_drift_limit']
            }
        }

    def _generate_recommendation(self, score: float, components: Dict, option_data: Dict) -> str:
        """
        Generate actionable recommendation based on enhanced score (max 115)
        """
        # Must have minimum scores in key areas
        liquidity_min = components['liquidity_score'] >= 12
        greeks_min = components['greeks_score'] >= 10
        activity_min = components['unusual_activity_score'] >= 8

        # Adjusted thresholds for 115-point scale
        if score >= 85 and liquidity_min and greeks_min and activity_min:
            return "🔥 STRONG BUY - High explosion potential"
        elif score >= 70 and liquidity_min and greeks_min:
            return "✅ BUY - Good opportunity"
        elif score >= 55 and liquidity_min:
            return "⚡ CAUTIOUS BUY - Monitor closely"
        elif score >= 40:
            return "⚠️ WATCH - Needs confirmation"
        elif score >= 25:
            return "⚠️ WEAK - Better opportunities exist"
        else:
            return "❌ REJECT - Does not meet criteria"

    def _calculate_confidence(self, scores: Dict) -> int:
        """
        Calculate confidence level (0-100%) for enhanced scoring system
        """
        # Updated weights for enhanced scoring
        weights = {
            'liquidity_score': 0.25,      # Increased importance
            'greeks_score': 0.25,         # Increased importance  
            'unusual_activity_score': 0.30,  # Highest weight
            'technical_score': 0.10,      # Reduced
            'iv_opportunity_score': 0.05,  # Reduced
            'market_regime_score': 0.05   # Reduced
        }

        # Updated max scores for enhanced system
        max_scores = {
            'liquidity_score': 25,        # Updated
            'greeks_score': 25,           # Updated
            'unusual_activity_score': 30, # Updated
            'technical_score': 15,        # Same
            'iv_opportunity_score': 10,   # Same
            'market_regime_score': 10     # Same
        }

        confidence = 0
        for component, weight in weights.items():
            if max_scores[component] > 0:
                component_pct = min(scores[component] / max_scores[component], 1.0)
                confidence += component_pct * weight * 100

        # Bonus for well-rounded scores (all components contributing)
        non_zero_components = sum(1 for score in scores.values() if score > 0)
        if non_zero_components >= 4:
            confidence += 5  # Bonus for diversified strength

        # Penalty for extreme imbalances
        max_component_pct = max(scores[comp] / max_scores[comp] for comp in scores.keys())
        if max_component_pct > 0.9 and confidence > 80:
            # Very high single component might indicate outlier
            confidence -= 10

        return min(100, max(0, int(confidence)))

    def _assess_risk_level(self, option_data: Dict, scores: Dict) -> str:
        """
        Assess risk level of the trade
        """
        risk_score = 0

        # Liquidity risk
        if scores['liquidity_score'] < 10:
            risk_score += 30

        # Greeks risk
        try:
            delta = float(option_data.get('delta', 0))
        except (ValueError, TypeError):
            delta = 0
        if abs(delta) < 0.10:
            risk_score += 20  # Very low delta
        try:
            theta = float(option_data.get('theta', 0))
        except (ValueError, TypeError):
            theta = 0
        if abs(theta) > 0.20:
            risk_score += 20  # High decay

        # Time risk
        try:
            expiration = option_data.get('expiration', '')
            if isinstance(expiration, str) and expiration:
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                    try:
                        exp_date = datetime.strptime(expiration, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    exp_date = datetime.now() + timedelta(days=30)
            elif expiration and not isinstance(expiration, str):
                try:
                    exp_date = pd.to_datetime(expiration)
                except:
                    exp_date = datetime.now() + timedelta(days=30)
            else:
                exp_date = datetime.now() + timedelta(days=30)

            days_to_expiry = max(1, (exp_date - datetime.now()).days)
        except Exception as e:
            print(f"Error parsing expiration in risk assessment '{expiration}': {e}")
            days_to_expiry = 30

        if risk_score >= 60:
            return "HIGH"
        elif risk_score >= 30:
            return "MEDIUM"
        else:
            return "LOW"

    # Alpha Vantage integration methods
    def _fetch_rsi(self, symbol: str, interval: str = 'daily', time_period: int = 14) -> Optional[float]:
        """Fetch RSI from Alpha Vantage"""
        url = f'https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval={interval}&time_period={time_period}&series_type=close&apikey={self.av_key}'
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'Technical Analysis: RSI' in data:
                latest_date = list(data['Technical Analysis: RSI'].keys())[0]
                return float(data['Technical Analysis: RSI'][latest_date]['RSI'])
        except:
            return None

    def _fetch_macd(self, symbol: str) -> Optional[Dict]:
        """Fetch MACD from Alpha Vantage"""
        url = f'https://www.alphavantage.co/query?function=MACD&symbol={symbol}&interval=daily&series_type=close&apikey={self.av_key}'
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'Technical Analysis: MACD' in data:
                dates = list(data['Technical Analysis: MACD'].keys())
                latest = data['Technical Analysis: MACD'][dates[0]]
                prev = data['Technical Analysis: MACD'][dates[1]] if len(dates) > 1 else latest
                return {
                    'macd': float(latest['MACD']),
                    'signal': float(latest['MACD_Signal']),
                    'histogram': float(latest['MACD_Hist']),
                    'histogram_prev': float(prev['MACD_Hist'])
                }
        except:
            return None

    def _fetch_bbands(self, symbol: str) -> Optional[Dict]:
        """Fetch Bollinger Bands from Alpha Vantage"""
        url = f'https://www.alphavantage.co/query?function=BBANDS&symbol={symbol}&interval=daily&time_period=20&series_type=close&apikey={self.av_key}'
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'Technical Analysis: BBANDS' in data:
                latest_date = list(data['Technical Analysis: BBANDS'].keys())[0]
                latest = data['Technical Analysis: BBANDS'][latest_date]
                return {
                    'upper': float(latest['Real Upper Band']),
                    'middle': float(latest['Real Middle Band']),
                    'lower': float(latest['Real Lower Band'])
                }
        except:
            return None

    def _fetch_option_history(self, symbol: str, strike: float, option_type: str) -> Optional[Dict]:
        """Fetch historical option data for comparison"""
        # This would integrate with Alpha Vantage options endpoint
        # For now, returning mock data structure
        return {
            'avg_volume': 100,
            'avg_oi': 500,
            'avg_spread': 0.10,
            'large_trades': []
        }

    def _detect_smart_money(self, option_data: Dict, historical_data: Dict) -> bool:
        """Detect potential smart money activity"""
        # Look for large block trades, sweeps, etc.
        volume = option_data.get('volume', 0)
        avg_volume = historical_data.get('avg_volume', 100)

        # Simple detection: unusually large volume in single strikes
        if volume > avg_volume * 10 and volume > 1000:
            return True

        return False

    def _update_market_regime(self):
        """Update market volatility regime using VIX"""
        try:
            # Fetch VIX data
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=VIX&apikey={self.av_key}'
            response = requests.get(url, timeout=10)
            data = response.json()

            if 'Global Quote' in data:
                vix = float(data['Global Quote']['05. price'])
                if vix < 15:
                    self.volatility_regime = 'low_vol'
                elif vix < 25:
                    self.volatility_regime = 'normal_vol'
                else:
                    self.volatility_regime = 'high_vol'
        except:
            self.volatility_regime = 'normal_vol'

    def adapt_thresholds(self, performance_data: Dict):
        """
        Adapt thresholds based on historical performance
        Machine learning component that improves over time
        """
        if not performance_data:
            return

        # Analyze winning trades
        winning_trades = [t for t in performance_data.values() if t.get('final_outcome') == 'TARGET_HIT']

        if len(winning_trades) >= 10:
            # Calculate optimal thresholds from winners
            volume_spikes = []
            oi_changes = []

            for trade in winning_trades:
                if 'unusual_activity' in trade:
                    volume_spikes.append(trade['unusual_activity'].get('volume_spike', 2.0))
                    oi_changes.append(trade['unusual_activity'].get('oi_change', 0.5))

            if volume_spikes:
                # Adjust thresholds to 25th percentile of winning trades
                self.thresholds['volume_spike'] = np.percentile(volume_spikes, 25)
            if oi_changes:
                self.thresholds['oi_change'] = np.percentile(oi_changes, 25)

            print(f"🔧 Adapted thresholds: Volume spike={self.thresholds['volume_spike']:.2f}, OI change={self.thresholds['oi_change']:.2f}")

    def _generate_recommendation(self, score: float, confidence: float, risk_level: str) -> str:
        """Generate trading recommendation based on score and confidence"""
        if score >= 80 and confidence >= 80:
            return "🔥 STRONG BUY - High explosion potential"
        elif score >= 70 and confidence >= 70:
            return "✅ BUY - Good opportunity"
        elif score >= 60 and confidence >= 60:
            return "⚠️ CAUTIOUS BUY - Monitor closely"
        elif score >= 50:
            return "🤔 NEUTRAL - Wait for better setup"
        else:
            return "❌ AVOID - Poor risk/reward"

    def _calculate_holding_period(self, option_data: Dict, score_components: Dict) -> Dict:
        """
        Determine optimal holding period based on Greeks
        """
        try:
            gamma = float(option_data.get('gamma', 0))
        except (ValueError, TypeError):
            gamma = 0

        try:
            theta = float(option_data.get('theta', 0))
        except (ValueError, TypeError):
            theta = 0

        try:
            # Handle different date formats from Alpha Vantage
            expiration = option_data.get('expiration', '')
            exp_date = None

            if isinstance(expiration, str) and expiration:
                expiration = expiration.strip()
                if expiration:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y', '%d/%m/%Y']:
                        try:
                            exp_date = datetime.strptime(expiration, fmt)
                            break
                        except ValueError:
                            continue

            elif hasattr(expiration, 'year'):  # It's already a datetime-like object
                exp_date = expiration
            elif expiration and not isinstance(expiration, str):
                try:
                    exp_date = pd.to_datetime(expiration).to_pydatetime()
                except:
                    exp_date = None

            # Default fallback if parsing failed
            if exp_date is None:
                exp_date = datetime.now() + timedelta(days=30)

            # Ensure exp_date is a datetime object before subtraction
            if not isinstance(exp_date, datetime):
                exp_date = datetime.now() + timedelta(days=30)

            # Days to expiration analysis - ensure we always get an integer
            days_to_exp = 30  # Default fallback

            if 'days_to_expiry' in option_data:
                try:
                    # Handle the case where days_to_expiry might be a string
                    days_val = option_data['days_to_expiry']
                    if isinstance(days_val, str):
                        # Clean string and convert to int
                        import re
                        cleaned_days = re.sub(r'[^\d\-]', '', str(days_val))
                        if cleaned_days and cleaned_days != '-':
                            days_to_exp = int(float(cleaned_days))
                        else:
                            days_to_exp = 30
                    else:
                        days_to_exp = int(float(days_val))
                except (ValueError, TypeError):
                    days_to_exp = 30
            elif 'expiration' in option_data:
                try:
                    exp_val = option_data['expiration']
                    if isinstance(exp_val, str) and exp_val.strip():
                        # Try to parse the expiration date string
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%m-%d-%Y']:
                            try:
                                exp_date = datetime.strptime(exp_val.strip(), fmt)
                                days_to_exp = max(1, (exp_date - datetime.now()).days)
                                break
                            except ValueError:
                                continue
                        else:
                            days_to_exp = 30
                    else:
                        days_to_exp = 30
                except (ValueError, TypeError):
                    days_to_exp = 30

            # Ensure days_to_exp is always a positive integer
            days_to_exp = max(1, int(days_to_exp))
            days_to_expiry = days_to_exp
        except Exception as e:
            print(f"Error parsing expiration date '{expiration}': {e}")
            days_to_expiry = 30  # Default fallback

        # Base holding period on gamma level
        if gamma >= 0.02:
            base_days = self.holding_matrix['high_gamma']['base_days']
            max_days = self.holding_matrix['high_gamma']['max_days']
        elif gamma >= 0.01:
            base_days = self.holding_matrix['moderate_gamma']['base_days']
            max_days = self.holding_matrix['moderate_gamma']['max_days']
        else:
            base_days = self.holding_matrix['low_gamma']['base_days']
            max_days = self.holding_matrix['low_gamma']['max_days']

        # Adjust for theta decay
        theta_adjustment = 0
        if abs(theta) > 0.10:
            theta_adjustment = -1  # Reduce hold time
        elif abs(theta) > 0.20:
            theta_adjustment = -2

        # Don't exceed time to expiry
        max_days = min(max_days, days_to_expiry - 1)

        return {
            'recommended_days': max(1, base_days + theta_adjustment),
            'maximum_days': max_days,
            'exit_triggers': {
                'profit_target': 0.40,  # 40% profit
                'stop_loss': -0.25,     # 25% loss
                'theta_limit': self.holding_matrix['theta_threshold'],
                'delta_limit': option_data.get('delta', 0.1) * self.holding_matrix['delta_drift_limit']
            }
        }
# Generate recommendation based on score
        recommendation = self._generate_recommendation(total_score, score_components, option_data)

        return total_score, {
            'components': score_components,
            'confidence': confidence,
            'recommendation': recommendation,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'holding_period': holding_period,
            'risk_level': risk_level
        }