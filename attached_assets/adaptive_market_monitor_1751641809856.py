# adaptive_market_monitor.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import json
import os
import yfinance as yf
from collections import deque

class AdaptiveMarketMonitor:
    """
    Real-time market regime detection and position monitoring
    Continuously adapts to market conditions and generates exit signals
    """
    
    def __init__(self, alpha_vantage_key: str):
        self.av_key = alpha_vantage_key
        
        # Market regime parameters
        self.regime_state = {
            'volatility': 'normal',
            'trend': 'neutral',
            'breadth': 'mixed',
            'sentiment': 'neutral',
            'last_update': None
        }
        
        # Sector performance tracking
        self.sector_performance = {}
        
        # Position tracking
        self.active_positions = {}
        
        # Alert thresholds
        self.alert_thresholds = {
            'profit_alert': 0.20,  # Alert at 20% profit
            'loss_alert': -0.15,   # Alert at 15% loss
            'theta_alert': -0.20,  # Alert if theta exceeds $0.20
            'volume_spike': 3.0,   # Alert on 3x volume
            'iv_change': 0.15      # Alert on 15% IV change
        }
        
        # Historical data for pattern detection
        self.market_history = {
            'vix': deque(maxlen=20),
            'spy': deque(maxlen=20),
            'breadth': deque(maxlen=10)
        }
    
    def update_market_regime(self) -> Dict:
        """
        Comprehensive market regime analysis using multiple indicators
        """
        regime_update = {
            'timestamp': datetime.now().isoformat(),
            'changes': []
        }
        
        # 1. Volatility Regime (VIX-based)
        vix_data = self._fetch_vix_data()
        if vix_data:
            old_vol_regime = self.regime_state['volatility']
            new_vol_regime = self._classify_volatility_regime(vix_data)
            
            if new_vol_regime != old_vol_regime:
                self.regime_state['volatility'] = new_vol_regime
                regime_update['changes'].append({
                    'type': 'volatility',
                    'from': old_vol_regime,
                    'to': new_vol_regime,
                    'impact': self._assess_volatility_impact(new_vol_regime)
                })
        
        # 2. Market Trend (SPY momentum)
        spy_trend = self._analyze_market_trend()
        if spy_trend != self.regime_state['trend']:
            old_trend = self.regime_state['trend']
            self.regime_state['trend'] = spy_trend
            regime_update['changes'].append({
                'type': 'trend',
                'from': old_trend,
                'to': spy_trend,
                'impact': self._assess_trend_impact(spy_trend)
            })
        
        # 3. Market Breadth (advance/decline)
        breadth = self._analyze_market_breadth()
        if breadth != self.regime_state['breadth']:
            old_breadth = self.regime_state['breadth']
            self.regime_state['breadth'] = breadth
            regime_update['changes'].append({
                'type': 'breadth',
                'from': old_breadth,
                'to': breadth,
                'impact': self._assess_breadth_impact(breadth)
            })
        
        # 4. Sentiment Analysis (put/call ratio, fear/greed)
        sentiment = self._analyze_market_sentiment()
        if sentiment != self.regime_state['sentiment']:
            old_sentiment = self.regime_state['sentiment']
            self.regime_state['sentiment'] = sentiment
            regime_update['changes'].append({
                'type': 'sentiment',
                'from': old_sentiment,
                'to': sentiment,
                'impact': self._assess_sentiment_impact(sentiment)
            })
        
        # 5. Sector Rotation
        self._update_sector_performance()
        
        self.regime_state['last_update'] = datetime.now()
        regime_update['current_regime'] = self.regime_state.copy()
        regime_update['trading_adjustments'] = self._generate_regime_adjustments()
        
        return regime_update
    
    def monitor_position(self, position_id: str, position_data: Dict) -> Dict:
        """
        Monitor an active position and generate alerts/exit signals
        """
        if position_id not in self.active_positions:
            self.active_positions[position_id] = {
                'entry_data': position_data,
                'entry_time': datetime.now(),
                'alerts_triggered': [],
                'exit_signals': [],
                'performance_history': []
            }
        
        position = self.active_positions[position_id]
        monitoring_result = {
            'position_id': position_id,
            'timestamp': datetime.now().isoformat(),
            'alerts': [],
            'exit_signals': [],
            'adjustments': []
        }
        
        # Get current option data
        current_data = self._fetch_current_option_data(
            position_data['symbol'],
            position_data['option_details']
        )
        
        if not current_data:
            monitoring_result['alerts'].append({
                'type': 'DATA_ERROR',
                'message': 'Unable to fetch current option data',
                'severity': 'HIGH'
            })
            return monitoring_result
        
        # Calculate performance metrics
        entry_price = position_data['option_details']['current_price']
        current_price = current_data['mark']
        pnl_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Record performance
        position['performance_history'].append({
            'timestamp': datetime.now(),
            'price': current_price,
            'pnl_percent': pnl_percent,
            'delta': current_data.get('delta'),
            'theta': current_data.get('theta'),
            'volume': current_data.get('volume')
        })
        
        # 1. Check profit targets
        targets = position_data.get('targets', {})
        for target_name, target_info in targets.items():
            if current_price >= target_info['price']:
                exit_signal = {
                    'type': 'PROFIT_TARGET_HIT',
                    'target': target_name,
                    'target_price': target_info['price'],
                    'current_price': current_price,
                    'action': f"Consider taking profits - {target_name} reached",
                    'urgency': 'HIGH'
                }
                monitoring_result['exit_signals'].append(exit_signal)
        
        # 2. Check stop loss
        stop_loss = position_data.get('stop_loss', {})
        if current_price <= stop_loss.get('stop_price', 0):
            exit_signal = {
                'type': 'STOP_LOSS_TRIGGERED',
                'stop_price': stop_loss['stop_price'],
                'current_price': current_price,
                'action': 'EXIT IMMEDIATELY - Stop loss hit',
                'urgency': 'CRITICAL'
            }
            monitoring_result['exit_signals'].append(exit_signal)
        
        # 3. Check Greeks deterioration
        greeks_alerts = self._check_greeks_deterioration(
            position_data['option_details'],
            current_data,
            position_data.get('exit_strategy', {})
        )
        monitoring_result['alerts'].extend(greeks_alerts)
        
        # 4. Check unusual activity
        activity_alerts = self._check_unusual_activity(
            position_data['symbol'],
            current_data
        )
        monitoring_result['alerts'].extend(activity_alerts)
        
        # 5. Check technical breakdown
        technical_alerts = self._check_technical_conditions(
            position_data['symbol'],
            position_data['option_details']['type']
        )
        monitoring_result['alerts'].extend(technical_alerts)
        
        # 6. Time-based checks
        time_alerts = self._check_time_conditions(
            position,
            position_data.get('exit_strategy', {})
        )
        monitoring_result['alerts'].extend(time_alerts)
        
        # 7. Generate position adjustments based on market regime
        adjustments = self._generate_position_adjustments(
            position_data,
            current_data,
            pnl_percent
        )
        monitoring_result['adjustments'] = adjustments
        
        # 8. Update trailing stop if needed
        if pnl_percent >= 10 and stop_loss.get('stop_type') == 'TRAILING_STOP':
            new_stop = self._calculate_trailing_stop(
                current_price,
                stop_loss.get('trail_percentage', 15)
            )
            if new_stop > stop_loss.get('stop_price', 0):
                monitoring_result['adjustments'].append({
                    'type': 'TRAILING_STOP_UPDATE',
                    'old_stop': stop_loss['stop_price'],
                    'new_stop': new_stop,
                    'action': f"Update trailing stop to ${new_stop:.2f}"
                })
        
        # Save monitoring result
        position['last_monitor'] = monitoring_result
        
        return monitoring_result
    
    def generate_exit_signals(self, position_id: str) -> List[Dict]:
        """
        Generate comprehensive exit signals based on all factors
        """
        if position_id not in self.active_positions:
            return []
        
        position = self.active_positions[position_id]
        exit_signals = []
        
        # Aggregate all recent alerts and signals
        recent_monitor = position.get('last_monitor', {})
        
        # Priority 1: Stop loss or critical alerts
        critical_signals = [s for s in recent_monitor.get('exit_signals', []) 
                          if s.get('urgency') == 'CRITICAL']
        if critical_signals:
            return critical_signals
        
        # Priority 2: Profit targets
        profit_signals = [s for s in recent_monitor.get('exit_signals', [])
                         if s.get('type') == 'PROFIT_TARGET_HIT']
        if profit_signals:
            exit_signals.extend(profit_signals)
        
        # Priority 3: High severity alerts
        high_alerts = [a for a in recent_monitor.get('alerts', [])
                      if a.get('severity') == 'HIGH']
        
        # Convert high alerts to exit signals if multiple
        if len(high_alerts) >= 2:
            exit_signals.append({
                'type': 'MULTIPLE_HIGH_ALERTS',
                'alerts': high_alerts,
                'action': 'Consider exiting - multiple warning signals',
                'urgency': 'MEDIUM'
            })
        
        # Priority 4: Market regime changes
        if self.regime_state['volatility'] == 'extreme':
            exit_signals.append({
                'type': 'EXTREME_VOLATILITY',
                'action': 'Consider reducing position in extreme volatility',
                'urgency': 'MEDIUM'
            })
        
        return exit_signals
    
    def _classify_volatility_regime(self, vix_data: Dict) -> str:
        """Classify volatility regime based on VIX levels and trend"""
        vix = vix_data.get('current', 20)
        vix_ma = vix_data.get('ma_20', 20)
        
        self.market_history['vix'].append(vix)
        
        if vix < 12:
            return 'ultra_low'
        elif vix < 16:
            return 'low'
        elif vix < 20:
            return 'normal'
        elif vix < 30:
            return 'elevated'
        elif vix < 40:
            return 'high'
        else:
            return 'extreme'
    
    def _analyze_market_trend(self) -> str:
        """Analyze overall market trend using SPY"""
        try:
            # Fetch SPY data
            spy = yf.Ticker('SPY')
            hist = spy.history(period='1mo')
            
            if hist.empty:
                return self.regime_state['trend']
            
            # Calculate trend metrics
            current = hist['Close'].iloc[-1]
            sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma_50 = hist['Close'].rolling(20).mean().iloc[-1]  # Using 20 as proxy
            
            # Trend strength
            if current > sma_20 * 1.02 and sma_20 > sma_50:
                return 'strong_uptrend'
            elif current > sma_20 and sma_20 > sma_50:
                return 'uptrend'
            elif current < sma_20 * 0.98 and sma_20 < sma_50:
                return 'strong_downtrend'
            elif current < sma_20 and sma_20 < sma_50:
                return 'downtrend'
            else:
                return 'neutral'
                
        except:
            return 'neutral'
    
    def _analyze_market_breadth(self) -> str:
        """Analyze market breadth using advance/decline data"""
        # This would use Alpha Vantage sector performance endpoint
        # For now, using simplified logic
        try:
            # Fetch sector performances
            sectors = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLB', 'XLRE', 'XLU']
            advances = 0
            declines = 0
            
            for sector in sectors:
                ticker = yf.Ticker(sector)
                hist = ticker.history(period='5d')
                if not hist.empty:
                    change = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
                    if change > 0:
                        advances += 1
                    else:
                        declines += 1
            
            ratio = advances / (advances + declines) if (advances + declines) > 0 else 0.5
            
            if ratio > 0.7:
                return 'strong_positive'
            elif ratio > 0.6:
                return 'positive'
            elif ratio < 0.3:
                return 'strong_negative'
            elif ratio < 0.4:
                return 'negative'
            else:
                return 'mixed'
                
        except:
            return 'mixed'
    
    def _analyze_market_sentiment(self) -> str:
        """Analyze market sentiment using put/call ratio and other indicators"""
        # This would integrate with CBOE put/call data via Alpha Vantage
        # Simplified version for now
        try:
            # Use VIX as proxy for sentiment
            vix_level = self.market_history['vix'][-1] if self.market_history['vix'] else 20
            
            if vix_level < 15:
                return 'complacent'
            elif vix_level < 20:
                return 'bullish'
            elif vix_level < 25:
                return 'neutral'
            elif vix_level < 35:
                return 'bearish'
            else:
                return 'fearful'
                
        except:
            return 'neutral'
    
    def _update_sector_performance(self):
        """Update sector rotation analysis"""
        sectors = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLE': 'Energy',
            'XLV': 'Healthcare',
            'XLI': 'Industrials',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities'
        }
        
        for etf, sector_name in sectors.items():
            try:
                ticker = yf.Ticker(etf)
                hist = ticker.history(period='1mo')
                if not hist.empty:
                    # Calculate momentum
                    returns_5d = (hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]
                    returns_20d = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
                    
                    self.sector_performance[sector_name] = {
                        'momentum_5d': returns_5d,
                        'momentum_20d': returns_20d,
                        'relative_strength': returns_20d  # Would compare to SPY
                    }
            except:
                continue
    
    def _fetch_vix_data(self) -> Optional[Dict]:
        """Fetch VIX data from Alpha Vantage"""
        try:
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=VIX&apikey={self.av_key}'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'Global Quote' in data:
                current_vix = float(data['Global Quote']['05. price'])
                
                # Also get SMA for trend
                sma_url = f'https://www.alphavantage.co/query?function=SMA&symbol=VIX&interval=daily&time_period=20&series_type=close&apikey={self.av_key}'
                sma_response = requests.get(sma_url, timeout=10)
                sma_data = sma_response.json()
                
                ma_20 = 20  # Default
                if 'Technical Analysis: SMA' in sma_data:
                    latest_date = list(sma_data['Technical Analysis: SMA'].keys())[0]
                    ma_20 = float(sma_data['Technical Analysis: SMA'][latest_date]['SMA'])
                
                return {
                    'current': current_vix,
                    'ma_20': ma_20,
                    'trend': 'rising' if current_vix > ma_20 else 'falling'
                }
        except:
            return None
    
    def _fetch_current_option_data(self, symbol: str, option_details: Dict) -> Optional[Dict]:
        """Fetch current option data for monitoring"""
        try:
            ticker = yf.Ticker(symbol)
            exp_date = option_details['expiration']
            
            # Get option chain
            options = ticker.option_chain(exp_date)
            
            if option_details['type'].lower() == 'call':
                chain = options.calls
            else:
                chain = options.puts
            
            # Find matching strike
            strike = float(option_details['strike'])
            matching = chain[chain['strike'] == strike]
            
            if not matching.empty:
                option = matching.iloc[0]
                return {
                    'mark': float(option['lastPrice']),
                    'bid': float(option['bid']),
                    'ask': float(option['ask']),
                    'volume': int(option['volume']) if pd.notna(option['volume']) else 0,
                    'open_interest': int(option['openInterest']) if pd.notna(option['openInterest']) else 0,
                    'delta': float(option.get('delta', 0)),
                    'gamma': float(option.get('gamma', 0)),
                    'theta': float(option.get('theta', 0)),
                    'vega': float(option.get('vega', 0)),
                    'implied_volatility': float(option['impliedVolatility'])
                }
        except Exception as e:
            print(f"Error fetching option data: {e}")
            return None
    
    def _check_greeks_deterioration(self, entry_greeks: Dict, current_greeks: Dict, 
                                  exit_strategy: Dict) -> List[Dict]:
        """Check for Greeks-based exit signals"""
        alerts = []
        
        # Delta deterioration
        entry_delta = entry_greeks.get('delta', 0.1)
        current_delta = current_greeks.get('delta', 0.1)
        delta_limit = exit_strategy.get('defensive_exits', {}).get('delta_deterioration', {}).get('trigger', 0.05)
        
        if current_delta < entry_delta * 0.5:
            alerts.append({
                'type': 'DELTA_DETERIORATION',
                'message': f'Delta dropped to {current_delta:.3f} from {entry_delta:.3f}',
                'severity': 'HIGH',
                'action': 'Consider exiting - option losing directional exposure'
            })
        
        # Theta acceleration
        current_theta = abs(current_greeks.get('theta', 0))
        theta_limit = 0.15  # Default limit
        
        if current_theta > theta_limit:
            alerts.append({
                'type': 'THETA_ACCELERATION',
                'message': f'Theta decay accelerated to ${current_theta:.2f}/day',
                'severity': 'HIGH' if current_theta > 0.20 else 'MEDIUM',
                'action': 'Time decay exceeding acceptable levels'
            })
        
        # Gamma risk (for short-dated options)
        current_gamma = current_greeks.get('gamma', 0)
        if current_gamma > 0.05:
            alerts.append({
                'type': 'HIGH_GAMMA_RISK',
                'message': f'Gamma at {current_gamma:.3f} - high volatility risk',
                'severity': 'MEDIUM',
                'action': 'Position highly sensitive to price moves'
            })
        
        return alerts
    
    def _check_unusual_activity(self, symbol: str, current_data: Dict) -> List[Dict]:
        """Check for unusual options activity"""
        alerts = []
        
        current_volume = current_data.get('volume', 0)
        current_oi = current_data.get('open_interest', 1)
        
        # Volume spike detection
        if current_oi > 0:
            vol_oi_ratio = current_volume / current_oi
            if vol_oi_ratio > self.alert_thresholds['volume_spike']:
                alerts.append({
                    'type': 'UNUSUAL_VOLUME',
                    'message': f'Volume spike detected: {vol_oi_ratio:.1f}x open interest',
                    'severity': 'MEDIUM',
                    'action': 'Monitor for potential reversal or acceleration'
                })
        
        # IV change detection
        # Would compare to entry IV in production
        current_iv = current_data.get('implied_volatility', 0)
        # Placeholder - would track IV changes
        
        return alerts
    
    def _check_technical_conditions(self, symbol: str, option_type: str) -> List[Dict]:
        """Check technical conditions for the underlying"""
        alerts = []
        
        try:
            # Get current technical data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d', interval='1h')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
                
                # Support/resistance breaks
                if option_type.lower() == 'call' and current < sma_20 * 0.98:
                    alerts.append({
                        'type': 'TECHNICAL_BREAKDOWN',
                        'message': f'{symbol} broke below 20-period SMA',
                        'severity': 'HIGH',
                        'action': 'Consider exiting calls - technical breakdown'
                    })
                elif option_type.lower() == 'put' and current > sma_20 * 1.02:
                    alerts.append({
                        'type': 'TECHNICAL_BREAKOUT',
                        'message': f'{symbol} broke above 20-period SMA',
                        'severity': 'HIGH',
                        'action': 'Consider exiting puts - technical breakout'
                    })
                
                # Volume analysis
                recent_volume = hist['Volume'].iloc[-5:].mean()
                avg_volume = hist['Volume'].mean()
                
                if recent_volume < avg_volume * 0.5:
                    alerts.append({
                        'type': 'LOW_VOLUME',
                        'message': 'Unusually low volume in underlying',
                        'severity': 'LOW',
                        'action': 'Momentum may be fading'
                    })
                    
        except:
            pass
        
        return alerts
    
    def _check_time_conditions(self, position: Dict, exit_strategy: Dict) -> List[Dict]:
        """Check time-based exit conditions"""
        alerts = []
        
        entry_time = position['entry_time']
        time_held = (datetime.now() - entry_time).days
        
        # Get recommended holding period
        max_hold = exit_strategy.get('defensive_exits', {}).get('time_decay', {}).get('trigger', '5 days')
        max_days = int(max_hold.split()[1]) if 'days' in max_hold else 5
        
        if time_held >= max_days:
            alerts.append({
                'type': 'MAX_TIME_REACHED',
                'message': f'Position held for {time_held} days (max: {max_days})',
                'severity': 'MEDIUM',
                'action': 'Consider exiting or reducing position'
            })
        elif time_held >= max_days * 0.75:
            alerts.append({
                'type': 'APPROACHING_MAX_TIME',
                'message': f'Position held for {time_held} days, approaching max hold time',
                'severity': 'LOW',
                'action': 'Prepare exit strategy'
            })
        
        return alerts
    
    def _generate_position_adjustments(self, position_data: Dict, 
                                     current_data: Dict, pnl_percent: float) -> List[Dict]:
        """Generate position adjustments based on current conditions"""
        adjustments = []
        
        # Rolling opportunities
        if pnl_percent > 50:
            adjustments.append({
                'type': 'ROLL_OPPORTUNITY',
                'action': 'Consider rolling up strikes to lock in profits',
                'details': 'Position up 50%+, can roll to higher strike for continued upside'
            })
        
        # Partial profit taking
        if pnl_percent > 30 and position_data.get('position_sizing', {}).get('contracts', 1) > 1:
            adjustments.append({
                'type': 'PARTIAL_PROFIT',
                'action': 'Consider taking partial profits',
                'details': 'Sell 25-50% of position to lock in gains'
            })
        
        # Hedging suggestions
        if self.regime_state['volatility'] in ['high', 'extreme']:
            adjustments.append({
                'type': 'HEDGE_SUGGESTION',
                'action': 'Consider adding protective puts',
                'details': 'High volatility regime - hedging recommended'
            })
        
        return adjustments
    
    def _calculate_trailing_stop(self, current_price: float, trail_percentage: float) -> float:
        """Calculate new trailing stop level"""
        return round(current_price * (1 - trail_percentage / 100), 2)
    
    def _generate_regime_adjustments(self) -> Dict:
        """Generate trading adjustments based on current regime"""
        adjustments = {
            'position_sizing': 'normal',
            'holding_period': 'normal',
            'entry_criteria': 'normal',
            'profit_targets': 'normal'
        }
        
        # Volatility adjustments
        if self.regime_state['volatility'] in ['high', 'extreme']:
            adjustments['position_sizing'] = 'reduce by 30-50%'
            adjustments['holding_period'] = 'shorten by 30%'
            adjustments['profit_targets'] = 'widen targets by 20%'
        elif self.regime_state['volatility'] == 'ultra_low':
            adjustments['position_sizing'] = 'can increase by 20%'
            adjustments['entry_criteria'] = 'be more selective'
        
        # Trend adjustments
        if self.regime_state['trend'] in ['strong_uptrend', 'strong_downtrend']:
            adjustments['holding_period'] = 'can extend if trend continues'
        elif self.regime_state['trend'] == 'neutral':
            adjustments['holding_period'] = 'stick to shorter timeframes'
        
        # Breadth adjustments
        if self.regime_state['breadth'] in ['strong_negative', 'negative']:
            adjustments['entry_criteria'] = 'require higher conviction scores'
            adjustments['position_sizing'] = 'reduce by 20%'
        
        return adjustments
    
    def _assess_volatility_impact(self, regime: str) -> str:
        """Assess impact of volatility regime on options trading"""
        impacts = {
            'ultra_low': 'Option premiums compressed - focus on earnings/events',
            'low': 'Good for selling premium, bad for long volatility',
            'normal': 'Balanced environment for directional trades',
            'elevated': 'Options more expensive but bigger moves possible',
            'high': 'Reduce position sizes, widen stops',
            'extreme': 'Consider closing positions or hedging heavily'
        }
        return impacts.get(regime, 'Normal trading conditions')
    
    def _assess_trend_impact(self, trend: str) -> str:
        """Assess impact of trend on options trading"""
        impacts = {
            'strong_uptrend': 'Favor calls, sell put spreads',
            'uptrend': 'Bullish bias, but watch for pullbacks',
            'neutral': 'Range-bound strategies, iron condors',
            'downtrend': 'Favor puts, sell call spreads',
            'strong_downtrend': 'Aggressive put positions, avoid calls'
        }
        return impacts.get(trend, 'No clear directional bias')
    
    def _assess_breadth_impact(self, breadth: str) -> str:
        """Assess impact of market breadth"""
        impacts = {
            'strong_positive': 'Risk-on environment, broad participation',
            'positive': 'Healthy market, most sectors participating',
            'mixed': 'Selective opportunities, focus on strong sectors',
            'negative': 'Risk-off building, be defensive',
            'strong_negative': 'Market weakness, consider hedges'
        }
        return impacts.get(breadth, 'Mixed market conditions')
    
    def _assess_sentiment_impact(self, sentiment: str) -> str:
        """Assess impact of sentiment"""
        impacts = {
            'complacent': 'Potential for volatility spike, buy cheap protection',
            'bullish': 'Momentum trades working, but watch for reversals',
            'neutral': 'Balanced sentiment, trade both directions',
            'bearish': 'Contrarian call opportunities emerging',
            'fearful': 'Extreme fear = potential bottom, brave buyers rewarded'
        }
        return impacts.get(sentiment, 'Normal sentiment conditions')


