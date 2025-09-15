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
    <style>
        .premium-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 8px;
        }
        .locked-input {
            background-color: #f3f4f6;
            cursor: not-allowed;
            position: relative;
        }
        .tooltip {
            position: relative;
            display: inline-block;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            font-size: 12px;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
        }
        .parameter-group {
            position: relative;
        }
        .lock-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            cursor: pointer;
        }
        .upgrade-prompt {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
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
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/scanner" class="text-purple-600 font-semibold">Scanner</a>
                    <button onclick="logout()" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Logout</button>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold">Options Scanner</h1>
            <div id="tierIndicator" class="px-4 py-2 rounded-lg font-semibold"></div>
        </div>
        
        <!-- Tier Limits Info Box -->
        <div id="tierLimitsBox" class="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-6 hidden">
            <div class="flex items-center">
                <svg class="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                </svg>
                <p id="tierLimitsText" class="text-sm text-yellow-800"></p>
            </div>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <h3 class="text-xl font-semibold mb-4">Scanner Settings</h3>
            
            <!-- Scanner Type Selection -->
            <div class="mb-6">
                <label class="block text-sm font-medium mb-2">
                    Scanner Type
                    <span class="tooltip">
                        <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                        </svg>
                        <span class="tooltiptext">Choose the type of scan to run</span>
                    </span>
                </label>
                <select id="scanType" class="w-full px-3 py-2 border rounded-lg">
                    <!-- Options will be populated based on tier -->
                </select>
            </div>
            
            <!-- Basic Parameters -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="parameter-group">
                    <label class="block text-sm font-medium mb-1">
                        Max Price
                        <span class="tooltip">
                            <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="tooltiptext">Maximum option contract price</span>
                        </span>
                    </label>
                    <input type="number" id="maxPrice" value="5.00" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div class="parameter-group">
                    <label class="block text-sm font-medium mb-1">
                        Min Delta
                        <span class="tooltip">
                            <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="tooltiptext">Minimum delta for option contracts</span>
                        </span>
                    </label>
                    <input type="number" id="minDelta" value="0.20" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div class="parameter-group">
                    <label class="block text-sm font-medium mb-1">
                        Max Delta
                        <span class="tooltip">
                            <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="tooltiptext">Maximum delta for option contracts</span>
                        </span>
                    </label>
                    <input type="number" id="maxDelta" value="0.40" step="0.01" class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div class="parameter-group">
                    <label class="block text-sm font-medium mb-1">
                        Days to Expiry
                        <span class="tooltip">
                            <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="tooltiptext">Maximum days until option expiration</span>
                        </span>
                    </label>
                    <input type="number" id="daysToExpiry" value="7" step="1" class="w-full px-3 py-2 border rounded-lg">
                </div>
            </div>
            
            <!-- Advanced Parameters (Premium Only) -->
            <div id="advancedParams" class="hidden">
                <h4 class="text-lg font-semibold mb-3">
                    Advanced Parameters
                    <span class="premium-badge">PREMIUM</span>
                </h4>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div class="parameter-group">
                        <label class="block text-sm font-medium mb-1">
                            Min Volume
                            <span class="tooltip">
                                <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="tooltiptext">Minimum daily volume for options</span>
                            </span>
                        </label>
                        <input type="number" id="minVolume" value="100" step="10" class="w-full px-3 py-2 border rounded-lg">
                    </div>
                    <div class="parameter-group">
                        <label class="block text-sm font-medium mb-1">
                            Min Open Interest
                            <span class="tooltip">
                                <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="tooltiptext">Minimum open interest for options</span>
                            </span>
                        </label>
                        <input type="number" id="minOpenInterest" value="50" step="10" class="w-full px-3 py-2 border rounded-lg">
                    </div>
                    <div class="parameter-group">
                        <label class="block text-sm font-medium mb-1">
                            Score Threshold
                            <span class="tooltip">
                                <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="tooltiptext">Minimum score for opportunities</span>
                            </span>
                        </label>
                        <input type="number" id="scoreThreshold" value="60" step="5" class="w-full px-3 py-2 border rounded-lg">
                    </div>
                    <div class="parameter-group">
                        <label class="block text-sm font-medium mb-1">
                            Max Results
                            <span class="tooltip">
                                <svg class="inline w-4 h-4 text-gray-400 ml-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="tooltiptext">Maximum number of results to display</span>
                            </span>
                        </label>
                        <input type="number" id="maxResults" value="20" step="5" class="w-full px-3 py-2 border rounded-lg">
                    </div>
                </div>
            </div>
            
            <div class="flex items-center justify-between mt-6">
                <button onclick="runScan()" class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
                    Run Scan
                </button>
                <div id="upgradePrompt" class="hidden">
                    <a href="/pricing" class="upgrade-prompt hover:opacity-90">
                        🚀 Upgrade to Premium for Advanced Features
                    </a>
                </div>
            </div>
        </div>

        <div id="results" class="bg-white p-6 rounded-lg shadow hidden">
            <h3 class="text-xl font-semibold mb-4">Scan Results</h3>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        let userTier = 'free';  // Default to free tier
        let userInfo = {};
        
        // Load user information and configure scanner based on tier
        async function loadUserInfo() {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            try {
                const response = await fetch('/api/auth/me', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    userInfo = data;
                    // Extract tier from the subscription object returned by /api/auth/me
                    if (data.subscription && data.subscription.tier) {
                        userTier = data.subscription.tier.toLowerCase();
                    } else {
                        userTier = 'free';
                    }
                    console.log('User tier detected:', userTier);
                    configureScannerForTier();
                } else if (response.status === 401) {
                    // Authentication failed, redirect to login
                    console.error('Authentication required');
                    window.location.href = '/login';
                } else {
                    console.error('Failed to load user info, status:', response.status);
                    configureScannerForTier();  // Use defaults
                }
            } catch (error) {
                console.error('Error loading user info:', error);
                configureScannerForTier();  // Use defaults
            }
        }
        
        function configureScannerForTier() {
            const scanTypeSelect = document.getElementById('scanType');
            const tierIndicator = document.getElementById('tierIndicator');
            const tierLimitsBox = document.getElementById('tierLimitsBox');
            const tierLimitsText = document.getElementById('tierLimitsText');
            const advancedParams = document.getElementById('advancedParams');
            const upgradePrompt = document.getElementById('upgradePrompt');
            
            // Clear existing options
            scanTypeSelect.innerHTML = '';
            
            // Configure based on tier
            if (userTier === 'premium') {
                // Premium tier - full access
                tierIndicator.textContent = '👑 Premium';
                tierIndicator.className = 'px-4 py-2 rounded-lg font-semibold bg-gradient-to-r from-purple-600 to-pink-600 text-white';
                
                // All scanner types available
                scanTypeSelect.innerHTML = `
                    <option value="scan">Basic Scan</option>
                    <option value="explosive-scan">Explosive Scan</option>
                    <option value="explosive-earnings-combo">Earnings Combo</option>
                    <option value="jpm-explosion-hunter">JPM Hunter</option>
                    <option value="gamma-squeeze-detector">Gamma Squeeze</option>
                    <option value="enhanced-scan">Enhanced Analysis</option>
                `;
                
                // Show advanced parameters
                advancedParams.classList.remove('hidden');
                
                // Enable all inputs
                enableAllInputs();
                
                // Hide upgrade prompt
                upgradePrompt.classList.add('hidden');
                tierLimitsBox.classList.add('hidden');
                
            } else if (userTier === 'basic') {
                // Basic tier - limited access
                tierIndicator.textContent = '⭐ Basic';
                tierIndicator.className = 'px-4 py-2 rounded-lg font-semibold bg-blue-500 text-white';
                
                // Limited scanner types
                scanTypeSelect.innerHTML = `
                    <option value="scan">Basic Scan</option>
                    <option value="explosive-scan">Explosive Scan</option>
                    <option value="explosive-earnings-combo">Earnings Combo</option>
                `;
                
                // Hide advanced parameters
                advancedParams.classList.add('hidden');
                
                // Limit basic inputs
                limitBasicInputs();
                
                // Show upgrade prompt
                upgradePrompt.classList.remove('hidden');
                
                // Show tier limits
                tierLimitsBox.classList.remove('hidden');
                tierLimitsText.textContent = 'Basic Tier: Max price limited to $1.00, Delta range 0.25-0.75, Max 14 days to expiry';
                
            } else {
                // Free tier - minimal access
                tierIndicator.textContent = '🆓 Free';
                tierIndicator.className = 'px-4 py-2 rounded-lg font-semibold bg-gray-500 text-white';
                
                // Only basic scan for free tier
                scanTypeSelect.innerHTML = `
                    <option value="scan">Basic Scan</option>
                    <option value="explosive-scan" disabled>🔒 Explosive Scan (Upgrade Required)</option>
                    <option value="jpm-explosion-hunter" disabled>🔒 JPM Hunter (Premium Only)</option>
                `;
                
                // Hide advanced parameters
                advancedParams.classList.add('hidden');
                
                // Lock most inputs to defaults
                lockFreeInputs();
                
                // Show upgrade prompt
                upgradePrompt.classList.remove('hidden');
                
                // Show tier limits
                tierLimitsBox.classList.remove('hidden');
                tierLimitsText.textContent = 'Free Tier: Max price $0.50, Delta 0.3-0.7, Max 7 days to expiry. Upgrade for full customization!';
            }
        }
        
        function enableAllInputs() {
            const inputs = ['maxPrice', 'minDelta', 'maxDelta', 'daysToExpiry', 'minVolume', 'minOpenInterest', 'scoreThreshold', 'maxResults'];
            inputs.forEach(id => {
                const input = document.getElementById(id);
                if (input) {
                    input.disabled = false;
                    input.classList.remove('locked-input');
                    // Remove any lock overlay
                    const parent = input.parentElement;
                    const overlay = parent.querySelector('.lock-overlay');
                    if (overlay) overlay.remove();
                }
            });
        }
        
        function limitBasicInputs() {
            // Set max values for basic tier
            document.getElementById('maxPrice').max = '1.00';
            document.getElementById('maxPrice').value = Math.min(1.00, parseFloat(document.getElementById('maxPrice').value));
            
            document.getElementById('minDelta').min = '0.25';
            document.getElementById('minDelta').value = Math.max(0.25, parseFloat(document.getElementById('minDelta').value));
            
            document.getElementById('maxDelta').max = '0.75';
            document.getElementById('maxDelta').value = Math.min(0.75, parseFloat(document.getElementById('maxDelta').value));
            
            document.getElementById('daysToExpiry').max = '14';
            document.getElementById('daysToExpiry').value = Math.min(14, parseInt(document.getElementById('daysToExpiry').value));
        }
        
        function lockFreeInputs() {
            // Lock inputs to free tier defaults
            const locks = [
                { id: 'maxPrice', value: '0.50', disabled: true },
                { id: 'minDelta', value: '0.30', disabled: true },
                { id: 'maxDelta', value: '0.70', disabled: true },
                { id: 'daysToExpiry', value: '7', disabled: true }
            ];
            
            locks.forEach(lock => {
                const input = document.getElementById(lock.id);
                if (input) {
                    input.value = lock.value;
                    input.disabled = lock.disabled;
                    if (lock.disabled) {
                        input.classList.add('locked-input');
                        
                        // Add lock overlay for visual feedback
                        const parent = input.parentElement;
                        if (!parent.querySelector('.lock-overlay')) {
                            const overlay = document.createElement('div');
                            overlay.className = 'lock-overlay';
                            overlay.innerHTML = '<span class="text-gray-600 text-xs">🔒 Upgrade to unlock</span>';
                            overlay.onclick = () => window.location.href = '/pricing';
                            parent.appendChild(overlay);
                        }
                    }
                }
            });
        }
        
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
                max_delta: document.getElementById('maxDelta').value,
                days_to_expiry: document.getElementById('daysToExpiry').value
            });
            
            // Add advanced parameters if premium
            if (userTier === 'premium') {
                params.append('min_volume', document.getElementById('minVolume').value);
                params.append('min_open_interest', document.getElementById('minOpenInterest').value);
                params.append('score_threshold', document.getElementById('scoreThreshold').value);
                params.append('max_results', document.getElementById('maxResults').value);
            }

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
                    // Check if parameter limits were applied
                    let resultsHtml = '';
                    if (data.applied_limits && data.applied_limits.length > 0) {
                        resultsHtml = '<div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">' +
                            '<p class="text-sm text-blue-800">📊 Parameters adjusted for ' + userTier.charAt(0).toUpperCase() + userTier.slice(1) + ' tier:<br>' +
                            data.applied_limits.join('<br>') + '</p></div>';
                        document.getElementById('resultsContent').innerHTML = resultsHtml;
                    } else {
                        document.getElementById('resultsContent').innerHTML = '';
                    }
                    displayResults(data);
                } else if (response.status === 403) {
                    // Tier restriction - show upgrade prompt
                    document.getElementById('resultsContent').innerHTML = 
                        '<div class="p-6 bg-yellow-50 border-2 border-yellow-200 rounded-lg">' +
                        '<h3 class="text-lg font-semibold text-yellow-800 mb-2">🔒 Feature Locked</h3>' +
                        '<p class="text-yellow-700 mb-4">' + (data.message || 'This scanner requires a higher tier subscription') + '</p>' +
                        '<p class="text-sm text-yellow-600 mb-4">Your current tier: <strong>' + (data.current_tier || userTier) + '</strong></p>' +
                        '<a href="/pricing" class="inline-block bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg font-semibold hover:opacity-90">Upgrade Now →</a>' +
                        '</div>';
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
            // Log the raw data for debugging
            console.log('Raw scan response:', data);
            
            let html = '<div class="overflow-x-auto"><table class="min-w-full">';
            html += '<thead><tr class="border-b">';
            html += '<th class="text-left p-2">Symbol</th>';
            html += '<th class="text-left p-2">Strike</th>';
            html += '<th class="text-left p-2">Type</th>';
            html += '<th class="text-left p-2">Expiry</th>';
            html += '<th class="text-left p-2">Entry Price</th>';
            html += '<th class="text-left p-2">Target</th>';
            html += '<th class="text-left p-2">Score</th>';
            html += '<th class="text-left p-2">Recommendation</th>';
            html += '</tr></thead><tbody>';
            
            // Convert opportunities dictionary to array if needed
            let opportunities = [];
            
            // Handle different response formats
            if (data.top_picks && Array.isArray(data.top_picks)) {
                // Use top_picks if available (from explosive scan)
                opportunities = data.top_picks;
                console.log(`Using top_picks: ${opportunities.length} items`);
            } else if (data.final_opportunities && Array.isArray(data.final_opportunities)) {
                // Use final_opportunities if available (from explosive-earnings-combo)
                opportunities = data.final_opportunities;
                console.log(`Using final_opportunities: ${opportunities.length} items`);
            } else if (data.opportunities) {
                // Handle opportunities - could be dict or array
                if (Array.isArray(data.opportunities)) {
                    opportunities = data.opportunities;
                    console.log(`Using opportunities array: ${opportunities.length} items`);
                } else if (typeof data.opportunities === 'object') {
                    // Convert dictionary to array
                    opportunities = Object.values(data.opportunities);
                    console.log(`Converting opportunities dict to array: ${opportunities.length} items`);
                }
            }
            
            console.log(`Total opportunities to display: ${opportunities.length}`);
            
            if (opportunities && opportunities.length > 0) {
                opportunities.slice(0, 20).forEach((opp, index) => {
                    console.log(`Processing opportunity ${index}:`, opp);
                    
                    // Extract strike and option type from option string if needed
                    let strike = '-';
                    let optionType = '-';
                    let expiration = '-';
                    
                    // If we have an 'option' field like "AMZN 240.0 CALL exp 2025-10-03"
                    if (opp.option) {
                        const optionParts = opp.option.match(/(\d+\.?\d*)\s+(CALL|PUT).*exp\s+(\d{4}-\d{2}-\d{2})/i);
                        if (optionParts) {
                            strike = optionParts[1];
                            optionType = optionParts[2];
                            expiration = optionParts[3];
                        }
                    }
                    
                    // Override with more specific fields if available
                    const plan = opp.trade_plan || opp.trading_plan || {};
                    const best = opp.best_opportunity || {};
                    const explosiveData = opp.full_explosive_analysis || {};
                    const explosiveBest = explosiveData.best_opportunity || {};
                    
                    // Get values from different possible sources
                    strike = plan.strike || best.strike || explosiveBest.strike || strike;
                    optionType = plan.option_type || plan.type || best.type || explosiveBest.type || optionType;
                    expiration = plan.expiration || best.expiration || explosiveBest.expiration || opp.expiration || expiration;
                    
                    // Get entry price and target
                    const entryPrice = opp.entry_price || plan.entry_price || best.mark || explosiveBest.mark || '-';
                    const target = opp.target_1 || plan.initial_target || plan.target || best.target || explosiveBest.target || '-';
                    
                    // Get score - handle both combined scores and regular scores
                    const score = opp.score || opp.combined_score || opp.total_score || best.total_score || explosiveBest.total_score || 0;
                    
                    // Get or generate recommendation
                    let recommendation = opp.recommendation || best.recommendation || explosiveBest.recommendation || '';
                    if (!recommendation && score > 0) {
                        if (score >= 75) recommendation = '🔥 STRONG BUY';
                        else if (score >= 60) recommendation = '✅ BUY';
                        else if (score >= 45) recommendation = '⚡ WATCH';
                        else recommendation = '📊 ANALYZE';
                    }
                    
                    html += '<tr class="border-b hover:bg-gray-50">';
                    html += '<td class="p-2 font-semibold">' + (opp.symbol || '-') + '</td>';
                    html += '<td class="p-2">$' + (strike !== '-' ? parseFloat(strike).toFixed(2) : '-') + '</td>';
                    html += '<td class="p-2">' + (optionType.toString().toUpperCase()) + '</td>';
                    html += '<td class="p-2">' + (expiration.toString().split(' ')[0]) + '</td>';
                    html += '<td class="p-2">$' + (entryPrice !== '-' ? parseFloat(entryPrice).toFixed(2) : '-') + '</td>';
                    html += '<td class="p-2">$' + (target !== '-' ? parseFloat(target).toFixed(2) : '-') + '</td>';
                    html += '<td class="p-2">' + (typeof score === 'number' ? score.toFixed(1) : '0.0') + '</td>';
                    html += '<td class="p-2">' + recommendation + '</td>';
                    html += '</tr>';
                });
            } else {
                html += '<tr><td colspan="8" class="p-4 text-center text-gray-500">No opportunities found matching your criteria</td></tr>';
            }
            
            html += '</tbody></table></div>';
            
            // Add summary information if available
            if (data.summary) {
                html += '<div class="mt-4 p-4 bg-blue-50 rounded-lg">';
                html += '<h4 class="font-semibold mb-2">Scan Summary:</h4>';
                html += '<p class="text-sm">' + data.summary + '</p>';
                html += '</div>';
            }
            
            // Add scan metadata if available
            if (data.scan_metadata) {
                html += '<div class="mt-4 p-4 bg-gray-50 rounded-lg">';
                html += '<h4 class="font-semibold mb-2">Scan Details:</h4>';
                html += '<p class="text-sm text-gray-600">' + (data.scan_metadata.methodology || 'Advanced options analysis') + '</p>';
                html += '</div>';
            }
            
            // Show summary stats if opportunities were found
            if (opportunities.length > 0) {
                html += '<div class="mt-4 p-4 bg-green-50 rounded-lg">';
                html += '<h4 class="font-semibold mb-2">Results Summary:</h4>';
                html += '<p class="text-sm text-gray-600">Found ' + opportunities.length + ' trading opportunities';
                if (opportunities.length > 20) {
                    html += ' (showing top 20)';
                }
                html += '</p>';
                html += '</div>';
            }
            
            document.getElementById('resultsContent').innerHTML = html;
        }

        function logout() {
            localStorage.removeItem('token');
            window.location.href = '/';
        }
        
        // Initialize on page load
        window.addEventListener('DOMContentLoaded', loadUserInfo);
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
        
        /* Custom toggle switch styles */
        .toggle-switch {
            position: relative;
            width: 200px;
            height: 44px;
            background: #e5e7eb;
            border-radius: 22px;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        
        .toggle-switch.monthly {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .toggle-slider {
            position: absolute;
            top: 4px;
            left: 4px;
            width: 92px;
            height: 36px;
            background: white;
            border-radius: 18px;
            transition: transform 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .toggle-switch.monthly .toggle-slider {
            transform: translateX(100px);
        }
        
        .toggle-label {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            font-weight: 600;
            font-size: 14px;
            transition: color 0.3s ease;
        }
        
        .toggle-label.weekly {
            left: 20px;
            color: #4b5563;
        }
        
        .toggle-label.monthly {
            right: 20px;
            color: #9ca3af;
        }
        
        .toggle-switch.monthly .toggle-label.weekly {
            color: #e5e7eb;
        }
        
        .toggle-switch.monthly .toggle-label.monthly {
            color: white;
        }
        
        /* Animation for price changes */
        .price-fade {
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Savings badge animation */
        .savings-badge {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
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
        <h1 class="text-4xl font-bold text-center mb-8">Choose Your Plan</h1>
        
        <!-- Billing Period Toggle -->
        <div class="flex justify-center mb-8">
            <div class="bg-white rounded-full shadow-lg p-2 flex items-center">
                <div id="billingToggle" class="toggle-switch monthly">
                    <div class="toggle-slider"></div>
                    <span class="toggle-label weekly">Weekly</span>
                    <span class="toggle-label monthly">Monthly</span>
                </div>
            </div>
        </div>
        
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
        
        // Pricing data for each currency with both weekly and monthly options
        const pricingData = {
            'USD': {
                symbol: '$',
                weekly: [
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
                        id: 'basic_usd_weekly',
                        name: 'Basic',
                        price: 7,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_usd_weekly',
                        name: 'Premium',
                        price: 25,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ],
                monthly: [
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
                        id: 'basic_usd_monthly',
                        name: 'Basic',
                        price: 29,
                        popular: true,
                        savings: '40',
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_usd_monthly',
                        name: 'Premium',
                        price: 99,
                        savings: '37',
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
                weekly: [
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
                        id: 'basic_eur_weekly',
                        name: 'Basic',
                        price: 6.50,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_eur_weekly',
                        name: 'Premium',
                        price: 23,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ],
                monthly: [
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
                        id: 'basic_eur_monthly',
                        name: 'Basic',
                        price: 27,
                        popular: true,
                        savings: '39',
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_eur_monthly',
                        name: 'Premium',
                        price: 92,
                        savings: '35',
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
                weekly: [
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
                        id: 'basic_gbp_weekly',
                        name: 'Basic',
                        price: 5.50,
                        popular: true,
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_gbp_weekly',
                        name: 'Premium',
                        price: 20,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features'
                        ]
                    }
                ],
                monthly: [
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
                        id: 'basic_gbp_monthly',
                        name: 'Basic',
                        price: 23,
                        popular: true,
                        savings: '38',
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support'
                        ]
                    },
                    {
                        id: 'premium_gbp_monthly',
                        name: 'Premium',
                        price: 79,
                        savings: '36',
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
                weekly: [
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
                        id: 'basic_usdc_weekly',
                        name: 'Basic',
                        price: 7,
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
                        id: 'premium_usdc_weekly',
                        name: 'Premium',
                        price: 25,
                        features: [
                            '500 scans/day',
                            'All scanners',
                            'Priority support',
                            'Advanced features',
                            '🔐 Pay with crypto'
                        ]
                    }
                ],
                monthly: [
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
                        id: 'basic_usdc_monthly',
                        name: 'Basic',
                        price: 29,
                        popular: true,
                        savings: '40',
                        features: [
                            '50 scans/day',
                            'Explosive scanner',
                            'Technical analysis',
                            'Email support',
                            '🔐 Pay with crypto'
                        ]
                    },
                    {
                        id: 'premium_usdc_monthly',
                        name: 'Premium',
                        price: 99,
                        savings: '37',
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
        let currentPeriod = 'monthly'; // Default to monthly
        
        function loadPricing(currency = null, period = null) {
            // Update current values if provided
            if (currency) currentCurrency = currency;
            if (period) currentPeriod = period;
            
            const data = pricingData[currentCurrency];
            const plans = data[currentPeriod];
            const container = document.getElementById('pricingCards');
            const cryptoBadge = document.getElementById('cryptoBadge');
            
            // Show/hide crypto badge
            if (currentCurrency === 'USDC') {
                cryptoBadge.classList.remove('hidden');
            } else {
                cryptoBadge.classList.add('hidden');
            }
            
            // Add animation class
            container.classList.add('price-fade');
            
            container.innerHTML = plans.map(plan => `
                <div class="bg-white p-6 rounded-lg shadow-lg ${plan.popular ? 'transform scale-105 border-2 border-purple-600 relative' : ''} transition-all duration-300">
                    ${plan.popular ? 
                        '<div class="absolute -top-3 left-1/2 transform -translate-x-1/2"><span class="bg-gradient-to-r from-yellow-400 to-orange-400 text-white px-4 py-1 rounded-full text-sm font-bold">Most Popular</span></div>' : 
                        ''
                    }
                    <h3 class="text-xl font-semibold mb-3 ${plan.popular ? 'mt-2' : ''}">${plan.name}</h3>
                    
                    ${plan.savings && currentPeriod === 'monthly' ? 
                        `<div class="mb-2">
                            <span class="inline-block bg-green-100 text-green-800 text-xs font-bold px-3 py-1 rounded-full savings-badge">
                                Save ${plan.savings}%
                            </span>
                        </div>` : 
                        ''
                    }
                    
                    <p class="text-3xl font-bold mb-4 price-fade">
                        ${data.symbol}${plan.price}${data.suffix || ''}
                        <span class="text-sm text-gray-600">/${currentPeriod === 'weekly' ? 'week' : 'month'}</span>
                    </p>
                    
                    ${currentCurrency === 'USDC' && plan.price > 0 ? 
                        '<div class="mb-4"><span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">₿ Pay with Crypto</span></div>' : 
                        ''
                    }
                    
                    <ul class="text-gray-600 space-y-2 mb-6">
                        ${plan.features.map(f => `<li class="flex items-start"><span class="text-green-500 mr-2">✓</span><span>${f}</span></li>`).join('')}
                    </ul>
                    
                    ${plan.price > 0 ? 
                        `<button onclick="subscribe('${plan.id}', '${currentCurrency}', '${currentPeriod}')" class="w-full ${plan.popular ? 'bg-gradient-to-r from-purple-600 to-purple-700' : 'bg-purple-600'} text-white py-3 rounded-lg hover:shadow-lg transition-all duration-200 font-semibold">
                            ${currentCurrency === 'USDC' ? 'Pay with Crypto' : 'Subscribe Now'}
                        </button>` :
                        `<a href="/register" class="block w-full bg-gray-600 text-white py-3 rounded-lg text-center hover:bg-gray-700 transition-all duration-200 font-semibold">
                            Start Free
                        </a>`
                    }
                </div>
            `).join('');
            
            // Remove animation class after animation completes
            setTimeout(() => {
                container.classList.remove('price-fade');
            }, 300);
        }
        
        async function subscribe(planId, currency, period) {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            // Get plan details from current pricing data
            const data = pricingData[currency];
            const plans = data[period];
            const plan = plans.find(p => p.id === planId);
            
            if (!plan) {
                alert('Error: Plan not found');
                return;
            }
            
            // Extract tier from planId (format: tier_currency_period)
            let tier = 'free';
            if (planId.startsWith('basic')) tier = 'basic';
            else if (planId.startsWith('premium')) tier = 'premium';
            
            // Redirect to payment method selection page with plan details
            const params = new URLSearchParams({
                tier: tier,
                name: plan.name,
                price: plan.price,
                period: period,
                currency: currency
            });
            
            window.location.href = '/payment-method?' + params.toString();
        }
        
        // Initialize pricing and event handlers on page load
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize with monthly pricing
            loadPricing('USD', 'monthly');
            
            // Handle billing period toggle
            const billingToggle = document.getElementById('billingToggle');
            billingToggle.addEventListener('click', () => {
                // Toggle the visual state
                billingToggle.classList.toggle('monthly');
                
                // Determine new period
                const newPeriod = billingToggle.classList.contains('monthly') ? 'monthly' : 'weekly';
                
                // Reload pricing with new period
                loadPricing(null, newPeriod);
            });
            
            // Handle currency selector
            document.getElementById('currencySelector').addEventListener('change', (e) => {
                loadPricing(e.target.value, null);
            });
        });
    </script>
</body>
</html>
"""

# Admin Dashboard Template
PAYMENT_METHOD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Select Payment Method - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.stripe.com/v3/"></script>
    <style>
        .payment-option {
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .payment-option:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        .badge-popular {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                    <a href="/pricing" class="text-gray-700 hover:text-purple-600">← Back to Pricing</a>
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-4xl mx-auto px-4 py-12">
        <!-- Order Summary -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 class="text-2xl font-bold mb-4">Order Summary</h2>
            <div class="flex justify-between items-center border-b pb-4 mb-4">
                <div>
                    <p class="font-semibold text-lg" id="planName">Loading...</p>
                    <p class="text-gray-600" id="billingPeriod">Loading...</p>
                </div>
                <div class="text-right">
                    <p class="text-2xl font-bold" id="planPrice">Loading...</p>
                    <p class="text-sm text-gray-500" id="periodLabel">Loading...</p>
                </div>
            </div>
            
            <!-- Account Balance Display -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div class="flex items-center justify-between">
                    <span class="text-blue-700 font-medium">Your Account Balance:</span>
                    <span class="text-2xl font-bold text-blue-900" id="accountBalance">Loading...</span>
                </div>
                <div id="balanceMessage" class="mt-2 text-sm"></div>
            </div>
        </div>

        <!-- Payment Methods -->
        <h1 class="text-3xl font-bold text-center mb-8">Select Payment Method</h1>
        
        <div class="grid md:grid-cols-3 gap-6">
            <!-- Pay with Card -->
            <div onclick="selectPaymentMethod('stripe')" class="payment-option bg-white rounded-lg shadow-lg p-6 border-2 border-transparent hover:border-purple-500">
                <div class="text-center mb-4">
                    <div class="w-16 h-16 bg-purple-100 rounded-full mx-auto flex items-center justify-center mb-3">
                        <span class="text-2xl">💳</span>
                    </div>
                    <h3 class="text-xl font-bold">Pay with Card</h3>
                    <span class="inline-block mt-2 px-3 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">Most Popular</span>
                </div>
                <ul class="text-sm text-gray-600 space-y-2">
                    <li>✓ Secure Stripe checkout</li>
                    <li>✓ All major cards accepted</li>
                    <li>✓ Instant activation</li>
                    <li>✓ Auto-renewal available</li>
                </ul>
                <button class="w-full mt-4 bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 transition">
                    Continue with Card
                </button>
            </div>

            <!-- Pay with Crypto -->
            <div onclick="selectPaymentMethod('crypto')" class="payment-option bg-white rounded-lg shadow-lg p-6 border-2 border-transparent hover:border-green-500">
                <div class="text-center mb-4">
                    <div class="w-16 h-16 bg-green-100 rounded-full mx-auto flex items-center justify-center mb-3">
                        <span class="text-2xl">₿</span>
                    </div>
                    <h3 class="text-xl font-bold">Pay with USDC</h3>
                    <span class="inline-block mt-2 px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">Stablecoin (1:1 USD)</span>
                </div>
                <ul class="text-sm text-gray-600 space-y-2">
                    <li>✓ USDC stablecoin pegged to USD</li>
                    <li>✓ Pay via Stripe Link</li>
                    <li>✓ Secure & regulated</li>
                    <li>✓ Same price as USD</li>
                </ul>
                <button class="w-full mt-4 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition">
                    Continue with USDC
                </button>
            </div>

            <!-- Pay with Credits -->
            <div onclick="selectPaymentMethod('credits')" class="payment-option bg-white rounded-lg shadow-lg p-6 border-2 border-transparent hover:border-blue-500">
                <div class="text-center mb-4">
                    <div class="w-16 h-16 bg-blue-100 rounded-full mx-auto flex items-center justify-center mb-3">
                        <span class="text-2xl">💰</span>
                    </div>
                    <h3 class="text-xl font-bold">Pay with Credits</h3>
                    <span id="creditStatus" class="inline-block mt-2 px-3 py-1 text-xs font-semibold rounded-full">Checking balance...</span>
                </div>
                <ul class="text-sm text-gray-600 space-y-2">
                    <li>✓ Use account balance</li>
                    <li>✓ Instant activation</li>
                    <li>✓ No transaction fees</li>
                    <li>✓ Simple one-click payment</li>
                </ul>
                <button id="creditPayButton" class="w-full mt-4 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition">
                    Pay with Credits
                </button>
            </div>
        </div>

        <!-- Info Section -->
        <div class="mt-8 text-center text-gray-600">
            <p>All payment methods are secure and encrypted</p>
            <p class="mt-2">Need help? <a href="#" class="text-purple-600 hover:underline">Contact support</a></p>
        </div>
    </div>

    <script>
        const stripe = Stripe('pk_test_51J1234567890'); // Will be replaced with actual key
        let planDetails = {};
        let userBalance = 0;
        
        async function loadPaymentPage() {
            // Get plan details from URL params
            const urlParams = new URLSearchParams(window.location.search);
            planDetails = {
                tier: urlParams.get('tier'),
                name: urlParams.get('name'),
                price: parseFloat(urlParams.get('price')),
                period: urlParams.get('period') || 'monthly',
                currency: urlParams.get('currency') || 'USD'
            };
            
            // Display plan details
            document.getElementById('planName').textContent = planDetails.name + ' Plan';
            document.getElementById('billingPeriod').textContent = planDetails.period.charAt(0).toUpperCase() + planDetails.period.slice(1) + ' Billing';
            
            // Format price based on currency
            const currencySymbol = planDetails.currency === 'EUR' ? '€' : 
                                 planDetails.currency === 'GBP' ? '£' : 
                                 planDetails.currency === 'USDC' ? 'USDC ' : '$';
            document.getElementById('planPrice').textContent = currencySymbol + planDetails.price;
            document.getElementById('periodLabel').textContent = 'per ' + (planDetails.period === 'weekly' ? 'week' : 'month');
            
            // Load user balance
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            try {
                const response = await fetch('/api/user/balance', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    userBalance = data.balance;
                    document.getElementById('accountBalance').textContent = data.formatted_balance;
                    
                    // Check if user has sufficient balance for credit payment
                    if (userBalance >= planDetails.price) {
                        document.getElementById('creditStatus').textContent = 'Sufficient Balance';
                        document.getElementById('creditStatus').className = 'inline-block mt-2 px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full';
                        document.getElementById('balanceMessage').innerHTML = '<span class="text-green-600">✓ You have sufficient balance to pay with credits</span>';
                        document.getElementById('creditPayButton').disabled = false;
                    } else {
                        document.getElementById('creditStatus').textContent = 'Insufficient Balance';
                        document.getElementById('creditStatus').className = 'inline-block mt-2 px-3 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded-full';
                        document.getElementById('balanceMessage').innerHTML = '<span class="text-red-600">✗ You need $' + (planDetails.price - userBalance).toFixed(2) + ' more to pay with credits</span>';
                        document.getElementById('creditPayButton').disabled = true;
                        document.getElementById('creditPayButton').className = 'w-full mt-4 bg-gray-400 text-white py-2 rounded-lg cursor-not-allowed';
                    }
                } else {
                    console.error('Failed to fetch balance');
                    document.getElementById('accountBalance').textContent = 'Error loading';
                }
            } catch (error) {
                console.error('Error loading balance:', error);
                document.getElementById('accountBalance').textContent = 'Error loading';
            }
        }
        
        async function selectPaymentMethod(method) {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            if (method === 'stripe') {
                // Redirect to Stripe checkout
                const response = await fetch('/api/stripe/create-checkout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        plan_tier: planDetails.tier,
                        billing_interval: planDetails.period,
                        currency: planDetails.currency.toLowerCase()
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.checkout_url) {
                        window.location.href = data.checkout_url;
                    } else {
                        alert('Error creating checkout session');
                    }
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.message);
                }
                
            } else if (method === 'crypto') {
                // Redirect to Stripe checkout with crypto payment
                const response = await fetch('/api/stripe/create-checkout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        plan_tier: planDetails.tier,
                        billing_interval: planDetails.period,
                        currency: 'usdc',
                        payment_type: 'crypto'
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.checkout_url) {
                        window.location.href = data.checkout_url;
                    } else {
                        alert('Error creating crypto checkout session');
                    }
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.message);
                }
                
            } else if (method === 'credits') {
                // Check balance again before processing
                if (userBalance < planDetails.price) {
                    alert('Insufficient balance. Please top up your account or choose another payment method.');
                    return;
                }
                
                // Process credit payment
                if (confirm(`Confirm payment of $${planDetails.price} from your account balance?`)) {
                    const response = await fetch('/api/subscription/credit-payment', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({
                            plan_tier: planDetails.tier,
                            billing_interval: planDetails.period
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        alert(data.message + '\\n\\nRemaining balance: ' + data.formatted_balance);
                        window.location.href = '/dashboard';
                    } else {
                        const error = await response.json();
                        alert('Error: ' + error.message);
                    }
                }
            }
        }
        
        // Load page data on load
        loadPaymentPage();
    </script>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Options Scanner Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 50;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        .modal-content {
            background-color: white;
            margin: 10% auto;
            padding: 20px;
            border-radius: 10px;
            width: 500px;
            max-width: 90%;
        }
        .modal.show {
            display: block;
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-xl font-bold text-purple-600">Options Scanner Pro - Admin</span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/" class="text-gray-700 hover:text-purple-600">Home</a>
                    <a href="/dashboard" class="text-gray-700 hover:text-purple-600">Dashboard</a>
                    <a href="/admin" class="text-gray-700 hover:text-purple-600 font-bold">Admin</a>
                    <button onclick="logout()" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Logout</button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Header -->
    <div class="gradient-bg text-white py-10">
        <div class="max-w-7xl mx-auto px-4">
            <h1 class="text-3xl font-bold">Admin Dashboard</h1>
            <p class="mt-2">Manage users, subscriptions, and account balances</p>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Search Bar -->
        <div class="mb-6 bg-white p-4 rounded-lg shadow">
            <input type="text" id="searchInput" placeholder="Search users by email, name, or company..." 
                   class="w-full px-4 py-2 border rounded-lg" onkeyup="searchUsers()">
        </div>

        <!-- Users Table -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="min-w-full">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subscription</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Active</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody" class="bg-white divide-y divide-gray-200">
                    <!-- Users will be loaded here -->
                </tbody>
            </table>
        </div>

        <!-- Pagination -->
        <div class="mt-4 flex justify-between items-center">
            <div>
                <span id="pageInfo" class="text-gray-600"></span>
            </div>
            <div class="space-x-2">
                <button onclick="previousPage()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">Previous</button>
                <button onclick="nextPage()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">Next</button>
            </div>
        </div>
    </div>

    <!-- Top Up Modal -->
    <div id="topupModal" class="modal">
        <div class="modal-content">
            <h2 class="text-2xl font-bold mb-4">Top Up User Balance</h2>
            <p class="mb-2">User: <span id="topupUserEmail" class="font-semibold"></span></p>
            <p class="mb-4">Current Balance: $<span id="currentBalance" class="font-semibold"></span></p>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Select Amount:</label>
                <div class="grid grid-cols-3 gap-2 mb-4">
                    <button onclick="setTopupAmount(10)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$10</button>
                    <button onclick="setTopupAmount(25)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$25</button>
                    <button onclick="setTopupAmount(50)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$50</button>
                    <button onclick="setTopupAmount(100)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$100</button>
                    <button onclick="setTopupAmount(500)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$500</button>
                    <button onclick="setTopupAmount(1000)" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">$1000</button>
                </div>
                
                <label class="block text-sm font-medium mb-2">Or enter custom amount:</label>
                <input type="number" id="topupAmount" placeholder="Enter amount" class="w-full px-3 py-2 border rounded-lg" step="0.01" min="0.01" max="10000">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Description (optional):</label>
                <input type="text" id="topupDescription" placeholder="Reason for top-up" class="w-full px-3 py-2 border rounded-lg">
            </div>
            
            <div class="flex justify-end space-x-2">
                <button onclick="closeTopupModal()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">Cancel</button>
                <button onclick="confirmTopup()" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Confirm Top Up</button>
            </div>
        </div>
    </div>

    <!-- Grant Subscription Modal -->
    <div id="subscriptionModal" class="modal">
        <div class="modal-content">
            <h2 class="text-2xl font-bold mb-4">Grant Subscription</h2>
            <p class="mb-2">User: <span id="subUserEmail" class="font-semibold"></span></p>
            <p class="mb-4">Current Plan: <span id="currentPlan" class="font-semibold"></span></p>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Select Plan Tier:</label>
                <select id="planTier" class="w-full px-3 py-2 border rounded-lg">
                    <option value="free">Free</option>
                    <option value="basic" selected>Basic</option>
                    <option value="premium">Premium</option>
                </select>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Duration (days):</label>
                <select id="duration" class="w-full px-3 py-2 border rounded-lg">
                    <option value="7">7 days</option>
                    <option value="30" selected>30 days</option>
                    <option value="90">90 days</option>
                    <option value="180">180 days</option>
                    <option value="365">365 days</option>
                </select>
            </div>
            
            <div class="flex justify-end space-x-2">
                <button onclick="closeSubscriptionModal()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">Cancel</button>
                <button onclick="confirmGrantSubscription()" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Grant Subscription</button>
            </div>
        </div>
    </div>

    <script>
        let currentPage = 1;
        let totalPages = 1;
        let currentUserId = null;
        let users = [];

        async function loadUsers(page = 1) {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }

            try {
                const response = await fetch(`/api/admin/users?page=${page}&per_page=20`, {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });

                if (response.status === 403) {
                    alert('Access denied. Admin privileges required.');
                    window.location.href = '/dashboard';
                    return;
                }

                const data = await response.json();
                if (data.status === 'success') {
                    users = data.users;
                    currentPage = data.pagination.page;
                    totalPages = data.pagination.pages;
                    renderUsers();
                    updatePageInfo(data.pagination);
                }
            } catch (error) {
                console.error('Error loading users:', error);
            }
        }

        function renderUsers() {
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';

            users.forEach(user => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div>
                            <div class="text-sm font-medium text-gray-900">${user.email}</div>
                            <div class="text-sm text-gray-500">${user.first_name || ''} ${user.last_name || ''}</div>
                            <div class="text-xs text-gray-400">${user.company || ''}</div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-sm font-semibold">$${user.account_balance.toFixed(2)}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                            ${user.subscription.tier === 'premium' ? 'bg-purple-100 text-purple-800' : 
                              user.subscription.tier === 'basic' ? 'bg-blue-100 text-blue-800' : 
                              'bg-gray-100 text-gray-800'}">
                            ${user.subscription.tier.toUpperCase()}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                            ${user.status === 'active' ? 'bg-green-100 text-green-800' : 
                              'bg-red-100 text-red-800'}">
                            ${user.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${user.last_activity ? new Date(user.last_activity).toLocaleDateString() : 'Never'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button onclick="openTopupModal(${user.id}, '${user.email}', ${user.account_balance})" 
                                class="text-green-600 hover:text-green-900 mr-3">Top Up</button>
                        <button onclick="openSubscriptionModal(${user.id}, '${user.email}', '${user.subscription.tier}')" 
                                class="text-blue-600 hover:text-blue-900">Grant Sub</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function updatePageInfo(pagination) {
            document.getElementById('pageInfo').textContent = 
                `Showing ${(pagination.page - 1) * pagination.per_page + 1} to ${Math.min(pagination.page * pagination.per_page, pagination.total)} of ${pagination.total} users`;
        }

        function searchUsers() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            // For now, we'll just filter the current page
            // In production, this should make an API call with search parameter
            const filtered = users.filter(user => 
                user.email.toLowerCase().includes(searchTerm) ||
                (user.first_name && user.first_name.toLowerCase().includes(searchTerm)) ||
                (user.last_name && user.last_name.toLowerCase().includes(searchTerm)) ||
                (user.company && user.company.toLowerCase().includes(searchTerm))
            );
            // Re-render with filtered results
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';
            filtered.forEach(user => {
                // Same rendering logic as in renderUsers()
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div>
                            <div class="text-sm font-medium text-gray-900">${user.email}</div>
                            <div class="text-sm text-gray-500">${user.first_name || ''} ${user.last_name || ''}</div>
                            <div class="text-xs text-gray-400">${user.company || ''}</div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-sm font-semibold">$${user.account_balance.toFixed(2)}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                            ${user.subscription.tier === 'premium' ? 'bg-purple-100 text-purple-800' : 
                              user.subscription.tier === 'basic' ? 'bg-blue-100 text-blue-800' : 
                              'bg-gray-100 text-gray-800'}">
                            ${user.subscription.tier.toUpperCase()}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                            ${user.status === 'active' ? 'bg-green-100 text-green-800' : 
                              'bg-red-100 text-red-800'}">
                            ${user.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${user.last_activity ? new Date(user.last_activity).toLocaleDateString() : 'Never'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button onclick="openTopupModal(${user.id}, '${user.email}', ${user.account_balance})" 
                                class="text-green-600 hover:text-green-900 mr-3">Top Up</button>
                        <button onclick="openSubscriptionModal(${user.id}, '${user.email}', '${user.subscription.tier}')" 
                                class="text-blue-600 hover:text-blue-900">Grant Sub</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function previousPage() {
            if (currentPage > 1) {
                loadUsers(currentPage - 1);
            }
        }

        function nextPage() {
            if (currentPage < totalPages) {
                loadUsers(currentPage + 1);
            }
        }

        function openTopupModal(userId, email, balance) {
            currentUserId = userId;
            document.getElementById('topupUserEmail').textContent = email;
            document.getElementById('currentBalance').textContent = balance.toFixed(2);
            document.getElementById('topupAmount').value = '';
            document.getElementById('topupDescription').value = '';
            document.getElementById('topupModal').classList.add('show');
        }

        function closeTopupModal() {
            document.getElementById('topupModal').classList.remove('show');
            currentUserId = null;
        }

        function setTopupAmount(amount) {
            document.getElementById('topupAmount').value = amount;
        }

        async function confirmTopup() {
            const amount = parseFloat(document.getElementById('topupAmount').value);
            const description = document.getElementById('topupDescription').value;

            if (!amount || amount <= 0) {
                alert('Please enter a valid amount');
                return;
            }

            const token = localStorage.getItem('token');
            try {
                const response = await fetch(`/api/admin/topup/${currentUserId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        amount: amount,
                        description: description || 'Admin credit adjustment'
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    alert(data.message);
                    closeTopupModal();
                    loadUsers(currentPage);
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error processing topup: ' + error.message);
            }
        }

        function openSubscriptionModal(userId, email, currentTier) {
            currentUserId = userId;
            document.getElementById('subUserEmail').textContent = email;
            document.getElementById('currentPlan').textContent = currentTier.toUpperCase();
            document.getElementById('subscriptionModal').classList.add('show');
        }

        function closeSubscriptionModal() {
            document.getElementById('subscriptionModal').classList.remove('show');
            currentUserId = null;
        }

        async function confirmGrantSubscription() {
            const tier = document.getElementById('planTier').value;
            const duration = parseInt(document.getElementById('duration').value);

            const token = localStorage.getItem('token');
            try {
                const response = await fetch(`/api/admin/grant-subscription/${currentUserId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        tier: tier,
                        duration_days: duration
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    alert(data.message);
                    closeSubscriptionModal();
                    loadUsers(currentPage);
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error granting subscription: ' + error.message);
            }
        }

        function logout() {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }

        // Load users on page load
        window.onload = () => {
            loadUsers();
        };
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

@frontend_app.route('/payment-method')
def payment_method():
    return render_template_string(PAYMENT_METHOD_TEMPLATE)

@frontend_app.route('/admin')
def admin():
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE)

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