#!/usr/bin/env python3

import sys
import json
import time
import hashlib
import random
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
from algosdk.error import AlgodHTTPError
from compliledger_clients import SBOMRegistryClient, ComplianceOracleClient
import os
import certifi
from algosdk.logic import get_application_address

# Constants for testing
TEST_ARTIFACT_HASH = hashlib.sha256(f"test_artifact_{random.randint(1, 1000)}".encode()).hexdigest()
TEST_RESULT_HASH = hashlib.sha256(f"test_result_{random.randint(1, 1000)}".encode()).hexdigest()
TEST_OSCAL_CID = f"QmTest{random.randint(10000, 99999)}OSCAL"
TEST_PROFILE_ID = "default_profile"

def load_contract_config(filename="contract_config.json"):
    """Load the deployed contract configuration"""
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        
        print(f"Successfully loaded contract config:")
        print(f"  Registry App ID: {config.get('registry_app_id')}")
        print(f"  Oracle App ID: {config.get('oracle_app_id')}")
        print(f"  Network: {config.get('network')}")
        return config
    except FileNotFoundError:
        print(f"Contract config file not found at {filename}")
        return None
    except Exception as e:
        print(f"Error loading contract config: {e}")
        return None

def get_algod_client(network="testnet"):
    """Create and return an Algorand client for the specified network"""
    if network == "testnet":
        algod_address = "https://testnet-api.algonode.cloud"
        algod_token = ""
    else:
        raise ValueError(f"Unsupported network: {network}")
    # Ensure TLS verification uses certifi bundle and set UA header
    try:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        pass
    headers = {"User-Agent": "py-algorand-sdk"}
    return algod.AlgodClient(algod_token, algod_address, headers=headers)

def check_account_balance(algod_client, address, mnemonic_phrase=None):
    """Check account balance and display in a user-friendly format"""
    try:
        account_info = algod_client.account_info(address)
        balance = account_info.get('amount', 0) / 1000000  # Convert microAlgos to Algos
        
        print(f"\n=== ACCOUNT BALANCE ===")
        print(f"Address: {address}")
        if mnemonic_phrase:
            print(f"Mnemonic available: Yes")
        print(f"Balance: {balance:.6f} ALGO")
        
        if balance < 0.1:
            print("⚠️  WARNING: Account has low balance!")
            print("Please fund the account with TestNet ALGOs: https://bank.testnet.algorand.network/")
            return False
        else:
            print("✓ Account has sufficient balance")
            return True
    except Exception as e:
        print(f"Error checking account balance: {e}")
        return False

def print_contract_state(client, app_id, title):
    """Print contract global state in a formatted way"""
    print(f"\n=== {title} (App ID: {app_id}) ===")
    
    try:
        state = client.get_contract_state()
        
        if not state:
            print("No state found or error retrieving state")
            return
        
        for key, value in state.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error printing contract state: {e}")

def fund_application(algod_client, funder_private_key, app_id, amount_algos=1.0):
    """Fund the application's address to cover box storage min balance."""
    sender = account.address_from_private_key(funder_private_key)
    app_addr = get_application_address(app_id)
    print(f"\n=== FUNDING APPLICATION ACCOUNT ===")
    print(f"App ID: {app_id}")
    print(f"App Address: {app_addr}")
    params = algod_client.suggested_params()
    amt = int(amount_algos * 1_000_000)
    ptxn = transaction.PaymentTxn(sender, params, app_addr, amt)
    stx = ptxn.sign(funder_private_key)
    txid = algod_client.send_transaction(stx)
    print(f"Fund tx sent: {txid}")
    # Simple wait
    start = algod_client.status()["last-round"] + 1
    for r in range(start, start + 10):
        try:
            pend = algod_client.pending_transaction_info(txid)
            if pend.get("confirmed-round", 0) > 0:
                print(f"Funding confirmed in round {pend['confirmed-round']}")
                break
        except Exception:
            pass
        algod_client.status_after_block(r)

