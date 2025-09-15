"""
Simple Flask-based frontend for the Options Scanner SaaS
Serves on port 5000 and proxies API calls to backend on port 5001
"""
from flask import Flask, render_template_string, request, jsonify, redirect, session
import requests
import os
from datetime import datetime

frontend_app = Flask(__name__)
frontend_app.secret_key = os.urandom(24)

# Backend API URL
BACKEND_URL = "http://localhost:5001"

# HTML Template for the SaaS frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Scanner Pro - AI-Powered Options Trading</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.stripe.com/v3/"></script>
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .card-hover:hover {
            transform: translateY(-5px);
            transition: all 0.3s ease;
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-xl font-bold text-purple-600">Options Scanner Pro</span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/" class="text-gray-700 hover:text-purple-600">Home</a>
                    <a href="/pricing" class="text-gray-700 hover:text-purple-600">Pricing</a>
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/scanner" class="text-gray-700 hover:text-purple-600">Scanner</a>
                    <a href="/login" class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700">Login</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <div class="gradient-bg text-white py-20">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <h1 class="text-5xl font-bold mb-4">AI-Powered Options Trading Scanner</h1>
            <p class="text-xl mb-8">Discover explosive options opportunities with advanced algorithms and real-time analysis</p>
            <div class="space-x-4">
                <a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100">Start Free Trial</a>
                <a href="/pricing" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600">View Pricing</a>
            </div>
        </div>
    </div>

    <!-- Features Section -->
    <div class="py-16">
        <div class="max-w-7xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Powerful Features</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">🚀 Explosive Scanner</h3>
                    <p class="text-gray-600">Advanced algorithms identify high-probability explosive moves before they happen</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">📊 Multi-Timeframe Analysis</h3>
                    <p class="text-gray-600">Analyze options across multiple timeframes for optimal entry and exit points</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">🎯 Gamma Squeeze Detection</h3>
                    <p class="text-gray-600">Identify potential gamma squeezes and unusual options activity in real-time</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">💰 Earnings Play Scanner</h3>
                    <p class="text-gray-600">Find the best options plays around earnings announcements</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">📈 Performance Tracking</h3>
                    <p class="text-gray-600">Track your scanner picks and measure performance over time</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg card-hover">
                    <h3 class="text-xl font-semibold mb-3">🔔 Real-Time Alerts</h3>
                    <p class="text-gray-600">Get instant notifications when high-probability setups are detected</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Pricing Preview -->
    <div class="bg-gray-100 py-16">
        <div class="max-w-7xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Simple, Transparent Pricing</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-3">Free</h3>
                    <p class="text-3xl font-bold mb-4">$0<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2">
                        <li>✓ Basic Scanner</li>
                        <li>✓ 10 scans/day</li>
                        <li>✓ Community support</li>
                    </ul>
                </div>
                <div class="bg-purple-600 text-white p-6 rounded-lg shadow-lg transform scale-105">
                    <h3 class="text-xl font-semibold mb-3">Basic</h3>
                    <p class="text-3xl font-bold mb-4">$29<span class="text-sm">/month</span></p>
                    <ul class="space-y-2">
                        <li>✓ Explosive Scanner</li>
                        <li>✓ 100 scans/day</li>
                        <li>✓ Email support</li>
                    </ul>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-3">Premium</h3>
                    <p class="text-3xl font-bold mb-4">$99<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2">
                        <li>✓ All Scanners</li>
                        <li>✓ 500 scans/day</li>
                        <li>✓ Priority support</li>
                    </ul>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-3">Enterprise</h3>
                    <p class="text-3xl font-bold mb-4">$299<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2">
                        <li>✓ Unlimited everything</li>
                        <li>✓ API access</li>
                        <li>✓ Dedicated support</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-8">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p>&copy; 2025 Options Scanner Pro. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen flex items-center justify-center">
        <div class="bg-white p-8 rounded-lg shadow-lg w-96">
            <h2 class="text-2xl font-bold mb-6 text-center">Login to Your Account</h2>
            <form id="loginForm">
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Email</label>
                    <input type="email" id="email" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-purple-600" required>
                </div>
                <div class="mb-6">
                    <label class="block text-gray-700 mb-2">Password</label>
                    <input type="password" id="password" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-purple-600" required>
                </div>
                <button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700">Login</button>
            </form>
            <p class="mt-4 text-center text-gray-600">
                Don't have an account? <a href="/register" class="text-purple-600 hover:underline">Register</a>
            </p>
        </div>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('email').value,
                    password: document.getElementById('password').value
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Login response:', data);
                
                // Check for token in different possible locations
                const token = data.access_token || data.token || (data.tokens && data.tokens.access_token);
                
                if (token) {
                    localStorage.setItem('token', token);
                    alert('Login successful! Redirecting to dashboard...');
                    window.location.href = '/dashboard';
                } else {
                    alert('Login successful but no token received. Please try again.');
                    console.error('No token found in response:', data);
                }
            } else {
                const error = await response.text();
                alert('Login failed: ' + error);
            }
        });
    </script>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen flex items-center justify-center">
        <div class="bg-white p-8 rounded-lg shadow-lg w-96">
            <h2 class="text-2xl font-bold mb-6 text-center">Create Your Account</h2>
            <form id="registerForm">
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Email</label>
                    <input type="email" id="email" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-purple-600" required>
                </div>
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Password</label>
                    <input type="password" id="password" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-purple-600" required>
                </div>
                <div class="mb-6">
                    <label class="block text-gray-700 mb-2">Confirm Password</label>
                    <input type="password" id="confirmPassword" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-purple-600" required>
                </div>
                <button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700">Register</button>
            </form>
            <p class="mt-4 text-center text-gray-600">
                Already have an account? <a href="/login" class="text-purple-600 hover:underline">Login</a>
            </p>
        </div>
    </div>
    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (password !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('email').value,
                    password: password
                })
            });
            const data = await response.json();
            if (data.message === 'User created successfully') {
                alert('Registration successful! Please login.');
                window.location.href = '/login';
            } else {
                alert(data.message || 'Registration failed');
            }
        });
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-xl font-bold text-purple-600">Options Scanner Pro</span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/scanner" class="text-gray-700 hover:text-purple-600">Scanner</a>
                    <button onclick="logout()" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Logout</button>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-8">Your Dashboard</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Current Plan</h3>
                <p class="text-2xl font-bold text-purple-600" id="currentPlan">Loading...</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Scans Today</h3>
                <p class="text-2xl font-bold" id="scansToday">0</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Daily Limit</h3>
                <p class="text-2xl font-bold" id="dailyLimit">Loading...</p>
            </div>
        </div>

        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-xl font-semibold mb-4">Quick Actions</h3>
            <div class="space-x-4">
                <a href="/scanner" class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">Launch Scanner</a>
                <button onclick="upgradeplan()" class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">Upgrade Plan</button>
            </div>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }

            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': 'Bearer ' + token
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                document.getElementById('currentPlan').textContent = data.subscription?.plan_name || 'Free';
                document.getElementById('dailyLimit').textContent = data.subscription?.daily_scans_limit || '10';
            } else {
                window.location.href = '/login';
            }
        }

        function logout() {
            localStorage.removeItem('token');
            window.location.href = '/';
        }

        function upgradeplan() {
            window.location.href = '/pricing';
        }

        loadDashboard();
    </script>
