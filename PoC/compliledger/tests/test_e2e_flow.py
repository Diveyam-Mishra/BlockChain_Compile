#!/usr/bin/env python3
"""
End-to-End Integration Test for CompliLedger
Tests the complete flow: SBOM Input → AI Analysis → Blockchain (On-Chain) Recording

This test:
1. Creates a sample SBOM
2. Processes it through the AI service
3. Verifies the integration with blockchain (Algorand TestNet)
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
    from backend.app.services.ai_service import AIService, AnalysisLevel
    from backend.app.services.ipfs_service import IPFSService
    from contracts.contract_integration import ContractIntegrationService
    logger.info("Successfully imported required services")
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

async def test_e2e_flow():
    """
    Run the end-to-end flow:
    1. Create a sample SBOM
    2. Run AI analysis on the SBOM
    3. Process the results through the blockchain integration
    """
    logger.info("Starting End-to-End CompliLedger Test")
    logger.info("=======================================")
    
    # Step 1: Create a sample SBOM
    logger.info("Step 1: Creating sample SBOM")
    sample_sbom = create_sample_sbom()
    sbom_hash = hashlib.sha256(json.dumps(sample_sbom).encode()).hexdigest()
    logger.info(f"Created sample SBOM with hash: {sbom_hash}")
    print("\n=== Sample SBOM ===")
    print(json.dumps(sample_sbom, indent=2)[:500] + "...\n")
    
    # Step 2: Run AI analysis
    logger.info("Step 2: Running AI analysis")
    ai_service = AIService()
    try:
        logger.info("Analyzing SBOM with Gemini 2.5 Flash")
        analysis_results = await ai_service.analyze_sbom(sample_sbom, level=AnalysisLevel.STANDARD)
        logger.info(f"AI analysis complete with score: {analysis_results.get('overall_score', 'N/A')}")
        print("\n=== AI Analysis Results ===")
        print(json.dumps({k: v for k, v in analysis_results.items() 
                         if k not in ['findings']}, indent=2))
        print(f"Findings: {len(analysis_results.get('findings', []))} items\n")
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}")
        analysis_results = {"error": str(e), "overall_score": 0}
    
    # Step 3: Store on IPFS
    logger.info("Step 3: Storing on IPFS")
    ipfs_service = IPFSService()
    try:
        sbom_with_analysis = {
            "sbom": sample_sbom,
            "analysis": analysis_results
        }
        # Provide required arguments: name and artifact_hash
        pin_result = await ipfs_service.pin_json(
            data=sbom_with_analysis,
            name=f"sbom-verification-{sbom_hash[:8]}",
            artifact_hash=sbom_hash
        )
        cid = pin_result.get("ipfs_cid")
        ipfs_url = pin_result.get("ipfs_url")
        logger.info(f"Stored on IPFS with CID: {cid}")
        logger.info(f"IPFS Gateway URL: {ipfs_url}")
    except Exception as e:
        logger.error(f"IPFS storage failed: {str(e)}")
        cid = None
    
    # Step 4: Process through blockchain integration
    logger.info("Step 4: Processing through blockchain integration")
    contract_service = ContractIntegrationService()
    
    # Create artifact data for blockchain
    artifact_data = {
        "name": "Test SBOM E2E",
        "description": "End-to-End Test SBOM",
        "type": "sbom",
        "format": "cyclonedx",
        "hash": sbom_hash,
        "components": sample_sbom.get("components", []),
        "analysis_results": {
            "compliance_score": analysis_results.get("overall_score", 0),
            "ipfs_cid": cid if cid else "mock_cid_placeholder",
            "findings_count": len(analysis_results.get("findings", [])),
            "controls_passed": len([f for f in analysis_results.get("findings", []) 
                                   if f.get("status") == "pass"]),
            "controls_failed": len([f for f in analysis_results.get("findings", []) 
                                   if f.get("status") == "fail"])
        }
    }
    
    try:
        blockchain_result = await contract_service.process_artifact(artifact_data)
        logger.info(f"Blockchain integration complete with status: {blockchain_result.get('status', 'unknown')}")
        print("\n=== Blockchain Integration Results ===")
        print(json.dumps(blockchain_result, indent=2))
    except Exception as e:
        logger.error(f"Blockchain integration failed: {str(e)}")
        blockchain_result = {"status": "error", "error": str(e)}
    
    # Final status and summary
    logger.info("=======================================")
    logger.info("End-to-End Test Complete")
    
    print("\n=== Test Summary ===")
    print(f"SBOM Hash: {sbom_hash}")
    print(f"AI Analysis Score: {analysis_results.get('overall_score', 'N/A')}")
    if cid:
        print(f"IPFS CID: {cid}")
        print(f"IPFS Gateway URL: https://gateway.pinata.cloud/ipfs/{cid}")
    print(f"Blockchain Status: {blockchain_result.get('status', 'unknown')}")
    
    if blockchain_result.get("status") == "complete":
        print(f"\nBlockchain Explorer Links:")
        print(f"Registry Contract: https://testnet.explorer.perawallet.app/application/{blockchain_result.get('registry_app_id', 'N/A')}/")
        print(f"Oracle Contract: https://testnet.explorer.perawallet.app/application/{blockchain_result.get('oracle_app_id', 'N/A')}/")
    
    return {
        "sbom": sbom_hash,
        "ai_score": analysis_results.get("overall_score", 0),
        "ipfs_cid": cid,
        "blockchain_status": blockchain_result.get("status", "unknown"),
        "registry_app_id": blockchain_result.get("registry_app_id", 0),
        "oracle_app_id": blockchain_result.get("oracle_app_id", 0),
    }

def create_sample_sbom():
    """Create a realistic sample SBOM for testing"""
    # CycloneDX format SBOM
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": "urn:uuid:ed50646c-6afc-4d3e-8f24-fa17cad66aa1",
        "version": 1,
        "metadata": {
            "timestamp": "2023-06-09T10:30:15Z",
            "tools": [
                {
                    "vendor": "CompliLedger",
                    "name": "SBOM Generator",
                    "version": "1.0.0"
                }
            ],
            "authors": [
                {
                    "name": "CompliLedger Test Suite",
                    "email": "test@compliledger.com"
                }
            ],
            "component": {
                "type": "application",
                "bom-ref": "pkg:compliledger/test-app@1.0.0",
                "name": "Test Application",
                "version": "1.0.0"
            }
        },
        "components": [
            {
                "type": "library",
                "bom-ref": "pkg:pypi/algorand-sdk@2.0.0",
                "name": "algorand-sdk",
                "version": "2.0.0",
                "purl": "pkg:pypi/algorand-sdk@2.0.0",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/fastapi@0.95.2",
                "name": "fastapi",
                "version": "0.95.2",
                "purl": "pkg:pypi/fastapi@0.95.2",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/ipfs-api@0.7.0",
                "name": "ipfs-api",
                "version": "0.7.0",
                "purl": "pkg:pypi/ipfs-api@0.7.0",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/pydantic@1.10.8",
                "name": "pydantic",
                "version": "1.10.8",
                "purl": "pkg:pypi/pydantic@1.10.8",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/pyteal@0.20.1",
                "name": "pyteal",
                "version": "0.20.1",
                "purl": "pkg:pypi/pyteal@0.20.1",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/sqlalchemy@2.0.15",
                "name": "sqlalchemy", 
                "version": "2.0.15",
                "purl": "pkg:pypi/sqlalchemy@2.0.15",
                "licenses": [
                    {
                        "license": {
                            "id": "MIT"
                        }
                    }
                ]
            },
            {
                "type": "library",
                "bom-ref": "pkg:pypi/google-generativeai@0.2.0",
                "name": "google-generativeai",
                "version": "0.2.0",
                "purl": "pkg:pypi/google-generativeai@0.2.0",
                "licenses": [
                    {
                        "license": {
                            "id": "Apache-2.0"
                        }
                    }
                ]
            }
        ]
    }

if __name__ == "__main__":
    asyncio.run(test_e2e_flow())
