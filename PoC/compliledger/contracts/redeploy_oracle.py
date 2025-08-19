#!/usr/bin/env python3
import json
import os
from pathlib import Path
from algosdk import transaction

# Reuse deploy utilities
import deploy as deploy_mod
import compliance_oracle as oracle_mod

CONFIG_PATH = Path(__file__).with_name("contract_config.json")


def main():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"contract_config.json not found at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    registry_app_id = int(cfg["registry_app_id"])  # keep existing registry

    # 1) Compile PyTeal to TEAL for oracle
    print("Compiling Compliance Oracle PyTeal → TEAL...")
    oracle_mod.compile_contract()

    # 2) Create deployer
    deployer = deploy_mod.ContractDeployer()

    # 3) Read TEAL and compile to binary
    print("Preparing TEAL for oracle deployment...")
    with open("CompliLedger_ComplianceOracle_approval.teal", "r") as f:
        oracle_approval = deployer.compile_program(f.read())
    with open("CompliLedger_ComplianceOracle_clear.teal", "r") as f:
        oracle_clear = deployer.compile_program(f.read())

    # 4) Define oracle schema (same as in deploy.py)
    oracle_global_schema = transaction.StateSchema(num_uints=3, num_byte_slices=3)
    oracle_local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    # 5) Deploy only the oracle
    print("Deploying new Compliance Oracle contract (keeping existing Registry)...")
    new_oracle_app_id = deployer.deploy_contract(
        oracle_approval,
        oracle_clear,
        oracle_global_schema,
        oracle_local_schema,
    )

    # 6) Link: set registry app id in oracle
    print("Linking new Oracle to existing Registry...")
    deployer.call_contract(
        new_oracle_app_id,
        [
            b"set_registry",
            int(registry_app_id).to_bytes(8, "big"),
        ],
    )

    # 7) Update config with new oracle app id
    cfg["oracle_app_id"] = int(new_oracle_app_id)

    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

    print("\nRedeploy complete!")
    print(f"Registry App ID: {registry_app_id}")
    print(f"New Compliance Oracle App ID: {new_oracle_app_id}")
    print(f"Updated configuration saved to {CONFIG_PATH}")

    # 8) Update project .env with new ORACLE_APP_ID
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env_path = os.path.join(repo_root, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as ef:
                lines = ef.readlines()
            found = False
            for i, ln in enumerate(lines):
                if ln.startswith("ORACLE_APP_ID="):
                    lines[i] = f"ORACLE_APP_ID={new_oracle_app_id}\n"
                    found = True
                    break
            if not found:
                lines.append(f"ORACLE_APP_ID={new_oracle_app_id}\n")
            with open(env_path, "w") as ef:
                ef.writelines(lines)
            print(f"Updated .env with new ORACLE_APP_ID at {env_path}")
        else:
            print(f".env not found at {env_path}; skipping .env update")
    except Exception as e:
        print(f"Warning: failed to update .env: {e}")


if __name__ == "__main__":
    main()
