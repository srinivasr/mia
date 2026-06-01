#!/usr/bin/env bash
set -e

# Setup trap to kill background jobs when script exits
trap 'kill $(jobs -p) 2>/dev/null || true' SIGINT SIGTERM EXIT

echo "Starting mia_n_mia runtime..."

# Kill lingering processes that might bind to our ports
echo "Cleaning up old processes..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8765/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# 1. Setup Python Environment
echo "Checking Python environment..."
if [ ! -d "brain/venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    cd brain
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    playwright install
    cd ..
else
    echo "Python venv found. Skipping dependency installation."
fi

# 2. Setup Node Environment
echo "Checking Node environment..."
if [ ! -d "ui/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd ui
    npm install
    cd ..
else
    echo "Node modules found. Skipping frontend installation."
fi

# Ensure dist directory exists for Tauri macro
mkdir -p ui/dist

# Start Python Servers in background using subshells
echo "Starting Python Backend Server..."
(cd brain && source venv/bin/activate && python main.py) &

# Wait for servers to initialise
sleep 2

# Start Rust Backend / Tauri (which also starts Svelte frontend)
echo "Starting Tauri runtime and Svelte frontend..."
cd ui
npm run tauri dev
