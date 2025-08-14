#!/bin/bash

# --- Function to kill all background processes on exit ---
cleanup() {
    echo ""
    echo "Shutting down background processes..."
    if [ -n "$CHATBOT_PID" ]; then
        kill $CHATBOT_PID
        echo "Killed Chatbot Backend (PID: $CHATBOT_PID)"
    fi
    if [ -n "$AUTH_API_PID" ]; then
        kill $AUTH_API_PID
        echo "Killed Auth API Backend (PID: $AUTH_API_PID)"
    fi
    if [ -n "$HOMEPAGE_PID" ]; then
        kill $HOMEPAGE_PID
        echo "Killed Homepage Server (PID: $HOMEPAGE_PID)"
    fi
}

# Trap the EXIT signal to run the cleanup function when the script ends
trap cleanup EXIT

# --- Backend Setup ---
echo "Starting Backends..."
cd "/home/hodauwu/C/ai bot"

# Activate the virtual environment
source venv/bin/activate

# 1. Run the main Chatbot Backend (on port 5000)
nohup python3 chatbot.py > chatbot.log 2>&1 &
CHATBOT_PID=$!
echo "Chatbot Backend started with PID: $CHATBOT_PID. (Logs in chatbot.log)"

# 2. Run the new Authentication API Backend (on port 5001)
nohup python3 api.py > api.log 2>&1 &
AUTH_API_PID=$!
echo "Auth API Backend started with PID: $AUTH_API_PID. (Logs in api.log)"
echo ""

# --- NEW: Homepage Server ---
echo "Starting Static Homepage Server on http://localhost:8000"
cd "/home/hodauwu/C/ai bot/homepage"
nohup python3 -m http.server 8000 > ../homepage.log 2>&1 &
HOMEPAGE_PID=$!
echo "Homepage Server started with PID: $HOMEPAGE_PID. (Logs in homepage.log)"
echo ""

# --- Frontend (React) ---
echo "Starting React Chat App..."
# Navigate to your frontend project's ROOT directory
cd "/home/hodauwu/C/ai bot/ai-bot-web"

# Start the development server. This will be the main process.
npm run dev

# The cleanup function will be called automatically when you stop `npm run dev`

