# intelligent_trade_planner.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import os

class IntelligentTradePlanner:
    """
    Generates data-driven trading plans based on comprehensive analysis
    No more arbitrary plans - every decision is backed by data
    """

    def __init__(self, alpha_vantage_key: str):
        self.av_key = alpha_vantage_key

        # Risk management parameters
        self.risk_params = {
            'max_risk_per_trade': 0.02,  # 2% of capital
            'position_sizing_method': 'kelly',  # or 'fixed', 'volatility_based'
            'max_contracts': 20,
            'min_reward_risk': 2.0  # Minimum 2:1 reward/risk
        }

        # Entry confirmation requirements
        self.entry_requirements = {
            'technical_confirmation': True,
            'volume_confirmation': True,
            'spread_improvement': True,
            'time_of_day_filter': True
        }

    def generate_intelligent_plan(self, 
                                option_data: Dict, 
                                score_analysis: Dict,
                                market_data: Dict,
                                account_size: float = 25000) -> Dict:
        """
        Generate a comprehensive, data-driven trading plan
        """
        # Extract key data
        symbol = option_data['symbol']
        current_price = market_data.get('current_price', 100)
        option_price = option_data['mark']

        # 1. Calculate position sizing based on Kelly Criterion or volatility
        position_size = self._calculate_position_size(
            option_data, score_analysis, market_data, account_size
        )

        # 2. Determine entry strategy and triggers
        entry_plan = self._generate_entry_plan(
            option_data, score_analysis, market_data
        )

        # 3. Calculate profit targets based on Greeks and technicals
        targets = self._calculate_profit_targets(
            option_data, score_analysis, market_data
        )

        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(option_data, market_data, score_analysis)

        # 5. Generate exit strategy
        exit_strategy = self._generate_exit_strategy(
            option_data, score_analysis, targets, stop_loss
        )

        # 6. Risk/reward analysis
        risk_reward = self._analyze_risk_reward(
            option_price, targets, stop_loss, position_size
        )

        # 7. Generate execution notes
        execution_notes = self._generate_execution_notes(
            option_data, score_analysis, market_data
        )

        # Compile the complete plan
        trade_plan = {
            'symbol': symbol,
            'option_details': {
                'strike': option_data['strike'],
                'type': option_data['type'],
                'expiration': option_data['expiration'],
                'current_price': option_price,
                'delta': option_data['delta'],
                'gamma': option_data['gamma'],
                'theta': option_data['theta'],
                'iv': option_data['implied_volatility']
            },
            'scoring': {
                'total_score': score_analysis['total_score'],
                'confidence': score_analysis['confidence'],
                'risk_level': score_analysis['risk_level']
            },
            'position_sizing': position_size,
            'entry_plan': entry_plan,
            'targets': targets,
            'stop_loss': stop_loss,
            'exit_strategy': exit_strategy,
            'risk_reward': risk_reward,
            'execution_notes': execution_notes,
            'plan_generated': datetime.now().isoformat(),
            'plan_validity': self._calculate_plan_validity(option_data)
        }

        # Format as human-readable text
        formatted_plan = self._format_trading_plan(trade_plan)
        trade_plan['formatted_text'] = formatted_plan

        return trade_plan

    def _calculate_position_size(self, option_data: Dict, score_analysis: Dict, 
                               market_data: Dict, account_size: float) -> Dict:
        """
        Calculate position size using Kelly Criterion or volatility-based sizing
        """
        option_price = option_data['mark']
        confidence = score_analysis['confidence'] / 100  # Convert to decimal

        # Get win rate from historical data or use confidence as proxy
        win_rate = max(0.35, min(0.65, confidence))  # Clamp between 35-65%

        # Average win/loss from targets and stops
        avg_win = 0.40  # 40% target
        avg_loss = 0.25  # 25% stop

        # Kelly Criterion: f = (bp - q) / b
        # where b = odds, p = win probability, q = loss probability
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25% of capital

        # Adjust for confidence and risk level
        if score_analysis['risk_level'] == 'HIGH':
            kelly_fraction *= 0.5
        elif score_analysis['risk_level'] == 'MEDIUM':
            kelly_fraction *= 0.75

        # Calculate contracts
        risk_amount = account_size * self.risk_params['max_risk_per_trade']
        position_value = account_size * kelly_fraction

        contracts = int(position_value / (option_price * 100))
        contracts = max(1, min(contracts, self.risk_params['max_contracts']))

        # Volatility adjustment
        if market_data.get('volatility_30d', 30) > 50:
            contracts = max(1, int(contracts * 0.7))  # Reduce in high volatility

        return {
            'contracts': contracts,
            'method': 'kelly_criterion',
            'kelly_fraction': round(kelly_fraction * 100, 1),
            'position_value': contracts * option_price * 100,
            'risk_amount': risk_amount,
            'percentage_of_capital': round((contracts * option_price * 100) / account_size * 100, 1)
        }

    def _generate_entry_plan(self, option_data: Dict, score_analysis: Dict, 
                           market_data: Dict) -> Dict:
        """
        Generate specific entry triggers based on technical and market conditions
        """
        current_price = market_data.get('current_price', 100)
        option_price = option_data['mark']

        entry_triggers = []

        # 1. Price action triggers
        technical_indicators = self._fetch_current_technicals(option_data['symbol'])

        if technical_indicators:
            # RSI trigger
            if technical_indicators['rsi'] < 40:
                entry_triggers.append({
                    'type': 'RSI_OVERSOLD_BOUNCE',
                    'condition': f"RSI crosses above 40 (currently {technical_indicators['rsi']:.1f})",
                    'priority': 'HIGH'
                })

            # MACD trigger
            if technical_indicators['macd_histogram'] < 0:
                entry_triggers.append({
                    'type': 'MACD_BULLISH_CROSS',
                    'condition': "MACD histogram turns positive",
                    'priority': 'MEDIUM'
                })

            # Moving average trigger
            if current_price < technical_indicators.get('sma_20', current_price * 1.02):
                entry_triggers.append({
                    'type': 'MA_BREAKOUT',
                    'condition': f"Price breaks above 20-SMA at ${technical_indicators['sma_20']:.2f}",
                    'priority': 'HIGH'
                })

        # 2. Volume triggers
        if score_analysis['components']['unusual_activity_score'] >= 15:
            entry_triggers.append({
                'type': 'VOLUME_SURGE',
                'condition': "Maintain 2x average volume for 30 minutes",
                'priority': 'HIGH'
            })

        # 3. Greeks-based triggers
        if option_data['delta'] < 0.20:
            entry_triggers.append({
                'type': 'DELTA_INCREASE',
                'condition': f"Delta rises above {option_data['delta'] * 1.2:.3f}",
                'priority': 'MEDIUM'
            })

        # 4. Time-based triggers
        entry_triggers.append({
            'type': 'TIME_WINDOW',
            'condition': "Enter between 10:00 AM - 3:00 PM ET (avoid first/last hour)",
            'priority': 'LOW'
        })

        # 5. Spread improvement trigger
        bid_ask_spread = (option_data['ask'] - option_data['bid']) / option_data['ask']
        if bid_ask_spread > 0.10:
            entry_triggers.append({
                'type': 'SPREAD_IMPROVEMENT',
                'condition': f"Bid-ask spread narrows below 10% (currently {bid_ask_spread*100:.1f}%)",
                'priority': 'MEDIUM'
            })

        # Determine entry price range
        entry_range = {
            'ideal_entry': option_price * 0.98,  # 2% below current
            'max_entry': option_price * 1.02,    # 2% above current
            'current_mark': option_price
        }

        # Confirmation requirements
        min_confirmations = 2 if score_analysis['confidence'] >= 70 else 3

        return {
            'entry_triggers': entry_triggers,
            'entry_range': entry_range,
            'confirmation_required': min_confirmations,
            'entry_method': 'LIMIT_ORDER',
            'urgency': self._calculate_entry_urgency(option_data, score_analysis)
        }

    def _calculate_profit_targets(self, option_data: Dict, score_analysis: Dict, 
                                market_data: Dict) -> Dict:
        """
        Calculate multiple profit targets based on technical levels and Greeks
        """
        option_price = option_data['mark']
        strike = option_data['strike']
        current_stock_price = market_data.get('current_price', 100)

        targets = {
            'target_1': {},
            'target_2': {},
            'target_3': {}
        }

        # Base targets on score confidence and Greeks
        if score_analysis['confidence'] >= 80:
            # High confidence = aggressive targets
            base_multipliers = [1.25, 1.60, 2.20]
        elif score_analysis['confidence'] >= 60:
            # Medium confidence = balanced targets  
            base_multipliers = [1.20, 1.45, 1.80]
        else:
            # Lower confidence = conservative targets
            base_multipliers = [1.15, 1.35, 1.60]

        # Adjust for gamma (explosive potential)
        gamma_boost = 1.0
        if option_data['gamma'] >= 0.02:
            gamma_boost = 1.15
        elif option_data['gamma'] >= 0.01:
            gamma_boost = 1.08

        # Calculate targets
        for i, (target_key, multiplier) in enumerate(zip(targets.keys(), base_multipliers)):
            base_target = option_price * multiplier * gamma_boost

            targets[target_key] = {
                'price': round(base_target, 2),
                'percentage': round((base_target / option_price - 1) * 100, 1),
                'stock_price': strike * (1 + 0.02 * (i + 1)),  # Rough estimate
                'probability': self._estimate_target_probability(i, score_analysis),
                'typical_time': f"{(i+1) * 2}-{(i+1) * 3} days"
            }

        # Add stretch target for home runs
        if score_analysis['confidence'] >= 75 and option_data['gamma'] >= 0.015:
            targets['moon_target'] = {
                'price': round(option_price * 3.5, 2),
                'percentage': 250,
                'stock_price': strike * 1.08,
                'probability': 15,
                'typical_time': "5-10 days",
                'note': "Low probability, high reward target"
            }

        return targets

    def _calculate_stop_loss(self, option_data: Dict, market_data: Dict, score_analysis: Dict = None) -> Dict:
        """
        Calculate intelligent stop loss based on support, volatility, and risk/reward
        """
        option_price = option_data['mark']

        # Base stop on volatility
        volatility = market_data.get('volatility_30d', 30) / 100
        volatility_stop = option_price * (1 - volatility * 0.5)  # Half daily volatility

        # Time-based stop (theta consideration)
        theta_stop = option_price - (abs(option_data['theta']) * 3)  # 3 days of decay

        # Choose most appropriate stop
        stop_price = max(volatility_stop, theta_stop, option_price * 0.65)

        # Ensure minimum risk/reward
        target_1_price = targets['target_1']['price']
        max_stop_for_rr = option_price - ((target_1_price - option_price) / self.risk_params['min_reward_risk'])
        stop_price = max(stop_price, max_stop_for_rr)

        return {
            'stop_price': round(stop_price, 2),
            'stop_percentage': round((stop_price / option_price - 1) * 100, 1),
            'stop_type': 'TRAILING_STOP',  # Convert to trailing after 10% profit
            'trail_trigger': round(option_price * 1.10, 2),
            'trail_percentage': 15,  # Trail by 15%
            'time_stop': score_analysis['holding_period']['maximum_days'],
            'theta_stop': f"Exit if theta exceeds ${abs(option_data['theta'] * 2):.2f}/day"
        }

    def _generate_exit_strategy(self, option_data: Dict, score_analysis: Dict,
                              targets: Dict, stop_loss: Dict) -> Dict:
        """
        Generate comprehensive exit strategy with multiple scenarios
        """
        holding_period = score_analysis['holding_period']

        exit_rules = {
            'profit_taking': {
                'target_1': {
                    'action': f"Sell 40% at ${targets['target_1']['price']:.2f}",
                    'reasoning': "Lock in base profits"
                },
                'target_2': {
                    'action': f"Sell 40% at ${targets['target_2']['price']:.2f}",
                    'reasoning': "Secure substantial gains"
                },
                'target_3': {
                    'action': f"Sell final 20% at ${targets['target_3']['price']:.2f} or trail",
                    'reasoning': "Let winners run with trailing stop"
                }
            },
            'defensive_exits': {
                'stop_loss': {
                    'trigger': f"Price hits ${stop_loss['stop_price']:.2f}",
                    'action': "Exit full position immediately"
                },
                'time_decay': {
                    'trigger': f"After {holding_period['recommended_days']} days if no targets hit",
                    'action': "Exit 50%, trail remainder"
                },
                'theta_acceleration': {
                    'trigger': stop_loss['theta_stop'],
                    'action': "Exit full position"
                },
                'delta_deterioration': {
                    'trigger': f"Delta drops below {holding_period['exit_triggers']['delta_limit']:.3f}",
                    'action': "Exit full position"
                }
            },
            'management_rules': {
                'morning_check': "Review position 30 min after open",
                'alerts': [
                    "Set price alerts at all targets and stop",
                    "Set Greeks alerts for theta/delta limits",
                    "Set unusual activity alerts"
                ],
                'adjustment_options': "Consider rolling up/out if up 50%+ with time remaining"
            }
        }

        return exit_rules

    def _analyze_risk_reward(self, entry_price: float, targets: Dict, 
                           stop_loss: Dict, position_size: Dict) -> Dict:
        """
        Comprehensive risk/reward analysis
        """
        contracts = position_size['contracts']
        position_value = entry_price * 100 * contracts

        # Calculate dollar amounts
        stop_price = stop_loss['stop_price']
        risk_amount = (entry_price - stop_price) * 100 * contracts

        reward_amounts = {}
        risk_reward_ratios = {}

        for target_key, target_data in targets.items():
            if 'price' in target_data:
                reward = (target_data['price'] - entry_price) * 100 * contracts
                reward_amounts[target_key] = reward
                risk_reward_ratios[target_key] = reward / risk_amount if risk_amount > 0 else 0

        # Expected value calculation
        expected_value = 0
        for target_key, target_data in targets.items():
            if 'probability' in target_data and target_key in reward_amounts:
                prob = target_data['probability'] / 100
                expected_value += reward_amounts[target_key] * prob

        # Add stop loss probability
        total_target_prob = sum(t.get('probability', 0) for t in targets.values()) / 100
        stop_probability = max(0, 1 - total_target_prob)
        expected_value -= risk_amount * stop_probability

        return {
            'position_value': round(position_value, 2),
            'max_risk': round(risk_amount, 2),
            'risk_percentage': round(risk_amount / position_value * 100, 1),
            'reward_amounts': {k: round(v, 2) for k, v in reward_amounts.items()},
            'risk_reward_ratios': {k: round(v, 2) for k, v in risk_reward_ratios.items()},
            'expected_value': round(expected_value, 2),
            'expected_return': round(expected_value / position_value * 100, 1),
            'breakeven_win_rate': round(risk_amount / (risk_amount + reward_amounts.get('target_1', risk_amount)) * 100, 1)
        }

    def _generate_execution_notes(self, option_data: Dict, score_analysis: Dict,
                                market_data: Dict) -> List[str]:
        """
        Generate specific execution notes and warnings
        """
        notes = []

        # Liquidity warnings
        if option_data['volume'] < 100:
            notes.append("⚠️ LOW VOLUME: Use limit orders only, be patient with fills")

        if option_data['open_interest'] < 500:
            notes.append("⚠️ LOW OPEN INTEREST: May have difficulty exiting, size accordingly")

        # Spread warnings
        spread = (option_data['ask'] - option_data['bid']) / option_data['ask']
        if spread > 0.15:
            notes.append(f"⚠️ WIDE SPREAD ({spread*100:.1f}%): Avoid market orders, work the bid/ask")

        # Greeks warnings
        if abs(option_data['theta']) > 0.15:
            notes.append(f"⚠️ HIGH THETA DECAY: Time is against you, need quick move")

        if option_data['delta'] < 0.15:
            notes.append("📊 LOW DELTA: Requires significant move, true lottery ticket")

        # Timing notes
        days_to_expiry = (pd.to_datetime(option_data['expiration']) - datetime.now()).days
        if days_to_expiry < 7:
            notes.append(f"⏰ NEAR EXPIRATION: Only {days_to_expiry} days left, gamma play")

        # Score-based notes
        if score_analysis['confidence'] >= 80:
            notes.append("✅ HIGH CONFIDENCE SETUP: Can be more aggressive with position")
        elif score_analysis['confidence'] < 50:
            notes.append("⚠️ LOWER CONFIDENCE: Consider smaller position or skip")

        # Technical notes
        if score_analysis['components']['technical_score'] >= 12:
            notes.append("📈 STRONG TECHNICALS: Multiple indicators aligned")

        if score_analysis['components']['unusual_activity_score'] >= 20:
            notes.append("🔥 UNUSUAL OPTIONS ACTIVITY: Smart money may be positioning")

        return notes

    def _format_trading_plan(self, plan: Dict) -> str:
        """
        Format the plan as human-readable text
        """
        pos = plan['position_sizing']
        entry = plan['entry_plan']
        targets = plan['targets']
        stop = plan['stop_loss']
        rr = plan['risk_reward']

        # Determine action strength based on confidence
        confidence = plan['scoring']['confidence']
        if confidence >= 80:
            action = "STRONG BUY"
        elif confidence >= 65:
            action = "BUY"
        else:
            action = "CAUTIOUS BUY"

        formatted = f"""
{'='*60}
{action}: {plan['symbol']} {plan['option_details']['strike']} {plan['option_details']['type'].upper()} exp {plan['option_details']['expiration']}
{'='*60}

📊 SCORING
- Total Score: {plan['scoring']['total_score']:.1f}/100
- Confidence: {confidence}%
- Risk Level: {plan['scoring']['risk_level']}

💰 POSITION SIZING
- Contracts: {pos['contracts']}
- Position Value: ${pos['position_value']:,.2f} ({pos['percentage_of_capital']:.1f}% of capital)
- Method: {pos['method'].replace('_', ' ').title()}
- Kelly Fraction: {pos['kelly_fraction']:.1f}%

🎯 ENTRY PLAN
- Entry Range: ${entry['entry_range']['ideal_entry']:.2f} - ${entry['entry_range']['max_entry']:.2f}
- Current Mark: ${entry['entry_range']['current_mark']:.2f}
- Confirmations Required: {entry['confirmation_required']} of the following:
"""

        # Add entry triggers
        for trigger in entry['entry_triggers'][:4]:  # Top 4 triggers
            formatted += f"  • {trigger['condition']} [{trigger['priority']}]\n"

        formatted += f"\n📈 PROFIT TARGETS\n"
        for i, (target_key, target_data) in enumerate(targets.items()):
            if 'price' in target_data:
                formatted += f"- Target {i+1}: ${target_data['price']:.2f} (+{target_data['percentage']:.1f}%) "
                formatted += f"@ ${target_data['stock_price']:.2f} stock [{target_data['probability']}% prob]\n"

        formatted += f"""
🛑 RISK MANAGEMENT
- Stop Loss: ${stop['stop_price']:.2f} ({stop['stop_percentage']:.1f}%)
- Stop Type: {stop['stop_type'].replace('_', ' ').title()}
- Trail Trigger: ${stop['trail_trigger']:.2f} (+10%)
- Max Hold Time: {stop['time_stop']} days
- Theta Stop: {stop['theta_stop']}

📊 RISK/REWARD ANALYSIS
- Max Risk: ${rr['max_risk']:,.2f}
- Expected Value: ${rr['expected_value']:,.2f} ({rr['expected_return']:.1f}% return)
- Risk/Reward Ratios:
"""

        for target, ratio in rr['risk_reward_ratios'].items():
            formatted += f"  • {target}: {ratio:.2f}:1\n"

        formatted += f"- Breakeven Win Rate: {rr['breakeven_win_rate']:.1f}%\n"

        # Add execution notes
        if plan['execution_notes']:
            formatted += f"\n📝 EXECUTION NOTES\n"
            for note in plan['execution_notes']:
                formatted += f"{note}\n"

        formatted += f"\n⏰ Plan Valid Until: {plan['plan_validity']}\n"
        formatted += f"Generated: {plan['plan_generated']}\n"

        return formatted

    # Helper methods for technical analysis and calculations

    def _fetch_current_technicals(self, symbol: str) -> Dict:
        """Fetch current technical indicators"""
        # Implementation would call Alpha Vantage for real-time data
        # Returning mock data for structure
        return {
            'rsi': 45.5,
            'macd_histogram': -0.15,
            'sma_20': 180.50,
            'sma_50': 175.25,
            'volume_avg': 10000000
        }

    def _estimate_target_probability(self, target_index: int, 
                                   score_analysis: Dict) -> int:
        """Estimate probability of hitting each target"""
        base_probs = [65, 40, 20]  # Base probabilities for targets 1, 2, 3

        # Adjust based on score
        confidence_multiplier = score_analysis['confidence'] / 70

        if target_index < len(base_probs):
            return int(base_probs[target_index] * confidence_multiplier)
        return 10

    def _calculate_entry_urgency(self, option_data: Dict, 
                               score_analysis: Dict) -> str:
        """Determine how urgent entry is"""
        if score_analysis['components']['unusual_activity_score'] >= 20:
            return "HIGH - Enter within 1 hour"
        elif score_analysis['confidence'] >= 75:
            return "MEDIUM - Enter today"
        else:
            return "LOW - Wait for confirmations"

    def _calculate_plan_validity(self, option_data: Dict) -> str:
        """Calculate how long this plan remains valid"""
        # Plans expire at end of day or if significant price movement
        today = datetime.now()
        if today.hour < 16:
            validity = today.replace(hour=16, minute=0, second=0)
        else:
            validity = (today + timedelta(days=1)).replace(hour=9, minute=30, second=0)

        return validity.strftime("%Y-%m-%d %H:%M ET")