</body>
</html>
"""

SCANNER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scanner - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-xl font-bold text-purple-600">Options Scanner Pro</span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/scanner" class="text-purple-600 font-semibold">Scanner</a>
                    <button onclick="logout()" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Logout</button>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-8">Options Scanner</h1>
        
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <h3 class="text-xl font-semibold mb-4">Scanner Settings</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                    <label class="block text-sm font-medium mb-1">Scanner Type</label>
                    <select id="scanType" class="w-full px-3 py-2 border rounded-lg">
                        <option value="scan">Basic Scan</option>
                        <option value="explosive-scan">Explosive Scan</option>
                        <option value="explosive-earnings-combo">Earnings Combo</option>
                        <option value="jpm-explosion-hunter">JPM Hunter</option>
                        <option value="gamma-squeeze-detector">Gamma Squeeze</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Max Price</label>
                    <input type="number" id="maxPrice" value="5.00" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Min Delta</label>
                    <input type="number" id="minDelta" value="0.20" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1">Max Delta</label>
                    <input type="number" id="maxDelta" value="0.40" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
            </div>
            <button onclick="runScan()" class="mt-4 bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
                Run Scan
            </button>
        </div>

        <div id="results" class="bg-white p-6 rounded-lg shadow hidden">
            <h3 class="text-xl font-semibold mb-4">Scan Results</h3>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        async function runScan() {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }

            const scanType = document.getElementById('scanType').value;
            const params = new URLSearchParams({
                max_price: document.getElementById('maxPrice').value,
                min_delta: document.getElementById('minDelta').value,
                max_delta: document.getElementById('maxDelta').value
            });

            document.getElementById('results').classList.remove('hidden');
            document.getElementById('resultsContent').innerHTML = '<p>Scanning... This may take a few moments.</p>';

            try {
                const response = await fetch(`/${scanType}?${params}`, {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayResults(data);
                } else {
                    document.getElementById('resultsContent').innerHTML = 
                        '<p class="text-red-600">Error: ' + (data.message || 'Scan failed') + '</p>';
                }
            } catch (error) {
                document.getElementById('resultsContent').innerHTML = 
                    '<p class="text-red-600">Error: ' + error.message + '</p>';
            }
        }

        function displayResults(data) {
            let html = '<div class="overflow-x-auto"><table class="min-w-full">';
            html += '<thead><tr class="border-b">';
            html += '<th class="text-left p-2">Symbol</th>';
            html += '<th class="text-left p-2">Strike</th>';
            html += '<th class="text-left p-2">Type</th>';
            html += '<th class="text-left p-2">Price</th>';
            html += '<th class="text-left p-2">Score</th>';
            html += '</tr></thead><tbody>';
            
            if (data.opportunities) {
                Object.entries(data.opportunities).slice(0, 20).forEach(([symbol, opp]) => {
                    const best = opp.best_opportunity || {};
                    html += '<tr class="border-b hover:bg-gray-50">';
                    html += '<td class="p-2 font-semibold">' + symbol + '</td>';
                    html += '<td class="p-2">' + (best.strike || '-') + '</td>';
                    html += '<td class="p-2">' + (best.type || '-') + '</td>';
                    html += '<td class="p-2">$' + (best.mark || '-') + '</td>';
                    html += '<td class="p-2">' + (best.total_score || '-') + '</td>';
                    html += '</tr>';
                });
            }
            
            html += '</tbody></table></div>';
            document.getElementById('resultsContent').innerHTML = html;
        }

        function logout() {
            localStorage.removeItem('token');
            window.location.href = '/';
        }
    </script>
</body>
</html>
"""

