import React from 'react';
import { Button } from '@/components/ui/button';
import { useWalletContext } from '@/contexts/WalletContext';
import { LogIn, LogOut } from 'lucide-react';

export function WalletConnect() {
  const { isConnected, activeAccount, connect, disconnect } = useWalletContext();

  const formatAddress = (addr: string) => {
    if (!addr) return '';
    return `${addr.substring(0, 5)}...${addr.substring(addr.length - 5)}`;
  };

  if (isConnected && activeAccount) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
          {formatAddress(activeAccount)}
        </span>
        <Button variant="ghost" size="icon" onClick={disconnect} aria-label="Disconnect wallet">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <Button onClick={connect}>
      <LogIn className="h-4 w-4 mr-2" />
      Connect Wallet
    </Button>
  );
}
