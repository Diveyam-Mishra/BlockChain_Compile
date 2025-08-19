#!/usr/bin/env python3
"""
API Integration Test for CompliLedger Blockchain Integration Endpoint
Tests the /api/v1/verification/blockchain-integration endpoint

This test:
1. Creates a sample SBOM
2. Processes it through AI analysis
3. Submits it to the blockchain integration API endpoint
4. Validates the response
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
import httpx
import uuid
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

# Import required services for local testing
try:
    from backend.app.services.ai_service import AIService, AnalysisLevel
    logger.info("Successfully imported required services")
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

# Configuration
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v1"

async def test_api_integration():
    """
    Test the blockchain integration API endpoint
    """
    logger.info("Starting API Integration Test")
    
    # 1. Create a sample SBOM
    logger.info("Creating sample SBOM for testing")
    sbom_data = create_sample_sbom()
    sbom_json = json.dumps(sbom_data)
    artifact_hash = hashlib.sha256(sbom_json.encode()).hexdigest()
    
    # 2. Run AI analysis
    logger.info("Running AI analysis on sample SBOM")
    try:
        ai_service = AIService()
        # Create a temporary file path for SBOM
        temp_path = "/tmp/test_sbom.json"
        with open(temp_path, "w") as f:
            f.write(sbom_json)
            
        # Create metadata dictionary
        metadata = {
            "type": "sbom",
            "format": "cyclonedx",
            "name": "API Test SBOM",
            "description": "Test SBOM for API integration"
        }
        
        # Call analyze_artifact with correct parameters
        analysis_result = await ai_service.analyze_artifact(
            artifact_path=temp_path,
            metadata=metadata,
            level=AnalysisLevel.ADVANCED
        )
        logger.info(f"AI analysis completed with score: {analysis_result.get('compliance_score')}")
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}")
        return False
    
    # 3. Prepare submission to blockchain integration endpoint
    artifact_data = {
        "hash": artifact_hash,
        "name": "API Test SBOM",
        "description": "Test SBOM for API integration",
        "type": "sbom",
        "format": "cyclonedx",
        "content": sbom_json,
        "analysis_results": analysis_result
    }
    
    # 4. Submit to API
    logger.info("Submitting to blockchain integration API endpoint")
    try:
        # Increase timeout to allow AI + IPFS + blockchain to complete
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Send JSON payload matching FastAPI route (Body params)
            payload = {
                'artifact_data': artifact_data,
                'profile_id': 'default'
            }
            response = await client.post(
                f"{API_BASE_URL}/verification/blockchain-integration",
                json=payload
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"API integration successful: {json.dumps(result, indent=2)}")
                
                # Validate response
                assert result["status"] == "success", "Response status should be success"
                assert result["artifact_hash"] == artifact_hash, "Artifact hash mismatch"
                assert "oscal_cid" in result, "Missing OSCAL CID in response"
                assert "oscal_url" in result, "Missing OSCAL URL in response"
                assert "compliance_score" in result, "Missing compliance score in response"
                
                logger.info("All validation checks passed!")
                return True
            else:
                logger.error(f"API request failed with status code {response.status_code}")
                logger.error(f"Error: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"API integration test failed: {str(e)}")
        return False

def create_sample_sbom():
    """Create a realistic sample SBOM for testing"""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{str(uuid.uuid4())}",
        "version": 1,
        "metadata": {
            "timestamp": "2023-10-15T08:30:00Z",
            "tools": [
                {
                    "vendor": "CompliLedger",
                    "name": "SBOM Generator",
                    "version": "1.0.0"
                }
            ],
            "authors": [
                {
                    "name": "CompliLedger Team",
                    "email": "team@compliledger.com"
                }
            ]
        },
        "components": [
            {
                "type": "library",
                "bom-ref": "pkg:npm/lodash@4.17.21",
                "name": "lodash",
                "version": "4.17.21",
                "purl": "pkg:npm/lodash@4.17.21",
                "description": "Lodash modular utilities."
            },
            {
                "type": "library",
                "bom-ref": "pkg:npm/axios@0.27.2",
                "name": "axios",
                "version": "0.27.2",
                "purl": "pkg:npm/axios@0.27.2",
                "description": "Promise based HTTP client for the browser and node.js"
            },
            {
                "type": "library",
                "bom-ref": "pkg:npm/react@18.2.0",
                "name": "react",
                "version": "18.2.0",
                "purl": "pkg:npm/react@18.2.0",
                "description": "React is a JavaScript library for building user interfaces."
            }
        ],
        "dependencies": [
            {
                "ref": "pkg:npm/lodash@4.17.21",
                "dependsOn": []
            },
            {
                "ref": "pkg:npm/axios@0.27.2",
                "dependsOn": []
            },
            {
                "ref": "pkg:npm/react@18.2.0",
                "dependsOn": []
            }
        ]
    }

async def main():
    """Main function to run the test"""
    success = await test_api_integration()
    if success:
        logger.info("✅ API integration test passed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ API integration test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
