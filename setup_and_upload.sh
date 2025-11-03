#!/bin/bash

# Setup and Upload Script for NSFW DB Manager
# This script sets up the backend and uploads the CSV data

set -e  # Exit on error

echo "===================================================================="
echo "NSFW DB Manager - Setup and Upload"
echo "===================================================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"
echo ""

# Step 1: Stop any running backend
echo "[1/4] Stopping any running backend..."
pkill -f "python.*run_server" || echo "No backend was running"
sleep 2
echo ""

# Step 2: Clean and setup database
echo "[2/4] Setting up fresh database..."
cd "$PROJECT_ROOT/nsfw_db_manager/backend"
rm -f nsfw_assets.db
rm -f "$PROJECT_ROOT/nsfw_assets.db"
echo "✓ Old databases removed"
echo ""

# Step 3: Start backend
echo "[3/4] Starting backend server..."
echo "Backend will run in the background..."

# Clear any external DATABASE_URL that might interfere
unset DATABASE_URL

# Check for virtual environment
if [ -d ".venv/bin" ]; then
    echo "Using virtual environment: .venv"
    .venv/bin/python run_server.py > backend.log 2>&1 &
elif [ -d "venv/bin" ]; then
    echo "Using virtual environment: venv"
    venv/bin/python run_server.py > backend.log 2>&1 &
else
    echo "No virtual environment found, using system python3"
    python3 run_server.py > backend.log 2>&1 &
fi

BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo "Waiting for backend to start..."
sleep 10

# Wait for backend to be ready
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://127.0.0.1:8001/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    echo "Waiting... ($WAITED/$MAX_WAIT seconds)"
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "✗ Backend did not become ready in time"
    echo "Check backend.log for errors:"
    tail -20 backend.log
    exit 1
fi

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✓ Backend is running"
else
    echo "✗ Backend failed to start. Check backend.log for errors:"
    tail -20 backend.log
    exit 1
fi
echo ""

# Step 4: Upload CSV data
echo "[4/4] Uploading CSV data to database..."
cd "$PROJECT_ROOT"
python3 upload_csv_to_db.py

echo ""
echo "===================================================================="
echo "Setup Complete!"
echo "===================================================================="
echo ""
echo "Backend is running on: http://localhost:8001"
echo "API Docs: http://localhost:8001/docs"
echo "Database location: $PROJECT_ROOT/nsfw_db_manager/backend/nsfw_assets.db"
echo ""
echo "To stop the backend, run: kill $BACKEND_PID"
echo "Or: pkill -f 'python.*run_server'"
echo ""
