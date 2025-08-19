import React, { createContext, useContext } from 'react';
import { useWallet } from '@/hooks/useWallet';

// The type of the value provided by the context
type WalletContextType = ReturnType<typeof useWallet>;

// Create the context with a null default value
const WalletContext = createContext<WalletContextType | null>(null);

/**
 * The provider component that wraps the application and makes the wallet state available.
 */
export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const wallet = useWallet();
  return (
    <WalletContext.Provider value={wallet}>
      {children}
    </WalletContext.Provider>
  );
};

/**
 * A custom hook to consume the wallet context.
 * This makes it easy for components to access the wallet state and functions.
 */
export const useWalletContext = () => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWalletContext must be used within a WalletProvider');
  }
  return context;
};
