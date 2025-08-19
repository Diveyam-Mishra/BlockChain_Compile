#!/usr/bin/env python3

import os
import sys
import json
import uuid
import time
import hashlib
import logging
import asyncio
import datetime
from pathlib import Path

# Import Algorand SDK
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import transaction
from algosdk.logic import get_application_address
from algosdk import transaction
import certifi
import ssl
import urllib.request

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent
sys.path.append(str(ROOT_DIR))

# Import backend services
from backend.app.services.ipfs_service import IPFSService

# Import contract clients (using relative import to fix ModuleNotFoundError)
from . import compliledger_clients
from .compliledger_clients import SBOMRegistryClient, ComplianceOracleClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContractIntegrationService:
    """
    Service to integrate backend services (OSCAL, IPFS, AI) with deployed Algorand contracts
    """
    def __init__(self):
        # Connect to Algorand node
        self.algod_address = os.getenv("ALGORAND_API_URL", "https://testnet-api.algonode.cloud")
        self.algod_token = ""  # Not needed for public nodes
        # Configure global HTTPS context to use certifi CA bundle (fixes SSL verification on macOS)
        try:
            os.environ.setdefault('SSL_CERT_FILE', certifi.where())
            ctx = ssl.create_default_context(cafile=certifi.where())
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            urllib.request.install_opener(opener)
        except Exception as _ssl_e:
            logger.warning(f"Could not install custom SSL context, proceeding with defaults: {_ssl_e}")
        self.algod_client = algod.AlgodClient(self.algod_token, self.algod_address)
        
        # Load account from mnemonic
        self.mnemonic = os.getenv("ALGORAND_MNEMONIC")
        if not self.mnemonic:
            # Try to load from file for testing
            config_path = os.path.join(os.path.dirname(__file__), "contract_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.mnemonic = config.get("mnemonic")
        
        # Setup account
        if self.mnemonic:
            self.private_key = mnemonic.to_private_key(self.mnemonic)
            self.account = account.address_from_private_key(self.private_key)
        else:
            # For development without a mnemonic
            self.private_key = None
            self.account = None
            logger.warning("No Algorand mnemonic provided. Limited functionality available.")
        
        # Load contract app IDs
        try:
            self._load_contract_config()
        except Exception as e:
            logger.warning(f"Failed to load contract configuration: {str(e)}")
            # Set default values for testing
            self.registry_app_id = int(os.getenv("REGISTRY_APP_ID", "0"))
            self.oracle_app_id = int(os.getenv("ORACLE_APP_ID", "0"))
        
        # Create contract clients
        if self.registry_app_id > 0 and self.oracle_app_id > 0 and self.private_key:
            self.registry_client = SBOMRegistryClient(self.algod_client, self.private_key, self.registry_app_id)
            self.oracle_client = ComplianceOracleClient(self.algod_client, self.private_key, self.oracle_app_id)
            logger.info(f"Contract clients initialized with Registry ID: {self.registry_app_id}, Oracle ID: {self.oracle_app_id}")
            # Ensure oracle is linked to the current registry
            try:
                logger.info(f"Ensuring oracle is linked to registry {self.registry_app_id}")
                self.oracle_client.set_registry(self.registry_app_id)
                logger.info("Oracle linked to registry successfully")
                # Ensure registry knows the EOA oracle address (so backend can update directly)
                try:
                    logger.info(f"Setting registry oracle_address to EOA signer: {self.account}")
                    self.registry_client.set_oracle(self.account)
                    logger.info("Registry oracle_address set successfully")
                except Exception as _inner:
                    logger.warning(f"Could not set registry oracle_address automatically: {_inner}")
            except Exception as e:
                logger.warning(f"Could not link oracle to registry automatically: {e}")
        else:
            logger.warning("Contract clients not initialized - missing app IDs or private key")
            self.registry_client = None
            self.oracle_client = None
            
        # Initialize IPFS service for real storage (no more mocking)
        try:
            self.ipfs_service = IPFSService()
            logger.info("IPFS service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize IPFS service: {str(e)}")
            self.ipfs_service = None
            
    def _load_contract_config(self):
        """Load contract configuration from file"""
        config_path = os.path.join(os.path.dirname(__file__), "contract_config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                self.registry_app_id = int(config.get("registry_app_id", 0))
                self.oracle_app_id = int(config.get("oracle_app_id", 0))
        else:
            # Try environment variables
            self.registry_app_id = int(os.getenv("REGISTRY_APP_ID", "0"))
            self.oracle_app_id = int(os.getenv("ORACLE_APP_ID", "0"))
    
    async def process_artifact(self, artifact_data, profile_id="default"):
        """
        Process an artifact through the entire pipeline:
        1. Generate mock OSCAL documents (simplified for contract testing)
        2. Generate mock IPFS CID (simplified for contract testing)
        3. Register on Algorand blockchain
        4. Submit for AI analysis (mock)
        5. Update verification status
        
        Args:
            artifact_data: Dictionary containing artifact data
            profile_id: ID of the compliance profile to use
            
        Returns:
            Dictionary with processing results
        """
        try:
            # 1. Calculate artifact hash (should be included in artifact_data)
            artifact_hash = artifact_data.get("hash")
            if not artifact_hash:
                raise ValueError("Artifact hash is required")
            
            logger.info(f"Processing artifact with hash: {artifact_hash}")
            
            # 2. Generate OSCAL component definition
            logger.info("Generating OSCAL component definition")
            initial_analysis = {"compliance_score": artifact_data.get("analysis_results", {}).get("compliance_score", 0), "findings": []}
            oscal_document = self._generate_oscal(artifact_data, initial_analysis)
            
            # 3. Store OSCAL document on real IPFS
            logger.info("Storing initial OSCAL document on IPFS")
            if self.ipfs_service:
                oscal_response = await self.ipfs_service.pin_json(
                    data=oscal_document,
                    name=f"oscal-initial-{artifact_hash[:8]}",
                    artifact_hash=artifact_hash
                )
                oscal_cid = oscal_response.get("ipfs_cid")
                logger.info(f"OSCAL document stored on IPFS with CID: {oscal_cid}")
            else:
                # Fallback only if IPFS service initialization failed
                oscal_cid = hashlib.sha256(f"{artifact_hash}-oscal".encode()).hexdigest()[:16]
                logger.warning("Using fallback hash for OSCAL CID (IPFS service unavailable)")

            
            # 4. Ensure registry app address is funded for box storage, then register artifact on blockchain
            registry_tx_id = None
            registry_tx_explorer = None
            if self.registry_client:
                try:
                    app_addr = get_application_address(self.registry_app_id)
                    acct = self.algod_client.account_info(app_addr)
                    balance = acct.get("amount", 0)
                except Exception:
                    balance = 0

                # Fund if balance < 800000 microAlgos (0.8 ALGO) to cover box min-balance comfortably
                if balance < 800000:
                    try:
                        params = self.algod_client.suggested_params()
                        pay_txn = transaction.PaymentTxn(
                            sender=self.account,
                            sp=params,
                            receiver=app_addr,
                            amt=1000000  # 1.0 ALGO buffer for box storage
                        )
                        signed = pay_txn.sign(self.private_key)
                        txid = self.algod_client.send_transaction(signed)
                        # Wait for confirmation lightly
                        start = self.algod_client.status()["last-round"]
                        while True:
                            info = self.algod_client.pending_transaction_info(txid)
                            if info.get("confirmed-round", 0) > 0:
                                break
                            self.algod_client.status_after_block(start + 1)
                            start += 1
                        logger.info("Funded registry app address for box storage")
                    except Exception as _e:
                        logger.warning(f"Could not fund app address automatically: {_e}")

                # Check if box already exists; if so, skip registration to avoid BoxCreate assert
                box_exists = False
                try:
                    box_name = bytes.fromhex(artifact_hash)
                    _ = self.algod_client.application_box_by_name(self.registry_app_id, box_name)
                    box_exists = True
                except Exception:
                    box_exists = False

                if box_exists:
                    logger.info("Artifact box already exists; skipping registration")
                    tx_result = {"tx_id": None}
                else:
                    logger.info(f"Registering artifact on blockchain with hash: {artifact_hash}")
                    tx_result = self.registry_client.register_artifact(artifact_hash, profile_id)
                try:
                    registry_tx_id = tx_result.get("tx_id") if isinstance(tx_result, dict) else None
                except Exception:
                    registry_tx_id = None
                if registry_tx_id:
                    registry_tx_explorer = f"https://testnet.explorer.perawallet.app/tx/{registry_tx_id}"
                    logger.info(f"Artifact registered on chain. Tx: {registry_tx_id} | {registry_tx_explorer}")
                else:
                    logger.info("Artifact registered on chain")
            else:
                logger.warning("Registry client not available - skipping blockchain registration")
            
            # 5. Use actual analysis results from artifact_data
            logger.info("Processing AI analysis results")
            analysis_results = artifact_data.get("analysis_results", {})
            result_hash = hashlib.sha256(f"{artifact_hash}-{time.time()}".encode()).hexdigest()[:32]
            
            # Optimize integer storage by using fewer integer values
            controls_passed = analysis_results.get("controls_passed", 0)
            controls_failed = analysis_results.get("controls_failed", 0)
            compliance_score = analysis_results.get("compliance_score", 0)
            findings_count = analysis_results.get("findings_count", 0)
            
            # 6. Generate verified OSCAL document with real analysis
            logger.info("Generating verified OSCAL document with analysis results")
            updated_oscal = self._generate_oscal(artifact_data, analysis_results, verified=True)
            
            # 7. Store verified OSCAL on real IPFS
            logger.info("Storing verified OSCAL document on IPFS")
            if self.ipfs_service:
                verified_response = await self.ipfs_service.pin_json(
                    data=updated_oscal,
                    name=f"oscal-verified-{artifact_hash[:8]}",
                    artifact_hash=artifact_hash
                )
                verified_oscal_cid = verified_response.get("ipfs_cid")
                verified_oscal_url = verified_response.get("ipfs_url")
                logger.info(f"Verified OSCAL stored on IPFS with CID: {verified_oscal_cid}")
            else:
                # Fallback only if IPFS service initialization failed
                verified_oscal_cid = hashlib.sha256(f"{artifact_hash}-verified".encode()).hexdigest()[:16]
                verified_oscal_url = f"https://gateway.pinata.cloud/ipfs/{verified_oscal_cid}"
                logger.warning("Using fallback hash for verified OSCAL CID (IPFS service unavailable)")
            
            # 8. Update registry directly with verification status (EOA oracle)
            oracle_tx_id = None
            oracle_tx_explorer = None
            # Compute verification status: 1 = pass (no failures), 2 = fail (some failures)
            verification_status = 1 if controls_failed == 0 else 2
            if self.registry_client:
                try:
                    txr = self.registry_client.update_verification(
                        artifact_hash,
                        verification_status,
                        verified_oscal_cid
                    )
                    try:
                        rid = txr.get("tx_id") if isinstance(txr, dict) else None
                    except Exception:
                        rid = None
                    if rid:
                        logger.info(f"Registry updated with verification status. Tx: {rid} | https://testnet.explorer.perawallet.app/tx/{rid}")
                    else:
                        logger.info("Registry updated with verification status")
                except Exception as e:
                    logger.error(f"Error updating registry with verification status: {e}")
            # 9. Optionally submit to oracle for logging/forwarding
            if self.oracle_client:
                logger.info("Submitting verification result to oracle")
                # Derive a stable result hash if not provided by analysis layer
                try:
                    result_hash = analysis_results.get("result_hash")
                except Exception:
                    result_hash = None
                if not result_hash:
                    base = f"{artifact_hash}-{verified_oscal_cid}-{analysis_results.get('compliance_score', 0)}"
                    result_hash = hashlib.sha256(base.encode()).hexdigest()[:32]
                # Use previously computed safe defaults
                controls_passed = analysis_results.get("controls_passed", controls_passed)
                controls_failed = analysis_results.get("controls_failed", controls_failed)
                
                # Submit to blockchain (oracle path optional)
                try:
                    oracle_txn = self.oracle_client.submit_result(
                        result_hash,
                        artifact_hash,
                        controls_passed,
                        controls_failed,
                        verified_oscal_cid
                    )
                    try:
                        oracle_tx_id = oracle_txn.get("tx_id") if isinstance(oracle_txn, dict) else None
                    except Exception:
                        oracle_tx_id = None
                    if oracle_tx_id:
                        oracle_tx_explorer = f"https://testnet.explorer.perawallet.app/tx/{oracle_tx_id}"
                        logger.info(f"Verification result submitted successfully. Tx: {oracle_tx_id} | {oracle_tx_explorer}")
                    else:
                        logger.info("Verification result submitted successfully")
                except Exception as e:
                    logger.error(f"Error submitting result to blockchain: {e}")
            else:
                logger.warning("Oracle client not available - skipping result submission")
            
            # Return comprehensive results
            return {
                "artifact_hash": artifact_hash,
                "profile_id": profile_id,
                "initial_oscal_cid": oscal_cid,
                "initial_oscal_url": f"https://gateway.pinata.cloud/ipfs/{oscal_cid}",
                "verified_oscal_cid": verified_oscal_cid,
                "verified_oscal_url": f"https://gateway.pinata.cloud/ipfs/{verified_oscal_cid}",
                "registry_app_id": self.registry_app_id,
                "oracle_app_id": self.oracle_app_id,
                "compliance_score": analysis_results.get("compliance_score", compliance_score),
                "controls_passed": analysis_results.get("controls_passed", controls_passed),
                "controls_failed": analysis_results.get("controls_failed", controls_failed),
                "registry_tx_id": registry_tx_id,
                "registry_tx_url": registry_tx_explorer,
                "oracle_tx_id": oracle_tx_id,
                "oracle_tx_url": oracle_tx_explorer,
                "status": "complete"
            }
            
        except Exception as e:
            logger.error(f"Error processing artifact: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "artifact_hash": artifact_data.get("hash", "unknown")
            }
    
    def _generate_oscal(self, artifact_data, analysis_results, verified=False):
        """Generate an OSCAL document from artifact and analysis data"""
        doc_uuid = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        artifact_hash = artifact_data.get("hash", "unknown")
        
        # Create a simplified OSCAL structure (not full OSCAL but with essential elements)
        return {
            "uuid": doc_uuid,
            "metadata": {
                "title": f"Compliance Assessment for {artifact_data.get('name', 'Unknown Artifact')}",
                "last-modified": timestamp,
                "version": "1.0",
                "oscal-version": "1.0.0",
                "verified": verified,
                "artifact-hash": artifact_hash
            },
            "results": {
                "score": analysis_results.get("compliance_score", 0),
                "findings": analysis_results.get("findings", []),
                "controls_passed": analysis_results.get("controls_passed", 0),
                "controls_failed": analysis_results.get("controls_failed", 0)
            }
        }
    
    def _generate_mock_cid(self, content_identifier):
        """Generate a mock IPFS CID based on content"""
        # Create a deterministic mock CID based on content
        mock_hash = hashlib.sha256(content_identifier.encode()).hexdigest()[:16]
        return f"Qm{mock_hash}MOCKCID{int(time.time()) % 1000}"

# Example usage
async def test_integration():
    # Sample artifact data
    artifact_data = {
        "name": "Sample SBOM",
        "description": "Test Software Bill of Materials",
        "type": "sbom",
        "format": "cyclonedx",
        "hash": "4efbe4768fa2182cf72a93cdab95f8a7b5637b6233302cfc2775228eab3c1ac0",
        "components": [
            {"name": "component1", "version": "1.0.0", "type": "library"},
            {"name": "component2", "version": "2.1.3", "type": "framework"}
        ]
    }
    
    # Create integration service
    service = ContractIntegrationService()
    
    # Process artifact
    result = await service.process_artifact(artifact_data)
    
    # Print results
    print("\n===== Contract Integration Test Results =====")
    print(json.dumps(result, indent=2))
    
    # Check deployment status
    print("\n===== Contract Deployment Status =====")
    print(f"Registry App ID: {service.registry_app_id}")
    print(f"Oracle App ID: {service.oracle_app_id}")
    print(f"Account: {service.account if service.account else 'Not available'}")
    
    # Print explorer links
    print("\n===== Explorer Links =====")
    print(f"Registry Contract: https://testnet.explorer.perawallet.app/application/{service.registry_app_id}/")
    print(f"Oracle Contract: https://testnet.explorer.perawallet.app/application/{service.oracle_app_id}/")

if __name__ == "__main__":
    asyncio.run(test_integration())
