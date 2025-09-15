#!/bin/bash

# Start the Flask backend in the background
echo "🚀 Starting Flask backend server on port 5001..."
python main.py &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start the Next.js frontend on port 5000
echo "🎨 Starting Next.js frontend on port 5000..."
cd frontend && npm run dev -- --port 5000

# If frontend exits, kill backend
kill $BACKEND_PID 2>/dev/null