# Overview

This is an Options Scanner SaaS platform that provides AI-powered options trading analysis and scanning capabilities. The platform identifies explosive options opportunities using multi-factor analysis including Greeks, unusual activity, and market regime detection. It's built as a comprehensive trading system with subscription-based access tiers, real-time scanning, backtesting capabilities, and performance tracking.

The system integrates multiple data sources (Alpha Vantage, Yahoo Finance) to provide comprehensive options analysis, generates intelligent trade plans with data-driven entry/exit strategies, and includes sophisticated risk management and position sizing algorithms.

# User Preferences

Preferred communication style: Simple, everyday language.
Admin account: sheltontraylor@gmail.com (UserRole.ADMIN)

# Admin Features

## Admin Dashboard (/admin)
- User management interface with search and pagination
- Top-up any user's account balance (no payment required)
- Grant free subscriptions to users (Basic/Premium)
- View user activity and subscription status
- Full audit logging of all admin actions

## Admin Capabilities
- **Account Top-up**: Add credits to any user's account ($10-$10,000)
- **Grant Subscriptions**: Give free Basic or Premium subscriptions
- **User Management**: View all users, balances, and subscription status
- **Audit Trail**: All admin actions are logged with timestamp and details
- **Self-Management**: Admin can top up own account and grant self subscriptions

## Payment Method Selection
- **Unified Checkout**: Single payment selection page for all subscription purchases
- **Three Payment Options**: 
  1. Pay with Card (Stripe) - Traditional card payments
  2. Pay with Crypto (USDC) - Stablecoin payments via Stripe
  3. Pay with Account Credits - Instant payment from balance
- **Smart Routing**: Automatically redirects to appropriate payment processor

# System Architecture

## Backend Architecture
- **Framework**: Flask-based REST API with SQLAlchemy ORM
- **Database**: PostgreSQL with Drizzle-compatible schema design
- **Authentication**: JWT-based authentication with bcrypt password hashing
- **API Structure**: RESTful endpoints with role-based access control and usage tracking

## Core Scanning Engine
- **Multi-Source Data Integration**: Primary Alpha Vantage API with Yahoo Finance fallback
- **Scanning Components**:
  - Enhanced options grader with explosive opportunity detection
  - Intelligent trade planner with data-driven entry/exit strategies
  - Real-time market regime detection and position monitoring
  - Performance tracker with historical analysis and adaptive learning
- **Analysis Methods**: Greeks-based analysis, unusual activity detection, technical pattern recognition, earnings play identification

## Subscription Management
- **Payment Processing**: Three payment methods - Stripe Card, USDC Crypto, Account Credits
- **Tier System**: Free, Basic (Weekly: $7, Monthly: $29), Premium (Weekly: $25, Monthly: $99), Enterprise ($299/month)
- **Account Balance**: Credit system with top-up functionality for instant payments
- **Usage Tracking**: API rate limiting, scan quotas, and feature gating based on subscription tier
- **Trial System**: 14-day trials for paid plans with automatic conversion
- **Auto-Renewal**: Automatic subscription renewal with sufficient account balance
- **Tier-Based Scanner Customization**:
  - **Free Tier**: 1 scanner type, locked parameters (max $0.50, 7 days expiration)
  - **Basic Tier**: 3 scanner types, limited customization (max $1.00, 14 days expiration, delta 0.25-0.75)
  - **Premium Tier**: All scanner types, full customization (up to $10, 90 days expiration, any delta range)
  - **Admin Access**: Automatic premium-level features regardless of subscription

## Data Storage and Management
- **Primary Database**: PostgreSQL for user data, subscriptions, API keys, and usage events
- **File Storage**: Local JSON storage for trading plans and scan results in TradingPlans directory
- **Caching Strategy**: In-memory caching for real-time data with 5-minute cache duration
- **Rate Limiting**: 150 requests/minute optimization for Alpha Vantage API limits

## Performance and Monitoring
- **Backtesting Engine**: Historical trade analysis with performance metrics
- **Adaptive Learning**: System learns from historical performance to improve scoring thresholds
- **Real-time Monitoring**: Continuous market regime detection and position tracking
- **Progressive Scanning**: Real-time results saving during long-running scans

## Security and Access Control
- **Multi-tier Authentication**: JWT tokens, API keys, and role-based permissions
- **Usage Enforcement**: Per-tier quotas for scans, API calls, and feature access
- **Server-Side Tier Enforcement**: All scanner parameter limits enforced at API level to prevent bypassing
- **Dynamic UI Restrictions**: Frontend adapts based on user tier with clear upgrade prompts
- **Audit Logging**: Comprehensive tracking of user actions and system events
- **Data Validation**: Input sanitization and type safety throughout the pipeline

# External Dependencies

## Financial Data APIs
- **Alpha Vantage**: Primary options data, technical indicators, and real-time quotes
- **Yahoo Finance (yfinance)**: Backup data source and cross-validation
- **Third-party Rate Limits**: 150 requests/minute for Alpha Vantage subscription plan

## Payment and Subscription Services
- **Payment Methods**: Three payment options - Stripe Card, USDC Crypto (via Stripe), Account Credits
- **Stripe Integration**: Card payments, USDC stablecoin payments, subscription management, webhook handling
- **Account Credits System**: Internal balance system for instant subscription payments
- **Billing Periods**: Weekly ($7 Basic, $25 Premium) and Monthly ($29 Basic, $99 Premium) options
- **Multi-Currency Support**: USD, EUR, GBP, and USDC stablecoin

## Database and Infrastructure
- **PostgreSQL**: Primary database (Supabase-compatible configuration)
- **Database Connection**: psycopg2 for PostgreSQL connectivity with SSL requirements
- **Environment Variables**: Comprehensive configuration for database, API keys, and Stripe settings

## Python Libraries and Frameworks
- **Core Framework**: Flask, SQLAlchemy, Flask-CORS for API development
- **Data Analysis**: pandas, numpy, scipy for quantitative analysis
- **Financial Data**: yfinance for market data, technical analysis libraries
- **Authentication**: PyJWT, bcrypt for security implementation
- **HTTP and Utilities**: requests, python-dotenv for external API integration

## Development and Testing Tools
- **Database Migration**: Flask-Migrate for schema management
- **Testing Infrastructure**: Comprehensive test suites for authentication, Stripe integration, and database operations
- **Frontend Interface**: Simple Flask-based frontend with Tailwind CSS and Stripe.js integration