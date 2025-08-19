#!/bin/bash

# Script to run the API server and execute API integration test

echo "=========================================="
echo "CompliLedger API Integration Test Runner"
echo "=========================================="

# Set environment variables
export DEBUG=true
export API_HOST=localhost
export API_PORT=8000

# Directory setup
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

echo "[1/4] Setting up Python environment..."
# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

echo "[2/4] Starting FastAPI server in the background..."
# Start the FastAPI server
echo "Current directory: $(pwd)"
cd "$PROJECT_ROOT/compliledger/backend"
echo "Starting server from: $(pwd)"
PYTHONPATH="$PROJECT_ROOT" python3 -m app.main &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for API server to start..."
sleep 5

echo "[3/4] Running API integration test..."
# Run the API integration test
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" python3 "$SCRIPT_DIR/test_api_integration.py"
TEST_EXIT_CODE=$?

echo "[4/4] Cleaning up..."
# Kill the FastAPI server
kill $SERVER_PID

# Output results
echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ API Integration Test: SUCCESS"
  echo "All tests passed successfully!"
else
  echo "❌ API Integration Test: FAILED"
  echo "Please check the logs for details."
fi
echo "=========================================="

exit $TEST_EXIT_CODE
