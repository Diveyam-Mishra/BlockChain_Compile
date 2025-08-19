import os
import base64
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
import json
from algosdk.logic import get_application_address
from algosdk import encoding as algo_encoding
import time
import certifi

class ContractDeployer:
    def __init__(self, algod_address="https://testnet-api.algonode.cloud", algod_token=""):
        """Initialize the deployer with Algorand client"""
        # Ensure TLS verification uses certifi bundle (fixes SSL on macOS)
        try:
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        except Exception:
            pass
        headers = {"User-Agent": "py-algorand-sdk"}
        self.algod_client = algod.AlgodClient(algod_token, algod_address, headers=headers)
        
        # Load account from mnemonic if provided in env var
        try:
            # Use hardcoded mnemonic of our funded account
            funded_mnemonic = "day peanut cycle shrimp bounce spend fee neglect enrich rigid manual tiger adjust ugly pigeon parrot universe river later hire clown capital extra ability found"
            
            # Use environment variable if available, otherwise use the funded account
            creator_mnemonic = os.environ.get("ALGORAND_MNEMONIC", funded_mnemonic)
            
            self.private_key = mnemonic.to_private_key(creator_mnemonic)
            self.address = account.address_from_private_key(self.private_key)
            print(f"Using account: {self.address}")
            
            # Check if we're using the funded account
            if creator_mnemonic == funded_mnemonic:
                print("Using previously funded account with 10 ALGO balance")
            else:
                print(f"Using custom account from environment variable")
                print("⚠️ Make sure this account has sufficient funds for contract deployment!")
        except Exception as e:
            print(f"Error initializing account: {e}")
            raise
    
    def compile_program(self, source_code):
        """Compile TEAL source code to binary"""
        try:
            compile_response = self.algod_client.compile(source_code)
            return base64.b64decode(compile_response["result"])
        except Exception as e:
            print(f"Error compiling TEAL: {e}")
            raise
    
    def wait_for_confirmation(self, txid):
        """Wait for transaction confirmation"""
        last_round = self.algod_client.status().get("last-round")
        while True:
            txinfo = self.algod_client.pending_transaction_info(txid)
            if txinfo.get("confirmed-round", 0) > 0:
                print(f"Transaction {txid} confirmed in round {txinfo.get('confirmed-round')}")
                return txinfo
            
            last_round += 1
            self.algod_client.status_after_block(last_round)
            print(f"Waiting for confirmation... (Round: {last_round})")
            time.sleep(2)
    
    def deploy_contract(self, approval_program, clear_program, global_schema, local_schema):
        """Deploy smart contract to Algorand TestNet"""
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Create application transaction
            txn = transaction.ApplicationCreateTxn(
                sender=self.address,
                sp=params,
                on_complete=transaction.OnComplete.NoOpOC,
                approval_program=approval_program,
                clear_program=clear_program,
                global_schema=global_schema,
                local_schema=local_schema
            )
            
            # Sign transaction
            signed_txn = txn.sign(self.private_key)
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            print(f"Submitted application create transaction: {tx_id}")
            
            # Wait for confirmation
            tx_response = self.wait_for_confirmation(tx_id)
            app_id = tx_response["application-index"]
            print(f"Created new app with ID: {app_id}")
            return app_id
        except Exception as e:
            print(f"Error deploying contract: {e}")
            raise
    
    def call_contract(self, app_id, app_args):
        """Call a method on the deployed contract"""
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Create application call transaction
            txn = transaction.ApplicationCallTxn(
                sender=self.address,
                sp=params,
                index=app_id,
                on_complete=transaction.OnComplete.NoOpOC,
                app_args=app_args
            )
            
            # Sign transaction
            signed_txn = txn.sign(self.private_key)
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            print(f"Submitted application call transaction: {tx_id}")
            
            # Wait for confirmation
            tx_response = self.wait_for_confirmation(tx_id)
            return tx_response
        except Exception as e:
            print(f"Error calling contract: {e}")
            raise

