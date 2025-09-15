# Stripe Integration Guide for Options Scanner SaaS

## Overview
This document provides a complete guide to the Stripe integration for the Options Scanner SaaS platform. The integration handles subscription management, payment processing, and customer billing.

## Features Implemented

### 1. Subscription Tiers
- **Free Tier**: $0/month - Basic scanning capabilities
- **Basic Plan**: $29/month - Enhanced scanning with explosive move detection
- **Premium Plan**: $99/month - Advanced scanning with all premium features  
- **Enterprise Plan**: $299/month - Unlimited access with priority support

### 2. Core Functionality
- ✅ Stripe product and price creation
- ✅ Checkout session creation for subscriptions
- ✅ Customer portal for subscription management
- ✅ Webhook processing for subscription events
- ✅ Automatic free tier assignment on registration
- ✅ Trial periods (14 days for paid plans)
- ✅ API key management with tier-based limits

## API Endpoints

### Authentication Endpoints
```bash
POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
POST /api/auth/api-keys
DELETE /api/auth/api-keys/{key_id}
```

### Stripe Integration Endpoints
```bash
GET /api/stripe/prices                 # Get available subscription tiers
POST /api/stripe/create-checkout       # Create Stripe checkout session
POST /api/stripe/create-portal         # Create customer portal session
POST /api/stripe/webhook              # Handle Stripe webhooks
GET /api/stripe/subscription          # Get current subscription info
POST /api/stripe/cancel-subscription  # Cancel subscription
POST /api/stripe/init-products        # Initialize Stripe products (Admin only)
```

## Setup Instructions

### 1. Environment Variables
Ensure the following environment variables are set:
```bash
STRIPE_SECRET_KEY=sk_test_...         # Your Stripe secret key
STRIPE_WEBHOOK_SECRET=whsec_...       # Webhook endpoint secret (optional for testing)
DATABASE_URL=postgresql://...         # PostgreSQL connection string
JWT_SECRET_KEY=your-secret-key        # JWT signing key
```

### 2. Initialize Stripe Products
Run the seed script to create Stripe products and prices:
```bash
python seed_stripe.py
```

This will create:
- Stripe products for each tier
- Monthly pricing for each product
- Database records with Stripe IDs

### 3. Configure Webhooks
In your Stripe Dashboard:
1. Go to Developers → Webhooks
2. Add endpoint: `https://your-domain.com/api/stripe/webhook`
3. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET`

### 4. Configure Customer Portal (Optional)
1. Go to https://dashboard.stripe.com/settings/billing/portal
2. Configure portal settings:
   - Enable subscription cancellation
   - Enable plan switching
   - Configure allowed plans
3. Save configuration

## Testing the Integration

### 1. Run Test Suite
```bash
python test_stripe_integration.py
```

This tests:
- Price retrieval
- User registration with free tier
- Subscription information
- Checkout session creation
- Portal session creation
- API key management

### 2. Test with Stripe CLI
```bash
# Install Stripe CLI
# Forward webhooks to local server
stripe listen --forward-to localhost:5000/api/stripe/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
```

### 3. Test Cards
Use these test card numbers:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Requires authentication: `4000 0025 0000 3155`

## Usage Examples

### 1. Register a New User
```python
import requests

response = requests.post('http://localhost:5000/api/auth/register', json={
    'email': 'user@example.com',
    'password': 'SecurePassword123!',
    'first_name': 'John',
    'last_name': 'Doe'
})

data = response.json()
access_token = data['tokens']['access_token']
```

### 2. Create Checkout Session
```python
headers = {'Authorization': f'Bearer {access_token}'}

response = requests.post('http://localhost:5000/api/stripe/create-checkout', 
    headers=headers,
    json={'plan_tier': 'premium'}
)

checkout_url = response.json()['checkout_url']
# Redirect user to checkout_url
```

### 3. Get Subscription Info
```python
headers = {'Authorization': f'Bearer {access_token}'}

response = requests.get('http://localhost:5000/api/stripe/subscription', 
    headers=headers)

