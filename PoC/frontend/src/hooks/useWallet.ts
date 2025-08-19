import { useState, useEffect, useCallback } from 'react';
import { PeraWalletConnect } from '@perawallet/connect';
import type { Transaction } from 'algosdk';

// Initialize PeraWalletConnect for Algorand TestNet
const peraWallet = new PeraWalletConnect({ chainId: 416002 });

export function useWallet() {
  const [accounts, setAccounts] = useState<string[]>([]);
  const [activeAccount, setActiveAccount] = useState<string | null>(null);
  const isConnected = !!activeAccount;

  const handleDisconnect = useCallback(async () => {
    await peraWallet.disconnect();
    setAccounts([]);
    setActiveAccount(null);
  }, []);

  const handleConnect = useCallback(async () => {
    try {
      const newAccounts = await peraWallet.connect();
      peraWallet.connector?.on('disconnect', handleDisconnect);
      setAccounts(newAccounts);
      if (newAccounts.length > 0) {
        setActiveAccount(newAccounts[0]);
      }
    } catch (error) {
      // Ignore session connect errors, typically from user closing modal
      if (error?.data?.type !== 'SESSION_CONNECT') {
        console.error("Error connecting wallet:", error);
      }
    }
  }, [handleDisconnect]);

  const signTransactions = useCallback(async (transactions: Transaction[]) => {
    if (!isConnected) {
      throw new Error("Wallet not connected");
    }
    // Pera Wallet expects a nested array of transactions (transaction groups).
    // We'll sign the passed transactions as a single group.
    return await peraWallet.signTransaction([transactions]);
  }, [isConnected]);

  // Reconnect to the session when the app loads
  useEffect(() => {
    peraWallet.reconnectSession().then((newAccounts) => {
      if (peraWallet.isConnected && newAccounts.length) {
        peraWallet.connector?.on('disconnect', handleDisconnect);
        setAccounts(newAccounts);
        setActiveAccount(newAccounts[0]);
      }
    }).catch(console.info); // Use .info to not show as error in console for non-existent session
  }, [handleDisconnect]);

  return {
    accounts,
    activeAccount,
    isConnected,
    connect: handleConnect,
    disconnect: handleDisconnect,
    signTransactions,
  };
}
