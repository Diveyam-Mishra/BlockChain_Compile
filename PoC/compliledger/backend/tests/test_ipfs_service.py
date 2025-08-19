#!/usr/bin/env python3
"""
Test for IPFS Service
Tests the functionality of the IPFS service for pinning documents to IPFS
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = SCRIPT_DIR.parent
SERVICES_DIR = BACKEND_DIR / "app" / "services"
sys.path.append(str(BACKEND_DIR))

try:
    from app.services.ipfs_service import IPFSService
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

async def test_ipfs_service():
    """
    Test IPFS service functionality
    """
    logger.info("=== Testing IPFS Service ===")
    
    # Create test data
    test_data = {
        "test": "document",
        "content": {
            "title": "Test IPFS Document",
            "version": "1.0.0",
            "items": ["item1", "item2", "item3"]
        },
        "timestamp": "2023-08-14T10:00:00Z",
    }
    
    # Create IPFS service
    try:
        ipfs_service = IPFSService()
        logger.info("IPFS Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize IPFS Service: {e}")
        return False
    
    # Test pin_json with all required parameters
    logger.info("Testing pin_json() with all required parameters")
    try:
        # All required parameters provided
        result = await ipfs_service.pin_json(
            data=test_data,
            name="test-ipfs-document",
            artifact_hash="0123456789abcdef0123456789abcdef"
        )
        
        logger.info(f"Document pinned successfully!")
        logger.info(f"IPFS CID: {result.get('ipfs_cid')}")
        logger.info(f"IPFS URL: {result.get('ipfs_url')}")
        
        # Verify the result has expected structure
        assert 'ipfs_cid' in result, "Result missing 'ipfs_cid'"
        assert 'ipfs_url' in result, "Result missing 'ipfs_url'"
        assert result['ipfs_url'].startswith("https://gateway.pinata.cloud/ipfs/"), "Invalid IPFS URL format"
        
        logger.info("✅ pin_json() test passed")
        return result
        
    except Exception as e:
        logger.error(f"Error testing pin_json(): {e}")
        return False

def run_all_tests():
    """Run all IPFS service tests"""
    logger.info("Starting IPFS Service tests")
    
    # Run the test and get the result
    result = asyncio.run(test_ipfs_service())
    
    # Print final summary
    print("\n=== IPFS Service Test Summary ===")
    if result:
        print("✅ All tests passed!")
        print(f"Sample IPFS CID: {result.get('ipfs_cid')}")
        print(f"Sample IPFS URL: {result.get('ipfs_url')}")
        
        # Print verification instructions
        print("\nTo verify the pinned document, visit:")
        print(f"{result.get('ipfs_url')}")
    else:
        print("❌ Tests failed. See logs for details.")
    
    print("\n=== End of Tests ===")
    return result is not False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