PRICING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pricing - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.stripe.com/v3/"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-xl font-bold text-purple-600">Options Scanner Pro</span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/" class="text-gray-700 hover:text-purple-600">Home</a>
                    <a href="/pricing" class="text-purple-600 font-semibold">Pricing</a>
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/login" class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700">Login</a>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-16">
        <h1 class="text-4xl font-bold text-center mb-12">Choose Your Plan</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8" id="pricingCards">
            <!-- Pricing cards will be loaded here -->
        </div>
    </div>

    <script>
        const stripe = Stripe('pk_test_51J1234567890'); // Will be replaced with actual key
        
        async function loadPricing() {
            const response = await fetch('/api/stripe/prices');
            const plans = await response.json();
            
            const container = document.getElementById('pricingCards');
            container.innerHTML = plans.map(plan => `
                <div class="bg-white p-6 rounded-lg shadow-lg ${plan.name === 'Basic' ? 'transform scale-105 border-2 border-purple-600' : ''}">
                    <h3 class="text-xl font-semibold mb-3">${plan.name}</h3>
                    <p class="text-3xl font-bold mb-4">$${plan.price_monthly}<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2 mb-6">
                        ${plan.features.map(f => `<li>✓ ${f}</li>`).join('')}
                    </ul>
                    ${plan.price_monthly > 0 ? 
                        `<button onclick="subscribe('${plan.id}')" class="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700">
                            Subscribe
                        </button>` :
                        `<a href="/register" class="block w-full bg-gray-600 text-white py-2 rounded-lg text-center hover:bg-gray-700">
                            Start Free
                        </a>`
                    }
                </div>
            `).join('');
        }
        
        async function subscribe(planId) {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            const response = await fetch('/api/stripe/create-checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ plan_id: planId })
            });
            
            const data = await response.json();
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                alert('Error creating checkout session');
            }
        }
        
        loadPricing();
    </script>
</body>
</html>
"""

@frontend_app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@frontend_app.route('/login')
def login():
    return render_template_string(LOGIN_TEMPLATE)

@frontend_app.route('/register')
def register():
    return render_template_string(REGISTER_TEMPLATE)

@frontend_app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)

@frontend_app.route('/scanner')
def scanner():
    return render_template_string(SCANNER_TEMPLATE)

@frontend_app.route('/pricing')
def pricing():
    return render_template_string(PRICING_TEMPLATE)

# Proxy all API calls to backend
@frontend_app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(path):
    url = f"{BACKEND_URL}/api/{path}"
    headers = dict(request.headers)
    headers.pop('Host', None)
    
    response = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        json=request.get_json() if request.is_json else None,
        params=request.args
    )
    
    return response.content, response.status_code, dict(response.headers)

# Proxy scanner endpoints
@frontend_app.route('/<path:scanner>', methods=['GET', 'POST'])
def proxy_scanner(scanner):
    if scanner in ['scan', 'explosive-scan', 'explosive-earnings-combo', 'jpm-explosion-hunter', 'gamma-squeeze-detector']:
        url = f"{BACKEND_URL}/{scanner}"
        headers = dict(request.headers)
        headers.pop('Host', None)
        
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            json=request.get_json() if request.is_json else None,
            params=request.args
        )
        
        return response.content, response.status_code, dict(response.headers)
    return "Not Found", 404

if __name__ == '__main__':
    print("Starting Options Scanner Pro Frontend on port 5000...")
    print("Backend API expected on port 5001")
    print("Visit http://localhost:5000 to access the application")
    frontend_app.run(host='0.0.0.0', port=5000, debug=True)