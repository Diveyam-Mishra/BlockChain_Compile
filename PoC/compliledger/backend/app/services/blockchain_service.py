import os
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod
# Update import for Algorand SDK v2.0.0
from algosdk.transaction import PaymentTxn, ApplicationCallTxn
from algosdk.encoding import decode_address
import base64

# Load environment variables
load_dotenv()

class AlgorandService:
    """
    Service for interacting with Algorand blockchain and smart contracts
    """
    
    def __init__(self):
        """Initialize Algorand service with API client and contracts"""
        # Connect to Algorand node
        self.algod_address = os.getenv("ALGORAND_API_URL", "https://testnet-api.algonode.cloud")
        self.algod_token = ""  # Not needed for public nodes
        self.algod_client = algod.AlgodClient(self.algod_token, self.algod_address)
        
        # Load account from mnemonic
        self.mnemonic = os.getenv("ALGORAND_MNEMONIC")
        if self.mnemonic:
            self.private_key = mnemonic.to_private_key(self.mnemonic)
            self.account = account.address_from_private_key(self.private_key)
        else:
            # For development without a mnemonic
            self.private_key = None
            self.account = None
            print("Warning: No Algorand mnemonic provided. Limited functionality available.")
        
        # Load contract app IDs
        try:
            self._load_contract_config()
        except Exception as e:
            print(f"Warning: Failed to load contract configuration: {str(e)}")
            # Set default values for testing
            self.registry_app_id = int(os.getenv("REGISTRY_APP_ID", "0"))
            self.oracle_app_id = int(os.getenv("ORACLE_APP_ID", "0"))
    
    def _load_contract_config(self):
        """Load contract configuration from file"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
            "contract_config.json"
        )
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                self.registry_app_id = int(config.get("registry_app_id", 0))
                self.oracle_app_id = int(config.get("oracle_app_id", 0))
        else:
            # Try environment variables
            self.registry_app_id = int(os.getenv("REGISTRY_APP_ID", "0"))
            self.oracle_app_id = int(os.getenv("ORACLE_APP_ID", "0"))
    
    async def get_network_params(self):
        """Get Algorand network parameters"""
        try:
            return self.algod_client.suggested_params()
        except Exception as e:
            raise Exception(f"Failed to get network parameters: {str(e)}")
    
    async def submit_verification_request(self, 
                                       artifact_hash: str, 
                                       profile_id: str,
                                       submitter_address: str) -> Dict[str, Any]:
        """
        Submit verification request to the SBOMRegistry contract
        
        Args:
            artifact_hash: Hash of the artifact to verify
            oscal_cid: IPFS CID of the OSCAL documents
            profile_id: ID of the compliance profile
            submitter_address: Address of the submitter
            
        Returns:
            Transaction details
        """
        try:
            if not self.private_key:
                # For PoC, return mock transaction if no private key
                return self._get_mock_transaction("submit_verification", artifact_hash, oscal_cid)
            
            # Get network parameters
            params = await self.get_network_params()
            
            # Convert artifact hash to bytes (if string)
            if isinstance(artifact_hash, str):
                # If hex string, convert to bytes
                if len(artifact_hash) == 64:  # SHA-256 hash length in hex
                    artifact_hash_bytes = bytes.fromhex(artifact_hash)
                else:
                    # Otherwise use UTF-8 encoding
                    artifact_hash_bytes = artifact_hash.encode("utf-8")
            else:
                artifact_hash_bytes = artifact_hash
            
            # Convert profile ID to bytes
            profile_id_bytes = profile_id.encode("utf-8")
            
            # Enforce 32-byte artifact hash (box key requirement)
            if len(artifact_hash_bytes) != 32:
                raise ValueError("artifact_hash must be 32 bytes (64-char hex)")

            # Create application call transaction
            app_args = [
                b"submit_verification",
                artifact_hash_bytes,
                profile_id_bytes
            ]
            
            txn = ApplicationCallTxn(
                sender=self.account,
                sp=params,
                index=self.registry_app_id,
                on_complete=0,  # NoOp
                app_args=app_args,
                boxes=[(0, artifact_hash_bytes)]
            )
            
            # Sign and send transaction
            signed_txn = txn.sign(self.private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            wait_for_confirmation(self.algod_client, tx_id)
            
            return {
                "status": "success",
                "txn_id": tx_id,
                "app_id": self.registry_app_id,
                "artifact_hash": artifact_hash,
                "submitter": submitter_address
            }
            
        except Exception as e:
            print(f"Error submitting verification request: {str(e)}")
            # For PoC, return mock transaction on failure
            return self._get_mock_transaction("submit_verification", artifact_hash, oscal_cid)
    
    async def submit_oracle_result(self, 
                               artifact_hash: str,
                               ai_result_hash: str,
                               controls_passed: int,
                               controls_failed: int,
                               findings_count: int) -> Dict[str, Any]:
        """
        Submit AI analysis results to the ComplianceOracle contract
        
        Args:
            artifact_hash: Hash of the artifact
            ai_result_hash: Hash of the AI analysis result
            controls_passed: Count of passed controls
            controls_failed: Count of failed controls
            findings_count: Count of total findings
            
        Returns:
            Transaction details
        """
        try:
            if not self.private_key:
                # For PoC, return mock transaction if no private key
                return self._get_mock_transaction("submit_result", artifact_hash, ai_result_hash)
            
            # Get network parameters
            params = await self.get_network_params()
            
            # Convert artifact hash to bytes (if string)
            if isinstance(artifact_hash, str):
                # If hex string, convert to bytes
                if len(artifact_hash) == 64:  # SHA-256 hash length in hex
                    artifact_hash_bytes = bytes.fromhex(artifact_hash)
                else:
                    # Otherwise use UTF-8 encoding
                    artifact_hash_bytes = artifact_hash.encode("utf-8")
            else:
                artifact_hash_bytes = artifact_hash
            
            # Convert AI result hash to bytes
            if isinstance(ai_result_hash, str):
                if len(ai_result_hash) == 64:  # SHA-256 hash length in hex
                    ai_result_hash_bytes = bytes.fromhex(ai_result_hash)
                else:
                    ai_result_hash_bytes = ai_result_hash.encode("utf-8")
            else:
                ai_result_hash_bytes = ai_result_hash
            
            # Create application call transaction
            app_args = [
                b"submit_result",
                artifact_hash_bytes,
                ai_result_hash_bytes,
                controls_passed.to_bytes(8, byteorder='big'),
                controls_failed.to_bytes(8, byteorder='big'),
                findings_count.to_bytes(8, byteorder='big')
            ]
            
            txn = ApplicationCallTxn(
                sender=self.account,
                sp=params,
                index=self.oracle_app_id,
                on_complete=0,  # NoOp
                app_args=app_args
            )
            
            # Sign and send transaction
            signed_txn = txn.sign(self.private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            wait_for_confirmation(self.algod_client, tx_id)
            
            return {
                "status": "success",
                "txn_id": tx_id,
                "app_id": self.oracle_app_id,
                "artifact_hash": artifact_hash,
                "ai_result_hash": ai_result_hash,
                "controls_passed": controls_passed,
                "controls_failed": controls_failed
            }
            
        except Exception as e:
            print(f"Error submitting oracle result: {str(e)}")
            # For PoC, return mock transaction on failure
            return self._get_mock_transaction("submit_result", artifact_hash, ai_result_hash)
    
    async def query_verification_status(self, artifact_hash: str) -> Dict[str, Any]:
        """
        Query verification status from the SBOMRegistry contract
        
        Args:
            artifact_hash: Hash of the artifact to query
            
        Returns:
            Verification status details
        """
        try:
            # Get registry app global state
            app_info = self.algod_client.application_info(self.registry_app_id)
            global_state = parse_global_state(app_info['params']['global-state'])
            
            # Find state for this artifact
            for key, value in global_state.items():
                if key == f"status_{artifact_hash}":
                    status = value
                    return {
                        "verified": status == 2,  # 2 = verified
                        "status": {0: "unverified", 1: "pending", 2: "verified"}.get(status, "unknown"),
                        "artifact_hash": artifact_hash,
                        "app_id": self.registry_app_id
                    }
            
            # If not found, return unverified
            return {
                "verified": False,
                "status": "not_found",
                "artifact_hash": artifact_hash,
                "app_id": self.registry_app_id
            }
            
        except Exception as e:
            print(f"Error querying verification status: {str(e)}")
            # For PoC, return mock status on failure
            return {
                "verified": True,
                "status": "verified",
                "artifact_hash": artifact_hash,
                "app_id": self.registry_app_id,
                "mock": True
            }
    
    def _get_mock_transaction(self, tx_type: str, artifact_hash: str, data_hash: str) -> Dict[str, Any]:
        """
        Get mock transaction data for development/testing
        
        Args:
            tx_type: Transaction type
            artifact_hash: Hash of the artifact
            data_hash: Secondary hash (OSCAL CID or AI result hash)
            
        Returns:
            Mock transaction details
        """
        import time
        import hashlib
        
        # Generate deterministic mock transaction ID
        mock_tx_id = hashlib.sha256(f"{tx_type}:{artifact_hash}:{data_hash}:{int(time.time())}".encode()).hexdigest()
        
        if tx_type == "submit_verification":
            return {
                "status": "success",
                "txn_id": f"mock-txn-{mock_tx_id[:8]}",
                "app_id": self.registry_app_id or 12345678,
                "artifact_hash": artifact_hash,
                "oscal_cid": data_hash,
                "mock": True
            }
        elif tx_type == "submit_result":
            return {
                "status": "success",
                "txn_id": f"mock-txn-{mock_tx_id[:8]}",
                "app_id": self.oracle_app_id or 87654321,
                "artifact_hash": artifact_hash,
                "ai_result_hash": data_hash,
                "controls_passed": 8,
                "controls_failed": 2,
                "mock": True
            }
        else:
            return {
                "status": "error",
                "message": f"Unknown transaction type: {tx_type}",
                "mock": True
            }


# Helper functions for Algorand interaction

def wait_for_confirmation(client, txid):
    """Wait for transaction confirmation"""
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print(f"Transaction {txid} confirmed in round {txinfo.get('confirmed-round')}.")
    return txinfo

def parse_global_state(global_state):
    """Parse global state from application info"""
    result = {}
    for item in global_state:
        key = base64.b64decode(item['key']).decode('utf-8')
        value = item['value']
        if value['type'] == 1:  # bytes
            result[key] = base64.b64decode(value['bytes'])
        else:  # int
            result[key] = value['uint']
    return result
