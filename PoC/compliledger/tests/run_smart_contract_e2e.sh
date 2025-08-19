#!/usr/bin/env bash
set -euo pipefail

# Simple runner for the Smart Contract E2E test
# Usage: ./run_smart_contract_e2e.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/compliledger/backend:$PROJECT_ROOT/compliledger/contracts:${PYTHONPATH:-}"

echo "[CompliLedger] Running Smart Contract E2E test..."
python3 "$SCRIPT_DIR/test_e2e_smart_contract.py"
