#!/usr/bin/env python3

import base64
from algosdk.v2client import algod
from algosdk import account, mnemonic, transaction
from algosdk.transaction import ApplicationCreateTxn, ApplicationCallTxn, ApplicationOptInTxn
from algosdk import encoding as algo_encoding
import time
import json

class SBOMRegistryClient:
    def __init__(self, algod_client, private_key, app_id=None):
        """Initialize SBOM Registry client"""
        self.algod_client = algod_client
        self.private_key = private_key
        self.address = account.address_from_private_key(private_key)
        self.app_id = app_id
    
    def compile_program(self, source_code):
        """Compile TEAL source code to binary"""
        compile_response = self.algod_client.compile(source_code)
        return base64.b64decode(compile_response['result'])
    
    def wait_for_confirmation(self, txid, timeout=20):
        """Wait for transaction confirmation"""
        start_round = self.algod_client.status()["last-round"] + 1
        current_round = start_round

        while current_round < start_round + timeout:
            try:
                pending_txn = self.algod_client.pending_transaction_info(txid)
            except Exception:
                return {"confirmed-round": 0, "pool-error": "Transaction not found"}
            
            if pending_txn.get("confirmed-round", 0) > 0:
                return pending_txn
            
            if pending_txn.get("pool-error"):
                # Try to attach any logs for easier debugging
                logs = pending_txn.get("logs") or []
                try:
                    import base64 as _b64
                    decoded_logs = [ _b64.b64decode(l).decode(errors="ignore") for l in logs ]
                except Exception:
                    decoded_logs = []
                raise Exception(f"Pool error: {pending_txn['pool-error']} | logs: {decoded_logs}")
            
            self.algod_client.status_after_block(current_round)
            current_round += 1
            
        raise Exception(f"Transaction {txid} not confirmed after {timeout} rounds")
    
    def deploy_contract(self, approval_source, clear_source):
        """Deploy the SBOM Registry contract"""
        print("Deploying SBOM Registry contract...")
        
        # Compile programs
        approval_program = self.compile_program(approval_source)
        clear_program = self.compile_program(clear_source)
        
        # Get network params
        params = self.algod_client.suggested_params()
        # Box ops require higher fee; use flat fee
        params.flat_fee = True
        try:
            min_fee = getattr(params, 'min_fee', 1000)
            params.fee = max(min_fee * 3, 4000)
        except Exception:
            params.fee = 4000
        # Cover inner transaction fee: outer tx must pay for inner tx min fee
        params.flat_fee = True
        try:
            # If there is 1 inner tx, pay at least 2x min fee
            min_fee = getattr(params, 'min_fee', 1000)
            params.fee = max(min_fee * 2, 2000)
        except Exception:
            params.fee = 2000
        
        # Create application transaction
        txn = ApplicationCreateTxn(
            sender=self.address,
            sp=params,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program,
            clear_program=clear_program,
            global_schema=transaction.StateSchema(5, 15),  # 5 integers + 15 byte-slices
            local_schema=transaction.StateSchema(0, 0)    # No local state
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        self.app_id = confirmed_txn["application-index"]
        
        print(f"Contract deployed! App ID: {self.app_id}")
        return self.app_id
    
    def set_oracle(self, oracle_address):
        """Set the oracle address for the SBOM Registry contract.
        Accepts a base32 Algorand address string or 32-byte public key bytes.
        """
        if isinstance(oracle_address, str):
            oracle_address_bytes = algo_encoding.decode_address(oracle_address)
        else:
            oracle_address_bytes = oracle_address
        print("Setting oracle address to:", algo_encoding.encode_address(oracle_address_bytes))
        
        params = self.algod_client.suggested_params()
        
        # Create application call transaction
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[b"set_oracle", oracle_address_bytes]
        )
        
        # Sign and send
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        print(f"Oracle address set successfully")
        return confirmed_txn

    def update_verification(self, artifact_hash, status:int, oscal_cid:str):
        """Oracle-only update of verification record in box.
        Caller must be set as oracle in registry contract.
        """
        print(f"Updating verification for {artifact_hash} to status={status}, oscal_cid={oscal_cid}")
        params = self.algod_client.suggested_params()
        # Ensure sufficient fee for box replace operations
        params.flat_fee = True
        try:
            min_fee = getattr(params, 'min_fee', 1000)
            params.fee = max(min_fee * 10, 10000)
        except Exception:
            params.fee = 10000
        box_name = bytes.fromhex(artifact_hash) if not isinstance(artifact_hash, bytes) else artifact_hash
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                b"update_verification",
                box_name,
                oscal_cid.encode(),
                status.to_bytes(8, byteorder='big')
            ],
            boxes=[(0, box_name)]
        )
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        confirmed_txn = self.wait_for_confirmation(tx_id)
        print("Update submitted successfully")
        return {"tx_id": tx_id, "confirmation": confirmed_txn}
    
    def register_artifact(self, artifact_hash, profile_id="default"):
        """Register an artifact for verification"""
        print(f"Registering artifact with hash: {artifact_hash}")
        
        params = self.algod_client.suggested_params()
        # Ensure sufficient fee for box create
        params.flat_fee = True
        try:
            min_fee = getattr(params, 'min_fee', 1000)
            params.fee = max(min_fee * 10, 10000)
        except Exception:
            params.fee = 10000
        
        # Create application call transaction
        # Box name is the artifact hash (32-byte). Use current app id = 0 per SDK semantics.
        box_name = bytes.fromhex(artifact_hash) if not isinstance(artifact_hash, bytes) else artifact_hash
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                b"submit_verification", 
                box_name,
                profile_id.encode()
            ],
            boxes=[(0, box_name)]
        )
        
        # Sign and send
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        print(f"Artifact registered successfully")
        # Return tx id along with confirmation for upstream logging
        return {"tx_id": tx_id, "confirmation": confirmed_txn}
    
    def query_verification_status(self, artifact_hash):
        """Query verification status of an artifact"""
        print(f"Querying verification status for: {artifact_hash}")
        
        params = self.algod_client.suggested_params()
        
        # Create application call transaction
        box_name = bytes.fromhex(artifact_hash) if not isinstance(artifact_hash, bytes) else artifact_hash
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                b"query_verification",
                box_name
            ],
            boxes=[(0, box_name)]
        )
        
        # Sign and send
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        
        # Status code: 0=Pending, 1=Verified, 2=Failed
        status_code = 0  # Default to pending
        
        # Prefer parsing from logs (contract now logs the 8-byte status value)
        try:
            logs = confirmed_txn.get("logs", []) or []
            if logs:
                # Base64 decode first log entry; treat as 8-byte big-endian int
                import base64 as _b64
                raw = _b64.b64decode(logs[0])
                if isinstance(raw, (bytes, bytearray)) and len(raw) >= 8:
                    status_code = int.from_bytes(raw[:8], byteorder="big")
        except Exception:
            # Fallback to legacy return-value if present
            try:
                status_code = int(confirmed_txn.get("return-value", "0"), 16)
            except Exception:
                pass
        
        status_text = "Pending" if status_code == 0 else "Verified" if status_code == 1 else "Failed"
        print(f"Verification status: {status_code} ({status_text})")
        
        return status_code
    
    def get_contract_state(self):
        """Get the global state of the SBOM Registry contract"""
        try:
            app_info = self.algod_client.application_info(self.app_id)
            global_state = app_info['params']['global-state']
            
            state_dict = {}
            for item in global_state:
                raw_key = base64.b64decode(item['key'])
                try:
                    key = raw_key.decode('utf-8')
                except Exception:
                    key = raw_key.hex()
                value = item['value']
                
                if value['type'] == 1:  # Byte slice
                    try:
                        # Try to decode as string
                        val = base64.b64decode(value['bytes']).decode('utf-8')
                    except Exception:
                        # If it fails, use hex representation
                        val = base64.b64decode(value['bytes']).hex()
                else:  # Integer
                    val = value['uint']
                
                state_dict[key] = val
            
            return state_dict
        except Exception as e:
            print(f"Error getting contract state: {e}")
            return {}


