#!/usr/bin/env python3

import os
import argparse
from algosdk import account, mnemonic
from algosdk.v2client import algod

def get_algod_client(network="testnet"):
    """Create and return an Algorand client for the specified network"""
    if network == "testnet":
        algod_address = "https://testnet-api.algonode.cloud"
        algod_token = ""
    elif network == "mainnet":
        algod_address = "https://mainnet-api.algonode.cloud"
        algod_token = ""
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    return algod.AlgodClient(algod_token, algod_address)

def check_account_balance(address=None, mnemonic_phrase=None, network="testnet"):
    """
    Check the balance of an Algorand account
    
    Args:
        address: Algorand account address
        mnemonic_phrase: Mnemonic phrase to derive address if not provided
        network: Network to check balance on (testnet or mainnet)
    """
    if not address and not mnemonic_phrase:
        raise ValueError("Either address or mnemonic phrase must be provided")
    
    # Derive address from mnemonic if provided
    if mnemonic_phrase and not address:
        try:
            private_key = mnemonic.to_private_key(mnemonic_phrase)
            address = account.address_from_private_key(private_key)
            print(f"Derived address: {address}")
        except Exception as e:
            print(f"Error deriving address from mnemonic: {e}")
            return
    
    # Get algod client
    algod_client = get_algod_client(network)
    
    try:
        # Get account information
        account_info = algod_client.account_info(address)
        
        # Calculate balance in Algos
        microalgos = account_info.get("amount", 0)
        algos = microalgos / 1000000  # 1 Algo = 1,000,000 microAlgos
        
        # Print balance information
        print(f"Account: {address}")
        print(f"Network: {network}")
        print(f"Balance: {algos:.6f} ALGO ({microalgos} microALGO)")
        print(f"Min Balance Requirement: {account_info.get('min-balance', 0) / 1000000:.6f} ALGO")
        
        # Print assets if any
        assets = account_info.get("assets", [])
        if assets:
            print("\nAsset Holdings:")
            for asset in assets:
                print(f"  Asset ID: {asset['asset-id']}")
                print(f"  Amount: {asset['amount']}")
        
        # Check if balance is sufficient for smart contract deployment
        # A typical app creation costs about 0.001 ALGO plus min balance requirement
        if algos < 0.1:
            print("\n⚠️ WARNING: Balance may be insufficient for contract deployment.")
            print("Consider funding this account from the TestNet faucet:")
            print("https://bank.testnet.algorand.network/")
        
    except Exception as e:
        print(f"Error checking account balance: {e}")

def main():
    parser = argparse.ArgumentParser(description="Check Algorand account balance")
    parser.add_argument("--address", help="Algorand account address")
    parser.add_argument("--mnemonic", help="Mnemonic phrase to derive address")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet",
                        help="Network to check balance on (default: testnet)")
    
    # If script is run with arguments, parse them
    args = parser.parse_args()
    
    # Check if environment variables are set
    env_mnemonic = os.environ.get("ALGORAND_MNEMONIC")
    
    # Determine which credentials to use
    address = args.address
    mnemonic_phrase = args.mnemonic or env_mnemonic
    
    # If no credentials provided via args or env vars, prompt for deployer mnemonic
    if not address and not mnemonic_phrase:
        print("No account credentials provided. Please enter the deployer account mnemonic:")
        print("(This is the mnemonic shown when you ran deploy.py)")
        mnemonic_phrase = input("Mnemonic: ").strip()
    
    check_account_balance(address, mnemonic_phrase, args.network)

if __name__ == "__main__":
    main()
