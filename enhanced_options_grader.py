
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
    
    def calculate_option_score(self, option_data: Dict, market_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate comprehensive option score (0-100) with detailed breakdown
        """
        scores = {
            'liquidity_score': 0,
            'greeks_score': 0,
            'unusual_activity_score': 0,
            'technical_score': 0,
            'iv_opportunity_score': 0,
            'market_regime_score': 0
        }
        
        # 1. LIQUIDITY SCORE (0-20 points)
        liquidity_score = self._calculate_liquidity_score(option_data)
        scores['liquidity_score'] = liquidity_score
        
        # Early exit for illiquid options
        if liquidity_score < 5:
            return 0, {
                'total_score': 0,
                'components': scores,
                'recommendation': 'REJECT - Insufficient liquidity',
                'holding_period': 0
            }
        
        # 2. GREEKS SCORE (0-20 points)
        greeks_score = self._calculate_greeks_score(option_data)
        scores['greeks_score'] = greeks_score
        
        # 3. UNUSUAL ACTIVITY SCORE (0-25 points) - Highest weight for "explosive" detection
        unusual_score = self._calculate_unusual_activity_score(option_data, market_data)
        scores['unusual_activity_score'] = unusual_score
        
        # 4. TECHNICAL SCORE (0-15 points)
        technical_score = self._calculate_technical_score(option_data['symbol'], market_data)
        scores['technical_score'] = technical_score
        
        # 5. IV OPPORTUNITY SCORE (0-10 points)
        iv_score = self._calculate_iv_opportunity_score(option_data, market_data)
        scores['iv_opportunity_score'] = iv_score
        
        # 6. MARKET REGIME SCORE (0-10 points)
        regime_score = self._calculate_market_regime_score(option_data, market_data)
        scores['market_regime_score'] = regime_score
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Determine holding period based on Greeks
        holding_period = self._determine_holding_period(option_data)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(total_score, scores, option_data)
        
        return total_score, {
            'total_score': total_score,
            'components': scores,
            'recommendation': recommendation,
            'holding_period': holding_period,
            'confidence': self._calculate_confidence(scores),
            'risk_level': self._assess_risk_level(option_data, scores)
        }
    
    def _calculate_liquidity_score(self, option_data: Dict) -> float:
        """
        Assess option liquidity (0-20 points)
        """
        score = 0
        
        # Convert strings to numbers safely
        try:
            volume = float(option_data.get('volume', 0))
        except (ValueError, TypeError):
            volume = 0
            
        try:
            oi = float(option_data.get('open_interest', 0))
        except (ValueError, TypeError):
            oi = 0
        
        # Volume check
        if volume >= 1000:
            score += 8
        elif volume >= 500:
            score += 6
        elif volume >= 100:
            score += 4
        elif volume >= 50:
            score += 2
        else:
            return 0  # Reject if volume too low
        
        # Open Interest check
        if oi >= 5000:
            score += 5
        elif oi >= 1000:
            score += 3
        elif oi >= 100:
            score += 1
        else:
            return score * 0.5  # Penalize low OI
        
        # Volume/OI ratio
        if oi > 0:
            vol_oi_ratio = volume / oi
            if vol_oi_ratio >= 0.5:
                score += 4  # Very active
            elif vol_oi_ratio >= 0.2:
                score += 2
        
        # Bid-ask spread
        try:
            bid = float(option_data.get('bid', 0))
            ask = float(option_data.get('ask', 0))
        except (ValueError, TypeError):
            bid = 0
            ask = 0
            
        if bid > 0 and ask > 0:
            spread = (ask - bid) / ask
            if spread <= 0.05:
                score += 3
            elif spread <= 0.10:
                score += 2
            elif spread <= 0.15:
                score += 1
            # Penalty for wide spreads like COST example
            elif spread > 0.30:
                score *= 0.5
        
        return min(score, 20)
    
    def _calculate_greeks_score(self, option_data: Dict) -> float:
        """
        Evaluate Greeks for explosive potential (0-20 points)
        """
        score = 0
        
        # Convert strings to numbers safely
        try:
            delta = abs(float(option_data.get('delta', 0)))
        except (ValueError, TypeError):
            delta = 0
            
        try:
            gamma = float(option_data.get('gamma', 0))
        except (ValueError, TypeError):
            gamma = 0
            
        try:
            theta = float(option_data.get('theta', 0))
        except (ValueError, TypeError):
            theta = 0
            
        try:
            vega = float(option_data.get('vega', 0))
        except (ValueError, TypeError):
            vega = 0
            
        try:
            mark = float(option_data.get('mark', 1))
        except (ValueError, TypeError):
            mark = 1
        
        # Delta scoring - prefer 0.15-0.35 for explosive moves
        if 0.15 <= delta <= 0.35:
            score += 6  # Sweet spot for leverage
        elif 0.10 <= delta <= 0.40:
            score += 4
        elif delta < 0.10:
            score += 2  # Too far OTM
        else:
            score += 1  # Too expensive/low leverage
        
        # Gamma scoring - higher gamma = more explosive
        if gamma >= 0.02:
            score += 5
        elif gamma >= 0.01:
            score += 3
        elif gamma >= 0.005:
            score += 1
        
        # Theta scoring - penalize high decay
        theta_per_dollar = abs(theta) / max(mark, 0.01)
        if theta_per_dollar <= 0.05:
            score += 4  # Low decay rate
        elif theta_per_dollar <= 0.10:
            score += 2
        elif theta_per_dollar > 0.20:
            score -= 2  # Too much decay
        
        # Vega scoring - opportunity for IV expansion
        if vega >= 0.05:
            score += 5
        elif vega >= 0.02:
            score += 3
        elif vega >= 0.01:
            score += 1
        
        return max(0, min(score, 20))
    
    def _calculate_unusual_activity_score(self, option_data: Dict, market_data: Dict) -> float:
        """
        Detect unusual options activity indicating potential explosion (0-25 points)
        """
        score = 0
        
        # Convert strings to numbers safely
        try:
            volume = float(option_data.get('volume', 0))
        except (ValueError, TypeError):
            volume = 0
            
        try:
            oi = float(option_data.get('open_interest', 0))
        except (ValueError, TypeError):
            oi = 0
        
        # Get historical averages from Alpha Vantage
        symbol = option_data['symbol']
        historical_data = self._fetch_option_history(symbol, option_data.get('strike', 0), option_data.get('type', 'call'))
        
        if not historical_data:
            # Fallback to basic unusual activity detection
            if volume > 0 and oi > 0:
                vol_oi = volume / oi
                if vol_oi >= 1.0:
                    score += 10
                elif vol_oi >= 0.5:
                    score += 7
                elif vol_oi >= 0.2:
                    score += 4
        else:
            # Advanced unusual activity detection
            avg_volume = historical_data.get('avg_volume', 1)
            avg_oi = historical_data.get('avg_oi', 1)
            
            # Volume spike detection
            volume_ratio = option_data.get('volume', 0) / max(avg_volume, 1)
            if volume_ratio >= 5.0:
                score += 12  # Massive spike
            elif volume_ratio >= 3.0:
                score += 8
            elif volume_ratio >= 2.0:
                score += 5
            
            # OI change detection
            oi_change = (option_data.get('open_interest', 0) - avg_oi) / max(avg_oi, 1)
            if oi_change >= 1.0:
                score += 8  # 100%+ increase
            elif oi_change >= 0.5:
                score += 5
            elif oi_change >= 0.25:
                score += 3
            
            # Smart money detection (large trades)
            if self._detect_smart_money(option_data, historical_data):
                score += 5
        
        return min(score, 25)
    
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
        
        iv = option_data.get('implied_volatility', 0) * 100
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
            if isinstance(expiration, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        exp_date = datetime.strptime(expiration, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format works, default to 30 days
                    exp_date = datetime.now() + timedelta(days=30)
            else:
                exp_date = pd.to_datetime(expiration)
            
            days_to_expiry = max(1, (exp_date - datetime.now()).days)
        except:
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
    
    def _generate_recommendation(self, total_score: float, components: Dict, option_data: Dict) -> str:
        """
        Generate actionable recommendation based on score
        """
        if total_score >= 75:
            return "🔥 STRONG BUY - High explosion potential"
        elif total_score >= 60:
            return "✅ BUY - Good opportunity"
        elif total_score >= 45:
            return "⚡ WATCH - Needs confirmation"
        elif total_score >= 30:
            return "⚠️ WEAK - Better opportunities exist"
        else:
            return "❌ REJECT - Does not meet criteria"
    
    def _calculate_confidence(self, scores: Dict) -> int:
        """
        Calculate confidence level (0-100%)
        """
        # Weight different components
        weights = {
            'liquidity_score': 0.20,
            'greeks_score': 0.20,
            'unusual_activity_score': 0.30,
            'technical_score': 0.15,
            'iv_opportunity_score': 0.10,
            'market_regime_score': 0.05
        }
        
        max_scores = {
            'liquidity_score': 20,
            'greeks_score': 20,
            'unusual_activity_score': 25,
            'technical_score': 15,
            'iv_opportunity_score': 10,
            'market_regime_score': 10
        }
        
        confidence = 0
        for component, weight in weights.items():
            if max_scores[component] > 0:
                component_pct = scores[component] / max_scores[component]
                confidence += component_pct * weight * 100
        
        return int(confidence)
    
    def _assess_risk_level(self, option_data: Dict, scores: Dict) -> str:
        """
        Assess risk level of the trade
        """
        risk_score = 0
        
        # Liquidity risk
        if scores['liquidity_score'] < 10:
            risk_score += 30
        
        # Greeks risk
        if abs(option_data.get('delta', 0)) < 0.10:
            risk_score += 20  # Very low delta
        if abs(option_data.get('theta', 0)) > 0.20:
            risk_score += 20  # High decay
        
        # Time risk
        try:
            expiration = option_data.get('expiration', '')
            if isinstance(expiration, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        exp_date = datetime.strptime(expiration, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    exp_date = datetime.now() + timedelta(days=30)
            else:
                exp_date = pd.to_datetime(expiration)
            
            days_to_expiry = max(1, (exp_date - datetime.now()).days)
        except:
            days_to_expiry = 30
            
        if days_to_expiry < 7:
            risk_score += 30
        
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
