#!/usr/bin/env python3
"""
End-to-End Integration Test for CompliLedger (Smart Contract - Solidity)
Tests the complete flow: Solidity Source → Heuristic Analysis → OSCAL/IPFS → On-Chain anchoring

This script mirrors test_e2e_flow.py but focuses on Solidity contracts and uses
SmartContractAnalyzer to produce analysis_results injected into the pipeline.
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directories to path to ensure imports work
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "backend"))
sys.path.append(str(PROJECT_ROOT / "contracts"))

# Import required services
try:
    from backend.app.services.smart_contract_analyzer import SmartContractAnalyzer
    from backend.app.services.ipfs_service import IPFSService
    from contracts.contract_integration import ContractIntegrationService
    logger.info("Successfully imported required services for smart contract E2E")
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)


async def test_e2e_smart_contract():
    """Run the end-to-end flow for a Solidity smart contract."""
    logger.info("Starting Smart Contract End-to-End CompliLedger Test")
    logger.info("====================================================")

    # Step 1: Create a sample Solidity contract
    logger.info("Step 1: Creating sample Solidity contract")
    solidity_src = create_sample_solidity()
    artifact_hash = hashlib.sha256(solidity_src.encode()).hexdigest()
    logger.info(f"Created sample Solidity with hash: {artifact_hash}")
    print("\n=== Solidity Source (truncated) ===")
    print(solidity_src[:400] + ("...\n" if len(solidity_src) > 400 else "\n"))

    # Step 2: Run heuristic analysis
    logger.info("Step 2: Running SmartContractAnalyzer")
    analyzer = SmartContractAnalyzer()
    try:
        analysis_results = analyzer.analyze_solidity(solidity_src)
        logger.info(
            "Heuristic analysis complete with score: %s (findings: %s)",
            analysis_results.get("compliance_score", "N/A"),
            analysis_results.get("findings_count", 0),
        )
        print("\n=== Analyzer Results (summary) ===")
        summary = {k: v for k, v in analysis_results.items() if k not in ["findings"]}
        print(json.dumps(summary, indent=2))
        print(f"Findings: {len(analysis_results.get('findings', []))} items\n")
    except Exception as e:
        logger.error(f"Analyzer failed: {str(e)}")
        analysis_results = {"compliance_score": 0, "findings": [], "findings_count": 0}

    # Step 3: Optionally store the raw contract on IPFS (not required by pipeline)
    logger.info("Step 3: Storing contract source on IPFS (optional)")
    ipfs_service = IPFSService()
    try:
        pin_result = await ipfs_service.pin_json(
            data={"type": "solidity_source", "artifact_hash": artifact_hash, "source": solidity_src},
            name=f"solidity-src-{artifact_hash[:8]}",
            artifact_hash=artifact_hash,
        )
        src_cid = pin_result.get("ipfs_cid")
        logger.info(f"Stored source on IPFS with CID: {src_cid}")
    except Exception as e:
        logger.warning(f"IPFS storage for source failed (non-fatal): {str(e)}")
        src_cid = None

    # Step 4: Process through blockchain integration
    logger.info("Step 4: Processing through blockchain integration")
    contract_service = ContractIntegrationService()

    # Build artifact_data expected by integration service
    artifact_data = {
        "name": "TestSmartContract.sol",
        "description": "E2E test for Solidity contract",
        "type": "smart_contract",
        "language": "solidity",
        "hash": artifact_hash,
        "dependencies": [],
        "analysis_results": analysis_results,
    }

    try:
        result = await contract_service.process_artifact(artifact_data)
        logger.info("Blockchain integration complete with status: %s", result.get("status", "unknown"))
        print("\n=== Blockchain Integration Results ===")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Blockchain integration failed: {str(e)}")
        result = {"status": "error", "error": str(e)}

    # Final summary
    logger.info("====================================================")
    logger.info("Smart Contract End-to-End Test Complete")

    print("\n=== Test Summary ===")
    print(f"Contract Hash: {artifact_hash}")
    print(f"Analyzer Score: {analysis_results.get('compliance_score', 'N/A')}")
    if src_cid:
        print(f"Source IPFS CID: {src_cid}")
        print(f"Source IPFS URL: https://gateway.pinata.cloud/ipfs/{src_cid}")
    print(f"Blockchain Status: {result.get('status', 'unknown')}")
    if result.get("status") == "complete":
        print(f"\nRegistry App ID: {result.get('registry_app_id', 'N/A')}")
        print(f"Oracle App ID: {result.get('oracle_app_id', 'N/A')}")
        print(f"Verified OSCAL CID: {result.get('verified_oscal_cid', 'N/A')}")
        print(f"Verified OSCAL URL: {result.get('verified_oscal_url', 'N/A')}")

    return {
        "artifact_hash": artifact_hash,
        "analyzer_score": analysis_results.get("compliance_score", 0),
        "blockchain_status": result.get("status", "unknown"),
        "registry_app_id": result.get("registry_app_id", 0),
        "oracle_app_id": result.get("oracle_app_id", 0),
    }


def create_sample_solidity() -> str:
    """Create a minimal Solidity contract with a couple of patterns for the analyzer."""
    return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vault {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // Bad practice: using tx.origin for auth (should trigger finding)
    modifier onlyOwner() {
        require(tx.origin == owner, "not owner");
        _;
    }

    // Reentrancy risk example via call (should trigger finding)
    function withdraw(address payable to, uint256 amount) external onlyOwner {
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "transfer failed");
    }

    // Self destruct pattern (should trigger finding)
    function destroy() external onlyOwner {
        selfdestruct(payable(owner));
    }

    receive() external payable {}
}
""".strip()


if __name__ == "__main__":
    asyncio.run(test_e2e_smart_contract())