subscription = response.json()['subscription']
print(f"Current plan: {subscription['plan']}")
print(f"Status: {subscription['status']}")
```

### 4. Use API Key Authentication
```python
# Create API key
response = requests.post('http://localhost:5000/api/auth/api-keys',
    headers={'Authorization': f'Bearer {access_token}'},
    json={'name': 'Production Key'}
)

api_key = response.json()['api_key']['key']

# Use API key for requests
headers = {'X-API-Key': api_key}
response = requests.get('http://localhost:5000/scan', headers=headers)
```

## Subscription Lifecycle

### User Journey
1. **Registration**: User signs up → Automatically assigned free tier
2. **Upgrade**: User selects plan → Redirected to Stripe checkout
3. **Payment**: User completes payment → Webhook activates subscription
4. **Management**: User accesses portal → Can cancel or change plan
5. **Renewal**: Stripe handles automatic renewal → Webhook updates status

### Webhook Events Handled
- `checkout.session.completed`: Marks checkout as successful
- `customer.subscription.created`: Creates subscription record
- `customer.subscription.updated`: Updates plan or status
- `customer.subscription.deleted`: Marks subscription as canceled
- `invoice.payment_succeeded`: Reactivates past-due subscriptions
- `invoice.payment_failed`: Marks subscription as past-due

## Rate Limiting by Tier

### Free Tier
- 5 scans per day
- 10 API calls per minute
- 1 API key maximum
- Access to: `/scan`

### Basic Plan ($29/month)
- 50 scans per day
- 30 API calls per minute
- 3 API keys maximum
- Access to: `/scan`, `/explosive-scan`

### Premium Plan ($99/month)
- 500 scans per day
- 60 API calls per minute
- 10 API keys maximum
- Access to: `/scan`, `/explosive-scan`, `/jpm-explosion-hunter`

### Enterprise Plan ($299/month)
- Unlimited scans
- Unlimited API calls
- Unlimited API keys
- Access to all endpoints

## Security Considerations

### 1. Webhook Verification
```python
# Webhook signature is verified automatically in stripe_manager.py
event = stripe.Webhook.construct_event(
    payload, signature, STRIPE_WEBHOOK_SECRET
)
```

### 2. API Key Storage
- API keys are hashed using SHA-256 before storage
- Original key is shown only once at creation
- Keys can be revoked but not retrieved

### 3. JWT Authentication
- Access tokens expire after 1 hour
- Refresh tokens expire after 30 days
- Tokens include user role and subscription tier

## Troubleshooting

### Common Issues

1. **Portal Creation Fails**
   - Ensure customer portal is configured in Stripe Dashboard
   - Check that user has a Stripe customer ID

2. **Webhook Not Received**
   - Verify webhook endpoint is accessible
   - Check webhook signing secret is correct
   - Use Stripe CLI to test locally

3. **Subscription Not Updating**
   - Check webhook events in Stripe Dashboard
   - Verify database connection
   - Check application logs for errors

### Debug Commands
```bash
# Check Stripe products
curl http://localhost:5000/api/stripe/prices

# View application logs
tail -f /tmp/logs/OptionsScanner_*.log

# Test webhook manually
stripe trigger checkout.session.completed --add session:customer=cus_xxx
```

## Production Checklist

- [ ] Set production Stripe API keys
- [ ] Configure production webhook endpoint
- [ ] Set webhook signing secret
- [ ] Enable HTTPS for all endpoints
- [ ] Configure customer portal in Stripe
- [ ] Set up monitoring for failed payments
- [ ] Configure email notifications
- [ ] Test subscription upgrade/downgrade flows
- [ ] Verify webhook idempotency
- [ ] Set up database backups

## Support

For issues or questions:
1. Check Stripe Dashboard for webhook logs
2. Review application logs in `/tmp/logs/`
3. Run test suite: `python test_stripe_integration.py`
4. Contact support with error messages and logs

## Updates and Maintenance

### Monthly Tasks
- Review failed payment reports
- Update subscription metrics
- Check for Stripe API updates

### Quarterly Tasks
- Audit subscription statuses
- Review pricing strategy
- Update rate limits if needed

## Conclusion

The Stripe integration provides a complete subscription management system for the Options Scanner SaaS platform. All core functionality is implemented and tested, ready for production use after configuring the production Stripe account and webhook endpoints.