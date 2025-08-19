import React from 'react';

type OnChainLinksProps = {
  // Algorand TestNet app IDs and tx IDs
  registryAppId: number | string;
  registryTxId?: string | null;
  oracleTxId?: string | null;

  // Artifact proofing
  artifactHash: string; // sha256 hash string
  oscalCid?: string | null; // IPFS CID for verified OSCAL

  // Optional: override gateways
  explorerBaseUrl?: string; // default: https://testnet.explorer.perawallet.app
  ipfsGatewayBase?: string; // default: https://gateway.pinata.cloud/ipfs
};

const OnChainLinks: React.FC<OnChainLinksProps> = ({
  registryAppId,
  registryTxId,
  oracleTxId,
  artifactHash,
  oscalCid,
  explorerBaseUrl = 'https://testnet.explorer.perawallet.app',
  ipfsGatewayBase = 'https://gateway.pinata.cloud/ipfs',
}) => {
  const appUrl = `${explorerBaseUrl}/application/${registryAppId}`;
  const regTxUrl = registryTxId ? `${explorerBaseUrl}/tx/${registryTxId}` : undefined;
  const oracleTxUrl = oracleTxId ? `${explorerBaseUrl}/tx/${oracleTxId}` : undefined;
  const oscalUrl = oscalCid ? `${ipfsGatewayBase}/${oscalCid}` : undefined;

  const Item: React.FC<{ label: string; value?: string; href?: string }> = ({ label, value, href }) => (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className="text-sm text-gray-600">{label}</span>
      {value ? (
        href ? (
          <a
            className="text-sm font-medium text-blue-600 hover:underline break-all"
            href={href}
            target="_blank"
            rel="noreferrer"
            title={value}
          >
            {value}
          </a>
        ) : (
          <span className="text-sm font-mono break-all" title={value}>
            {value}
          </span>
        )
      ) : (
        <span className="text-sm text-gray-400">—</span>
      )}
    </div>
  );

  return (
    <div className="rounded-md border border-gray-200 p-4 bg-white">
      <h3 className="text-base font-semibold mb-2">On-chain Proof</h3>

      {/* Explorer: Registry App */}
      <Item label="Registry App" value={`#${registryAppId}`} href={appUrl} />

      {/* Explorer: Registry Transaction */}
      <Item label="Registry Tx" value={registryTxId || undefined} href={regTxUrl} />

      {/* Explorer: Oracle Transaction (optional) */}
      <Item label="Oracle Tx" value={oracleTxId || undefined} href={oracleTxUrl} />

      {/* Artifact Hash: open the Registry App (explorers cannot deep-link by hash stored in boxes) */}
      <Item label="Artifact Hash" value={artifactHash} href={appUrl} />

      {/* IPFS: Verified OSCAL directory */}
      <Item label="OSCAL (IPFS)" value={oscalCid || undefined} href={oscalUrl} />

      <p className="mt-3 text-xs text-gray-500">
        Note: Explorers don’t currently deep-link to box-stored keys (artifact hashes). Clicking the hash opens the Registry App page; auditors can inspect boxes from there.
      </p>
    </div>
  );
};

export default OnChainLinks;