def deploy_registry_and_oracle():
    """Deploy both contracts to TestNet and set up their relationship"""
    deployer = ContractDeployer()
    
    print("Compiling CompliLedger SBOM Registry contract...")
    # Read and compile approval program
    with open("CompliLedger_SbomRegistry_approval.teal", "r") as f:
        sbom_approval = deployer.compile_program(f.read())
    
    # Read and compile clear state program
    with open("CompliLedger_SbomRegistry_clear.teal", "r") as f:
        sbom_clear = deployer.compile_program(f.read())
    
    print("Compiling CompliLedger Compliance Oracle contract...")
    # Read and compile approval program
    with open("CompliLedger_ComplianceOracle_approval.teal", "r") as f:
        oracle_approval = deployer.compile_program(f.read())
    
    # Read and compile clear state program
    with open("CompliLedger_ComplianceOracle_clear.teal", "r") as f:
        oracle_clear = deployer.compile_program(f.read())
    
    # Define schemas for the contracts
    print("Deploying SBOM Registry contract (box-based)...")
    # Registry now stores per-artifact records in boxes; keep globals minimal
    sbom_global_schema = transaction.StateSchema(num_uints=0, num_byte_slices=2)
    sbom_local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)
    
    # Deploy registry contract
    registry_app_id = deployer.deploy_contract(
        sbom_approval,
        sbom_clear,
        sbom_global_schema,
        sbom_local_schema
    )
    
    print("Deploying Compliance Oracle contract...")
    # For oracle: We store analytics data and app references
    oracle_global_schema = transaction.StateSchema(num_uints=3, num_byte_slices=3)
    oracle_local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)
    
    # Deploy oracle contract
    oracle_app_id = deployer.deploy_contract(
        oracle_approval,
        oracle_clear,
        oracle_global_schema,
        oracle_local_schema
    )
    
    # Link the contracts by setting registry ID in oracle
    print("Linking contracts...")
    deployer.call_contract(
        oracle_app_id,
        [
            "set_registry".encode(),
            registry_app_id.to_bytes(8, "big")
        ]
    )
    
    # Set oracle address in registry to the oracle application's address (32-byte public key)
    print("Setting oracle address in registry...")
    oracle_app_addr = get_application_address(oracle_app_id)  # base32 address string
    oracle_app_pk = algo_encoding.decode_address(oracle_app_addr)  # 32-byte public key
    deployer.call_contract(
        registry_app_id,
        [
            "set_oracle".encode(),
            oracle_app_pk
        ]
    )
    
    # Save app IDs to config file
    config = {
        "registry_app_id": registry_app_id,
        "oracle_app_id": oracle_app_id,
        "oracle_address": deployer.address,
        "network": "testnet"
    }
    
    with open("contract_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Update project .env with new IDs
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env_path = os.path.join(repo_root, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as ef:
                lines = ef.readlines()
            def upsert(lines, key, value):
                found = False
                for i, ln in enumerate(lines):
                    if ln.startswith(key+"="):
                        lines[i] = f"{key}={value}\n"
                        found = True
                        break
                if not found:
                    lines.append(f"{key}={value}\n")
                return lines
            lines = upsert(lines, "REGISTRY_APP_ID", str(registry_app_id))
            lines = upsert(lines, "ORACLE_APP_ID", str(oracle_app_id))
            with open(env_path, "w") as ef:
                ef.writelines(lines)
            print(f"Updated .env with new App IDs at {env_path}")
        else:
            print(f".env not found at {env_path}; skipping .env update")
    except Exception as e:
        print(f"Warning: failed to update .env: {e}")

    print(f"\nDeployment complete!")
    print(f"CompliLedger SBOMRegistry App ID: {registry_app_id}")
    print(f"CompliLedger ComplianceOracle App ID: {oracle_app_id}")
    print(f"Configuration saved to contract_config.json")
    
    return registry_app_id, oracle_app_id

def compile_pyteal_to_teal():
    """Compile PyTeal contracts to TEAL files"""
    import sbom_registry
    import compliance_oracle
    
    # Execute the compilation code for each contract
    # This will create the TEAL files
    if hasattr(sbom_registry, "compile_contract"):
        sbom_registry.compile_contract()
    else:
        # Default compilation if compile_contract doesn't exist
        with open("sbom_registry_approval.teal", "w") as f:
            compiled = sbom_registry.compileTeal(sbom_registry.sbom_registry(), sbom_registry.Mode.Application, version=6)
            f.write(compiled)
        
        with open("sbom_registry_clear.teal", "w") as f:
            compiled = sbom_registry.compileTeal(sbom_registry.clear_state_program(), sbom_registry.Mode.Application, version=6)
            f.write(compiled)
    
    if hasattr(compliance_oracle, "compile_contract"):
        compliance_oracle.compile_contract()
    else:
        # Default compilation if compile_contract doesn't exist
        with open("compliance_oracle_approval.teal", "w") as f:
            compiled = compliance_oracle.compileTeal(compliance_oracle.approval_program(), compliance_oracle.Mode.Application, version=6)
            f.write(compiled)
        
        with open("compliance_oracle_clear.teal", "w") as f:
            compiled = compliance_oracle.compileTeal(compliance_oracle.clear_state_program(), compliance_oracle.Mode.Application, version=6)
            f.write(compiled)

if __name__ == "__main__":
    # First, compile the PyTeal contracts to TEAL
    print("Compiling PyTeal to TEAL...")
    compile_pyteal_to_teal()
    
    # Now deploy the contracts
    deploy_registry_and_oracle()
