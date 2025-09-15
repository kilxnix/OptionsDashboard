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
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-3">Free</h3>
                    <p class="text-3xl font-bold mb-4">$0<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2">
                        <li>✓ 5 scans/day</li>
                        <li>✓ Basic scanner</li>
                        <li>✓ Community support</li>
                    </ul>
                </div>
                <div class="bg-purple-600 text-white p-6 rounded-lg shadow-lg transform scale-105 relative">
                    <div class="absolute -top-3 left-1/2 transform -translate-x-1/2">
                        <span class="bg-gradient-to-r from-yellow-400 to-orange-400 text-white px-4 py-1 rounded-full text-sm font-bold">Most Popular</span>
                    </div>
                    <h3 class="text-xl font-semibold mb-3 mt-2">Basic</h3>
                    <p class="text-3xl font-bold mb-4">$29<span class="text-sm">/month</span></p>
                    <ul class="space-y-2">
                        <li>✓ 50 scans/day</li>
                        <li>✓ Explosive scanner</li>
                        <li>✓ Technical analysis</li>
                        <li>✓ Email support</li>
                    </ul>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-3">Premium</h3>
                    <p class="text-3xl font-bold mb-4">$99<span class="text-sm text-gray-600">/month</span></p>
                    <ul class="text-gray-600 space-y-2">
                        <li>✓ 500 scans/day</li>
                        <li>✓ All scanners</li>
                        <li>✓ Priority support</li>
                        <li>✓ Advanced features</li>
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
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Account Balance</h3>
                <p class="text-2xl font-bold text-green-600" id="accountBalance">$0.00</p>
                <button onclick="showTopupModal()" class="mt-2 text-sm bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">Add Credits</button>
            </div>
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
    
    <!-- Top-up Modal -->
    <div id="topupModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Add Credits to Your Account</h3>
                <div class="mt-4">
                    <p class="text-sm text-gray-500 mb-4">Select amount to add to your account balance:</p>
                    <div class="grid grid-cols-2 gap-3">
                        <button onclick="selectTopupAmount('small')" class="topup-btn border-2 border-gray-300 p-3 rounded-lg hover:border-green-500 focus:border-green-500 focus:bg-green-50">$10</button>
                        <button onclick="selectTopupAmount('medium')" class="topup-btn border-2 border-gray-300 p-3 rounded-lg hover:border-green-500 focus:border-green-500 focus:bg-green-50">$25</button>
                        <button onclick="selectTopupAmount('large')" class="topup-btn border-2 border-gray-300 p-3 rounded-lg hover:border-green-500 focus:border-green-500 focus:bg-green-50">$50</button>
                        <button onclick="selectTopupAmount('xlarge')" class="topup-btn border-2 border-gray-300 p-3 rounded-lg hover:border-green-500 focus:border-green-500 focus:bg-green-50">$100</button>
                    </div>
                    <div class="mt-4">
                        <label class="block text-sm font-medium text-gray-700">Custom Amount ($5 - $1000)</label>
                        <input type="number" id="customAmount" min="5" max="1000" step="1" placeholder="Enter amount" 
                               class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500"
                               onchange="selectTopupAmount('custom')">
                    </div>
                </div>
                <div class="flex justify-end mt-6 space-x-3">
                    <button onclick="closeTopupModal()" class="px-4 py-2 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400">Cancel</button>
                    <button onclick="processTopup()" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Add Credits</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedTopupAmount = null;
        
        async function loadDashboard() {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }

            // Load user info
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': 'Bearer ' + token
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                document.getElementById('currentPlan').textContent = data.subscription?.plan || 'Free';
                document.getElementById('dailyLimit').textContent = data.subscription?.quotas?.scans_per_day || '5';
            } else {
                window.location.href = '/login';
            }
            
            // Load account balance
            const balanceResponse = await fetch('/api/account/balance', {
                headers: {
                    'Authorization': 'Bearer ' + token
                }
            });
            
            if (balanceResponse.ok) {
                const balanceData = await balanceResponse.json();
                document.getElementById('accountBalance').textContent = `$${balanceData.balance.toFixed(2)}`;
            }
        }

        function showTopupModal() {
            document.getElementById('topupModal').classList.remove('hidden');
        }
        
        function closeTopupModal() {
            document.getElementById('topupModal').classList.add('hidden');
            selectedTopupAmount = null;
            document.querySelectorAll('.topup-btn').forEach(btn => {
                btn.classList.remove('border-green-500', 'bg-green-50');
            });
        }
        
        function selectTopupAmount(amount) {
            selectedTopupAmount = amount;
            document.querySelectorAll('.topup-btn').forEach(btn => {
                btn.classList.remove('border-green-500', 'bg-green-50');
            });
            if (amount !== 'custom') {
                event.target.classList.add('border-green-500', 'bg-green-50');
            }
        }
        
        async function processTopup() {
            const token = localStorage.getItem('token');
            if (!token || !selectedTopupAmount) {
                alert('Please select an amount');
                return;
            }
            
            let requestData = { amount: selectedTopupAmount };
            if (selectedTopupAmount === 'custom') {
                const customValue = parseFloat(document.getElementById('customAmount').value);
                if (customValue < 5 || customValue > 1000) {
                    alert('Please enter an amount between $5 and $1000');
                    return;
                }
                requestData.custom_amount = customValue;
            }
            
            const response = await fetch('/api/account/topup', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (response.ok) {
                const data = await response.json();
                // Redirect to Stripe checkout
                window.location.href = data.checkout_url;
            } else {
                alert('Failed to create top-up session');
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
            html += '<th class="text-left p-2">Expiry</th>';
            html += '<th class="text-left p-2">Entry Price</th>';
            html += '<th class="text-left p-2">Target</th>';
            html += '<th class="text-left p-2">Score</th>';
            html += '</tr></thead><tbody>';
            
            // Check for both possible field names
            const opportunities = data.final_opportunities || data.opportunities || [];
            
            if (opportunities && opportunities.length > 0) {
                opportunities.slice(0, 20).forEach(opp => {
                    const plan = opp.trade_plan || {};
                    html += '<tr class="border-b hover:bg-gray-50">';
                    html += '<td class="p-2 font-semibold">' + (opp.symbol || '-') + '</td>';
                    html += '<td class="p-2">$' + (plan.strike || '-') + '</td>';
                    html += '<td class="p-2">' + (plan.option_type || '-').toUpperCase() + '</td>';
                    html += '<td class="p-2">' + (plan.expiration ? plan.expiration.split(' ')[0] : '-') + '</td>';
                    html += '<td class="p-2">$' + (plan.entry_price || '-') + '</td>';
                    html += '<td class="p-2">$' + (plan.initial_target || '-') + '</td>';
                    html += '<td class="p-2">' + (opp.combined_score || opp.total_score || '-') + '</td>';
                    html += '</tr>';
                });
            } else {
                html += '<tr><td colspan="7" class="p-4 text-center text-gray-500">No opportunities found matching your criteria</td></tr>';
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
    <style>
        .currency-flag {
            width: 20px;
            height: 14px;
            display: inline-block;
            margin-right: 8px;
        }
    </style>
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
        <h1 class="text-4xl font-bold text-center mb-4">Choose Your Plan</h1>
        
        <!-- Currency Selector -->
        <div class="flex justify-center mb-12">
            <div class="bg-white rounded-lg shadow-md p-2 flex items-center space-x-2">
                <label class="text-sm font-medium text-gray-700 px-2">Currency:</label>
                <select id="currencySelector" class="px-4 py-2 border-0 focus:outline-none focus:ring-2 focus:ring-purple-600 rounded-lg cursor-pointer font-medium">
                    <option value="USD">🇺🇸 USD - US Dollar</option>
                    <option value="EUR">🇪🇺 EUR - Euro</option>
                    <option value="GBP">🇬🇧 GBP - British Pound</option>
                    <option value="USDC">₿ USDC - Crypto</option>
                </select>
            </div>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8" id="pricingCards">
            <!-- Pricing cards will be loaded here -->
        </div>
        
        <!-- Payment Methods Notice -->
        <div class="mt-12 text-center">
            <p class="text-gray-600">Accepted payment methods: </p>
            <div class="flex justify-center items-center mt-3 space-x-4">
                <span class="text-gray-500">💳 Credit/Debit Cards</span>
                <span class="text-gray-500">🏦 Bank Transfer</span>
                <span id="cryptoBadge" class="text-gray-500 hidden">₿ Cryptocurrency</span>
            </div>
        </div>
    </div>

    <script>
        const stripe = Stripe('pk_test_51J1234567890'); // Will be replaced with actual key
        
        // Pricing data for each currency
        const pricingData = {
            'USD': {
                symbol: '$',
                plans: [
                    {
                        id: 'free',
                        name: 'Free',
                        price: 0,
                        features: [
                            '5 scans/day',
                            'Basic scanner',
                            'Community support'
                        ]
                    },
                    {
                        id: 'basic_usd',
                        name: 'Basic',
                        price: 29,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_usd',
                        name: 'Premium',
                        price: 99,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ]
            },
            'EUR': {
                symbol: '€',
                plans: [
                    {
                        id: 'free',
                        name: 'Free',
                        price: 0,
                        features: [
                            '5 scans/day',
                            'Basic scanner',
                            'Community support'
                        ]
                    },
                    {
                        id: 'basic_eur',
                        name: 'Basic',
                        price: 27,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_eur',
                        name: 'Premium',
                        price: 92,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ]
            },
            'GBP': {
                symbol: '£',
                plans: [
                    {
                        id: 'free',
                        name: 'Free',
                        price: 0,
                        features: [
                            '5 scans/day',
                            'Basic scanner',
                            'Community support'
                        ]
                    },
                    {
                        id: 'basic_gbp',
                        name: 'Basic',
                        price: 23,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_gbp',
                        name: 'Premium',
                        price: 79,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ]
            },
            'USDC': {
                symbol: '',
                suffix: ' USDC',
                plans: [
                    {
                        id: 'free',
                        name: 'Free',
                        price: 0,
                        features: [
                            '5 scans/day',
                            'Basic scanner',
                            'Community support'
                        ]
                    },
                    {
                        id: 'basic_usdc',
                        name: 'Basic',
                        price: 29,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support',
                            '🔐 Pay with crypto'
                        ]
                    },
                    {
                        id: 'premium_usdc',
                        name: 'Premium',
                        price: 99,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features',
                            '🔐 Pay with crypto'
                        ]
                    }
                ]
            }
        };
        
        let currentCurrency = 'USD';
        
        function loadPricing(currency = 'USD') {
            currentCurrency = currency;
            const data = pricingData[currency];
            const container = document.getElementById('pricingCards');
            const cryptoBadge = document.getElementById('cryptoBadge');
            
            // Show/hide crypto badge
            if (currency === 'USDC') {
                cryptoBadge.classList.remove('hidden');
            } else {
                cryptoBadge.classList.add('hidden');
            }
            
            container.innerHTML = data.plans.map(plan => `
                <div class="bg-white p-6 rounded-lg shadow-lg ${plan.popular ? 'transform scale-105 border-2 border-purple-600 relative' : ''} transition-all duration-300">
                    ${plan.popular ? 
                        '<div class="absolute -top-3 left-1/2 transform -translate-x-1/2"><span class="bg-gradient-to-r from-yellow-400 to-orange-400 text-white px-4 py-1 rounded-full text-sm font-bold">Most Popular</span></div>' : 
                        ''
                    }
                    <h3 class="text-xl font-semibold mb-3 ${plan.popular ? 'mt-2' : ''}">${plan.name}</h3>
                    <p class="text-3xl font-bold mb-4">
                        ${data.symbol}${plan.price}${data.suffix || ''}
                        <span class="text-sm text-gray-600">/month</span>
                    </p>
                    ${currency === 'USDC' && plan.price > 0 ? 
                        '<div class="mb-4"><span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">₿ Pay with Crypto</span></div>' : 
                        ''
                    }
                    <ul class="text-gray-600 space-y-2 mb-6">
                        ${plan.features.map(f => `<li class="flex items-start"><span class="text-green-500 mr-2">✓</span><span>${f}</span></li>`).join('')}
                    </ul>
                    ${plan.price > 0 ? 
                        `<button onclick="subscribe('${plan.id}', '${currency}')" class="w-full ${plan.popular ? 'bg-gradient-to-r from-purple-600 to-purple-700' : 'bg-purple-600'} text-white py-3 rounded-lg hover:shadow-lg transition-all duration-200 font-semibold">
                            ${currency === 'USDC' ? 'Pay with Crypto' : 'Subscribe Now'}
                        </button>` :
                        `<a href="/register" class="block w-full bg-gray-600 text-white py-3 rounded-lg text-center hover:bg-gray-700 transition-all duration-200 font-semibold">
                            Start Free
                        </a>`
                    }
                </div>
            `).join('');
        }
        
        async function subscribe(planId, currency) {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            const paymentType = currency === 'USDC' ? 'crypto' : 'stripe';
            
            const response = await fetch('/api/stripe/create-checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ 
                    plan_id: planId,
                    currency: currency,
                    payment_type: paymentType
                })
            });
            
            const data = await response.json();
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                alert('Error creating checkout session');
            }
        }
        
        // Handle currency change
        document.getElementById('currencySelector').addEventListener('change', (e) => {
            loadPricing(e.target.value);
        });
        
        // Load initial pricing
        loadPricing('USD');
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