class ComplianceOracleClient:
    def __init__(self, algod_client, private_key, app_id=None):
        """Initialize Compliance Oracle client"""
        self.algod_client = algod_client
        self.private_key = private_key
        self.address = account.address_from_private_key(private_key)
        self.app_id = app_id
    
    def compile_program(self, source_code):
        """Compile TEAL source code to binary"""
        compile_response = self.algod_client.compile(source_code)
        return base64.b64decode(compile_response['result'])
    
    def wait_for_confirmation(self, txid, timeout=20):
        """Wait for transaction confirmation"""
        start_round = self.algod_client.status()["last-round"] + 1
        current_round = start_round

        while current_round < start_round + timeout:
            try:
                pending_txn = self.algod_client.pending_transaction_info(txid)
            except Exception:
                return {"confirmed-round": 0, "pool-error": "Transaction not found"}
            
            if pending_txn.get("confirmed-round", 0) > 0:
                return pending_txn
            
            if pending_txn.get("pool-error"):
                raise Exception(f"Pool error: {pending_txn['pool-error']}")
            
            self.algod_client.status_after_block(current_round)
            current_round += 1
            
        raise Exception(f"Transaction {txid} not confirmed after {timeout} rounds")
    
    def deploy_contract(self, approval_source, clear_source):
        """Deploy the Compliance Oracle contract"""
        print("Deploying Compliance Oracle contract...")
        
        # Compile programs
        approval_program = self.compile_program(approval_source)
        clear_program = self.compile_program(clear_source)
        
        # Get network params
        params = self.algod_client.suggested_params()
        
        # Create application transaction
        txn = ApplicationCreateTxn(
            sender=self.address,
            sp=params,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program,
            clear_program=clear_program,
            global_schema=transaction.StateSchema(5, 5),   # 5 integers + 5 byte-slices
            local_schema=transaction.StateSchema(0, 0)    # No local state
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        self.app_id = confirmed_txn["application-index"]
        
        print(f"Contract deployed! App ID: {self.app_id}")
        return self.app_id
    
    def set_registry(self, registry_app_id):
        """Set the registry app ID for the Compliance Oracle contract"""
        print(f"Setting registry app ID to: {registry_app_id}")
        
        params = self.algod_client.suggested_params()
        
        # Create application call transaction
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                b"set_registry", 
                registry_app_id.to_bytes(8, byteorder='big')
            ]
        )
        
        # Sign and send
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        print(f"Registry app ID set successfully")
        return confirmed_txn
    
    def submit_result(self, result_hash, artifact_hash, controls_passed, controls_failed, oscal_cid, registry_app_id=None):
        """Submit analysis results to the Compliance Oracle
        Optionally provide registry_app_id; if not provided, read from Oracle state.
        """
        print(f"Submitting analysis results for artifact: {artifact_hash}")
        print(f"Controls: {controls_passed} passed, {controls_failed} failed")
        print(f"OSCAL CID: {oscal_cid}")
        
        # Resolve Registry App ID for foreign apps
        rid = registry_app_id
        if rid is None:
            try:
                state = self.get_contract_state()
                rid = state.get('registry_app_id')
            except Exception:
                rid = None
        
        params = self.algod_client.suggested_params()
        # Ensure the outer app call fee covers the inner transaction fee
        params.flat_fee = True
        try:
            min_fee = getattr(params, 'min_fee', 1000)
            params.fee = max(min_fee * 2, 2000)
        except Exception:
            params.fee = 2000
        
        # Build kwargs to include foreign apps only if available
        call_kwargs = {}
        if isinstance(rid, int) and rid > 0:
            call_kwargs['foreign_apps'] = [rid]
        
        # Create application call transaction
        txn = ApplicationCallTxn(
            sender=self.address,
            sp=params,
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                b"submit_result",
                bytes.fromhex(result_hash) if not isinstance(result_hash, bytes) else result_hash,
                bytes.fromhex(artifact_hash) if not isinstance(artifact_hash, bytes) else artifact_hash,
                controls_passed.to_bytes(8, byteorder='big'),
                controls_failed.to_bytes(8, byteorder='big'),
                oscal_cid.encode()
            ],
            **call_kwargs
        )
        
        # Sign and send
        signed_txn = txn.sign(self.private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = self.wait_for_confirmation(tx_id)
        print(f"Analysis results submitted successfully")
        # Return tx id along with confirmation for upstream logging
        return {"tx_id": tx_id, "confirmation": confirmed_txn}
    
    def get_contract_state(self):
        """Get the global state of the Compliance Oracle contract"""
        try:
            app_info = self.algod_client.application_info(self.app_id)
            global_state = app_info['params']['global-state']
            
            state_dict = {}
            for item in global_state:
                raw_key = base64.b64decode(item['key'])
                try:
                    key = raw_key.decode('utf-8')
                except Exception:
                    key = raw_key.hex()
                value = item['value']
                
                if value['type'] == 1:  # Byte slice
                    try:
                        # Try to decode as string
                        val = base64.b64decode(value['bytes']).decode('utf-8')
                    except Exception:
                        # If it fails, use hex representation
                        val = base64.b64decode(value['bytes']).hex()
                else:  # Integer
                    val = value['uint']
                
                state_dict[key] = val
            
            return state_dict
        except Exception as e:
            print(f"Error getting contract state: {e}")
            return {}