def main():
    """Main function to test the deployed contracts"""
    print("===== CompliLedger Smart Contract Test =====\n")
    
    # Step 1: Load contract configuration
    print("\n=== STEP 1: Loading Contract Configuration ===")
    config = load_contract_config()
    if not config:
        print("Failed to load contract configuration. Exiting...")
        sys.exit(1)
    
    # Step 2: Connect to Algorand TestNet
    print("\n=== STEP 2: Connecting to Algorand TestNet ===")
    try:
        algod_client = get_algod_client(config.get('network', 'testnet'))
        status = algod_client.status()
        print(f"Connected to Algorand TestNet")
        print(f"Last round: {status.get('last-round')}")
        print(f"Version: {status.get('version')}")
    except Exception as e:
        print(f"Failed to connect to Algorand TestNet: {e}")
        sys.exit(1)
    
    # Step 3: Set up account from mnemonic
    print("\n=== STEP 3: Setting Up Account ===")
    mnemonic_phrase = "day peanut cycle shrimp bounce spend fee neglect enrich rigid manual tiger adjust ugly pigeon parrot universe river later hire clown capital extra ability found"
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    
    print(f"Using account: {address}")
    
    # Check account balance
    if not check_account_balance(algod_client, address, mnemonic_phrase):
        print("\n⚠️  Proceeding with low balance - some transactions may fail")
    
    # Step 4: Initialize clients with the deployed contract IDs
    print("\n=== STEP 4: Initializing Clients ===")
    registry_client = SBOMRegistryClient(algod_client, private_key, config.get('registry_app_id'))
    oracle_client = ComplianceOracleClient(algod_client, private_key, config.get('oracle_app_id'))
    
    print(f"Initialized SBOMRegistryClient with app ID: {registry_client.app_id}")
    print(f"Initialized ComplianceOracleClient with app ID: {oracle_client.app_id}")
    
    # Step 5: Check initial contract states
    print("\n=== STEP 5: Checking Initial Contract States ===")
    print_contract_state(registry_client, registry_client.app_id, "SBOM REGISTRY CONTRACT STATE")
    print_contract_state(oracle_client, oracle_client.app_id, "COMPLIANCE ORACLE CONTRACT STATE")
    
    # Step 6: Link contracts by setting Registry ID in Oracle and Oracle address (EOA) in Registry
    print("\n=== STEP 6: Linking Contracts ===")
    try:
        # Set Registry ID in Oracle
        oracle_client.set_registry(registry_client.app_id)
        
        # Set Oracle address in Registry to our EOA for this test
        registry_client.set_oracle(address)
    except Exception as e:
        print(f"Error linking contracts: {e}")
    
    # Fund Registry application address to cover box min balance
    try:
        fund_application(algod_client, private_key, registry_client.app_id, amount_algos=1.5)
    except Exception as e:
        print(f"Error funding application: {e}")
    
    # Step 7: Register a test artifact
    print("\n=== STEP 7: Registering Test Artifact ===")
    print(f"Artifact Hash: {TEST_ARTIFACT_HASH}")
    print(f"Profile ID: {TEST_PROFILE_ID}")
    
    try:
        registry_client.register_artifact(TEST_ARTIFACT_HASH, TEST_PROFILE_ID)
        time.sleep(2)  # Give blockchain time to update
    except AlgodHTTPError as e:
        print(f"Error registering artifact: {e}")
        if "err opcode executed" in str(e):
            print("This might be due to smart contract restrictions or incorrect parameters")
    except Exception as e:
        print(f"Error registering artifact: {e}")
    
    # Step 8: Query verification status (should be pending/0)
    print("\n=== STEP 8: Querying Initial Verification Status ===")
    try:
        status = registry_client.query_verification_status(TEST_ARTIFACT_HASH)
        print(f"Initial status: {status} ({'Pending' if status == 0 else 'Verified' if status == 1 else 'Failed'})")
    except Exception as e:
        print(f"Error querying verification status: {e}")
    
    # Step 9: Submit analysis results directly to Registry (simulating oracle)
    print("\n=== STEP 9: Submitting Analysis Results (Direct Registry Call) ===")
    print(f"Result Hash: {TEST_RESULT_HASH}")
    print(f"Controls Passed: 8, Controls Failed: 0")
    print(f"OSCAL CID: {TEST_OSCAL_CID}")
    try:
        registry_client.update_verification(
            TEST_ARTIFACT_HASH,
            1,  # Verified
            TEST_OSCAL_CID
        )
        time.sleep(2)
    except AlgodHTTPError as e:
        print(f"Error submitting results: {e}")
        if "err opcode executed" in str(e):
            print("This might be due to smart contract restrictions or incorrect parameters")
    except Exception as e:
        print(f"Error submitting results: {e}")
    
    # Step 10: Query verification status again (should be verified/1)
    print("\n=== STEP 10: Querying Updated Verification Status ===")
    try:
        status = registry_client.query_verification_status(TEST_ARTIFACT_HASH)
        print(f"Updated status: {status} ({'Pending' if status == 0 else 'Verified' if status == 1 else 'Failed'})")
    except Exception as e:
        print(f"Error querying verification status: {e}")
    
    # Step 11: Check final contract states
    print("\n=== STEP 11: Checking Final Contract States ===")
    print_contract_state(registry_client, registry_client.app_id, "FINAL SBOM REGISTRY CONTRACT STATE")
    print_contract_state(oracle_client, oracle_client.app_id, "FINAL COMPLIANCE ORACLE CONTRACT STATE")
    
    # Test complete
    print("\n===== TEST COMPLETED =====")
    print(f"Registry App ID: {registry_client.app_id}")
    print(f"Oracle App ID: {oracle_client.app_id}")
    print("All steps executed. Check output for any errors.")

if __name__ == "__main__":
    main()
