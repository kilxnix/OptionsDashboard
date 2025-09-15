"""
Tier-based parameter limits for scanner endpoints
"""
from models import PlanTier

def get_tier_limits(tier):
    """Get parameter limits for a specific tier"""
    tier_limits = {
        PlanTier.FREE: {
            'max_price': 0.50,
            'min_delta': 0.30,
            'max_delta': 0.70,
            'days_to_expiry': 7,
            'min_days': 1,
            'max_days': 7,
            'min_volume': 50,
            'min_open_interest': 25,
            'score_threshold': 50,
            'max_results': 5,
            'max_symbols': 50,
            'scanner_types': ['scan']  # Only basic scan
        },
        PlanTier.BASIC: {
            'max_price': 1.00,
            'min_delta': 0.25,
            'max_delta': 0.75,
            'days_to_expiry': 14,
            'min_days': 1,
            'max_days': 14,
            'min_volume': 75,
            'min_open_interest': 40,
            'score_threshold': 45,
            'max_results': 15,
            'max_symbols': 100,
            'scanner_types': ['scan', 'explosive-scan', 'explosive-earnings-combo']
        },
        PlanTier.PREMIUM: {
            'max_price': 10.00,
            'min_delta': 0.0,
            'max_delta': 1.0,
            'days_to_expiry': 90,
            'min_days': 1,
            'max_days': 90,
            'min_volume': 10000,
            'min_open_interest': 10000,
            'score_threshold': 100,
            'max_results': 100,
            'max_symbols': 500,
            'scanner_types': [
                'scan', 'explosive-scan', 'explosive-earnings-combo',
                'jpm-explosion-hunter', 'gamma-squeeze-detector', 'enhanced-scan'
            ]
        }
    }
    
    return tier_limits.get(tier, tier_limits[PlanTier.FREE])


def apply_tier_limits(tier, params):
    """Apply parameter limits based on subscription tier"""
    limits = get_tier_limits(tier)
    applied_limits = []
    adjusted_params = params.copy()
    
    # Apply limits to each parameter
    if 'max_price' in params:
        if params['max_price'] > limits['max_price']:
            adjusted_params['max_price'] = limits['max_price']
            applied_limits.append(f"Max price limited to ${limits['max_price']}")
    
    if 'min_delta' in params:
        if params['min_delta'] < limits['min_delta']:
            adjusted_params['min_delta'] = limits['min_delta']
            applied_limits.append(f"Min delta adjusted to {limits['min_delta']}")
    
    if 'max_delta' in params:
        if params['max_delta'] > limits['max_delta']:
            adjusted_params['max_delta'] = limits['max_delta']
            applied_limits.append(f"Max delta limited to {limits['max_delta']}")
    
    if 'days_to_expiry' in params:
        if params['days_to_expiry'] > limits['days_to_expiry']:
            adjusted_params['days_to_expiry'] = limits['days_to_expiry']
            applied_limits.append(f"Days to expiry limited to {limits['days_to_expiry']}")
    
    if 'max_days' in params:
        if params['max_days'] > limits['max_days']:
            adjusted_params['max_days'] = limits['max_days']
            applied_limits.append(f"Max days limited to {limits['max_days']}")
    
    if 'max_results' in params:
        if params['max_results'] > limits['max_results']:
            adjusted_params['max_results'] = limits['max_results']
            applied_limits.append(f"Results limited to {limits['max_results']}")
    
    if 'max_symbols' in params:
        if params['max_symbols'] > limits['max_symbols']:
            adjusted_params['max_symbols'] = limits['max_symbols']
            applied_limits.append(f"Symbols limited to {limits['max_symbols']}")
    
    # For non-premium tiers, cap advanced parameters
    if tier != PlanTier.PREMIUM:
        if 'min_volume' in params:
            adjusted_params['min_volume'] = min(params['min_volume'], limits['min_volume'])
        
        if 'min_open_interest' in params:
            adjusted_params['min_open_interest'] = min(params['min_open_interest'], limits['min_open_interest'])
        
        if 'score_threshold' in params:
            adjusted_params['score_threshold'] = min(params['score_threshold'], limits['score_threshold'])
    
    return adjusted_params, applied_limits


def is_scanner_allowed(tier, scanner_type):
    """Check if a scanner type is allowed for a given tier"""
    limits = get_tier_limits(tier)
    return scanner_type in limits.get('scanner_types', ['scan'])