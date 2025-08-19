#!/usr/bin/env python3

from algosdk import account, mnemonic
from algosdk.v2client import algod
import argparse
import time

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

def check_deployer_balance(deployer_mnemonic=None, watch_mode=False, interval=10):
    """
    Check the balance of the deployer account
    
    Args:
        deployer_mnemonic: Mnemonic of the deployer account
        watch_mode: If True, continuously monitor the balance
        interval: Seconds between balance checks when in watch mode
    """
    # Use the provided deployer mnemonic or the default one from contract creation
    if not deployer_mnemonic:
        deployer_mnemonic = "day peanut cycle shrimp bounce spend fee neglect enrich rigid manual tiger adjust ugly pigeon parrot universe river later hire clown capital extra ability found"
    
    # Get address from mnemonic
    try:
        private_key = mnemonic.to_private_key(deployer_mnemonic)
        address = account.address_from_private_key(private_key)
    except Exception as e:
        print(f"Error deriving address from mnemonic: {e}")
        return
    
    # Get algod client
    algod_client = get_algod_client("testnet")
    
    # Function to display balance
    def display_balance():
        try:
            # Get account information
            account_info = algod_client.account_info(address)
            
            # Calculate balance in Algos
            microalgos = account_info.get("amount", 0)
            algos = microalgos / 1000000  # 1 Algo = 1,000,000 microAlgos
            
            # Print balance information
            print(f"\n----- DEPLOYER ACCOUNT STATUS [{time.strftime('%H:%M:%S')}] -----")
            print(f"Account: {address}")
            print(f"Balance: {algos:.6f} ALGO ({microalgos} microALGO)")
            
            # Check if balance is sufficient for smart contract deployment
            if algos < 0.1:
                print("\n⚠️ WARNING: Balance may be insufficient for contract deployment.")
                print("Consider funding this account from the TestNet faucet:")
                print("https://bank.testnet.algorand.network/")
                print(f"Address to fund: {address}")
            else:
                print("\n✅ Balance is sufficient for contract deployment")
            
            return algos
            
        except Exception as e:
            print(f"Error checking account balance: {e}")
            return 0
    
    # Initial balance display
    balance = display_balance()
    
    # Watch mode
    if watch_mode:
        print(f"\nWatching account balance. Press Ctrl+C to stop.")
        try:
            last_balance = balance
            while True:
                time.sleep(interval)
                new_balance = display_balance()
                
                # Alert on balance change
                if new_balance != last_balance:
                    change = new_balance - last_balance
                    print(f"\n🔔 Balance changed by {change:+.6f} ALGO")
                    last_balance = new_balance
        except KeyboardInterrupt:
            print("\nStopping balance monitor.")

def main():
    parser = argparse.ArgumentParser(description="Check and monitor deployer account balance")
    parser.add_argument("--mnemonic", help="Alternative mnemonic to use")
    parser.add_argument("--watch", action="store_true", help="Watch account balance continuously")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between balance checks when watching (default: 10)")
    
    args = parser.parse_args()
    check_deployer_balance(args.mnemonic, args.watch, args.interval)

if __name__ == "__main__":
    main()
