#!/bin/bash

# Page Visit Counter - Startup Script

echo "Starting Page Visit Counter API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"

uvicorn page_count:app --reload --host 0.0.0.0 --port 8000