def example_monitoring():
    """Example of position monitoring"""
    monitor = AdaptiveMarketMonitor(os.getenv('ALPHA_VANTAGE_API_KEY'))
    
    # Update market regime
    regime_update = monitor.update_market_regime()
    print("Market Regime Update:")
    print(f"Current Regime: {regime_update['current_regime']}")
    print(f"Changes: {regime_update['changes']}")
    print(f"Adjustments: {regime_update['trading_adjustments']}")
    
    # Example position to monitor
    position_data = {
        'symbol': 'GOOGL',
        'option_details': {
            'strike': 200,
            'type': 'call',
            'expiration': '2025-07-25',
            'current_price': 0.78,
            'delta': 0.1087,
            'gamma': 0.0121,
            'theta': -0.0668
        },
        'targets': {
            'target_1': {'price': 1.09},
            'target_2': {'price': 1.32}
        },
        'stop_loss': {
            'stop_price': 0.59,
            'stop_type': 'TRAILING_STOP',
            'trail_percentage': 15
        },
        'position_sizing': {
            'contracts': 10
        }
    }
    
    # Monitor position
    monitoring_result = monitor.monitor_position('GOOGL_200C_0725', position_data)
    
    print("\nPosition Monitoring Result:")
    print(f"Alerts: {monitoring_result['alerts']}")
    print(f"Exit Signals: {monitoring_result['exit_signals']}")
    print(f"Adjustments: {monitoring_result['adjustments']}")
    
    # Generate exit signals
    exit_signals = monitor.generate_exit_signals('GOOGL_200C_0725')
    print(f"\nExit Signals: {exit_signals}")


if __name__ == "__main__":
    example_monitoring()
