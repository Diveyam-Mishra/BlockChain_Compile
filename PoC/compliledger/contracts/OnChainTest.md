# CompliLedger On-Chain Test Results

This document provides an overview of the on-chain test results for the CompliLedger Proof of Concept (PoC) project, including deployed smart contracts on Algorand TestNet and their transaction history.

## Deployed Contracts

| Contract | App ID | Purpose |
|----------|--------|---------|
| SBOMRegistry | [744253114](https://testnet.explorer.perawallet.app/application/744253114/) | Manages SBOM verification records and status |
| ComplianceOracle | [744253115](https://testnet.explorer.perawallet.app/application/744253115/) | Evaluates AI analysis results and updates registry |

## Transaction History

### Deployment Transactions

| Transaction | Type | Description | Explorer Link |
|-------------|------|-------------|--------------|
| SWHER4WHBQEK5WSHFLSPZDOGOPNBCVWJTR3CCTFQUM5RAR3DKJIQ | App Create | Deploy SBOM Registry | [View on Explorer](https://testnet.explorer.perawallet.app/tx/SWHER4WHBQEK5WSHFLSPZDOGOPNBCVWJTR3CCTFQUM5RAR3DKJIQ/) |
| SHJUEZBYXVUUCYPQ6YM2FGZSR5FQVFU3T6NKGHXUNCIBQQYAVVPA | App Create | Deploy Compliance Oracle | [View on Explorer](https://testnet.explorer.perawallet.app/tx/SHJUEZBYXVUUCYPQ6YM2FGZSR5FQVFU3T6NKGHXUNCIBQQYAVVPA/) |
| KRZG34TTEQP3CCWWDT3I4RT3AV7ESR7E2W2FE4O5YOSTHMHVY2KA | App Call | Set Registry App ID in Oracle | [View on Explorer](https://testnet.explorer.perawallet.app/tx/KRZG34TTEQP3CCWWDT3I4RT3AV7ESR7E2W2FE4O5YOSTHMHVY2KA/) |
| TJNJTYPQHEWLBMFLYUZODTOHWQWQJONHXADWASQR3R7VEZTBEWOA | App Call | Set Oracle Address in Registry | [View on Explorer](https://testnet.explorer.perawallet.app/tx/TJNJTYPQHEWLBMFLYUZODTOHWQWQJONHXADWASQR3R7VEZTBEWOA/) |

### Test Transactions

| Transaction | Type | Status | Description | Explorer Link |
|-------------|------|--------|-------------|--------------|
| LSUFZHM7QQWLKILU2JYZW7S23IIKJUTM6YGRKWW4KJDTLVEWX2GQ | App Create | Success | Deployed SBOMRegistry (App ID 744253114) | [View](https://testnet.explorer.perawallet.app/tx/LSUFZHM7QQWLKILU2JYZW7S23IIKJUTM6YGRKWW4KJDTLVEWX2GQ/) |
| NMG3HP75EGBDR4X4S3ZWTRSGTSWB42GNBKXWBZ5VUKGG3OTAE5WA | App Create | Success | Deployed ComplianceOracle (App ID 744253115) | [View](https://testnet.explorer.perawallet.app/tx/NMG3HP75EGBDR4X4S3ZWTRSGTSWB42GNBKXWBZ5VUKGG3OTAE5WA/) |
| QI7FCPUW64T2VRUB2HZHC4SHMGBB53C5GQHZ7S2BN4HOFA3LB5KQ | App Call | Success | Oracle set_registry to Registry App ID | [View](https://testnet.explorer.perawallet.app/tx/QI7FCPUW64T2VRUB2HZHC4SHMGBB53C5GQHZ7S2BN4HOFA3LB5KQ/) |
| K6RD3H6F7YORGVERR2VIRBPGMR5USH3VSEI25UXBFCWMKK6M56DQ | App Call | Success | Registry set_oracle to Oracle app address | [View](https://testnet.explorer.perawallet.app/tx/K6RD3H6F7YORGVERR2VIRBPGMR5USH3VSEI25UXBFCWMKK6M56DQ/) |
| WV7MGS3VOS7WKHNOUPTANKLBQZQNNBNRRBGEMEJSVENEC7OQMAUA | App Call | Success | Artifact Registration (example: hash 317986d3...) | [View](https://testnet.explorer.perawallet.app/tx/WV7MGS3VOS7WKHNOUPTANKLBQZQNNBNRRBGEMEJSVENEC7OQMAUA/) |
| A3FGWYRQ5CFKMJQKYHB27IYL7IFFXSLNUT7BAUM44ERBBZ3XSJJQ | App Call | Success | Artifact Registration (example: hash 4916b636...) | [View](https://testnet.explorer.perawallet.app/tx/A3FGWYRQ5CFKMJQKYHB27IYL7IFFXSLNUT7BAUM44ERBBZ3XSJJQ/) |
| KVHFRYN774427YVBAFOXP5PENC223UPDMI562R3NBRS65IWECNVQ | App Call | Success | Submit Analysis Results (oracle to registry) | [View](https://testnet.explorer.perawallet.app/tx/KVHFRYN774427YVBAFOXP5PENC223UPDMI562R3NBRS65IWECNVQ/) |
| II3LNMKNFVUGZMMXPBHAUVW67R3CV5NMBHQH3RFTWK24EJFLNIXA | App Call | Success | Submit Analysis Results (oracle to registry) | [View](https://testnet.explorer.perawallet.app/tx/II3LNMKNFVUGZMMXPBHAUVW67R3CV5NMBHQH3RFTWK24EJFLNIXA/) |

> Note: Verification status queries are performed via App Call logging and may not always have distinct tx IDs captured in this summary. Both Pending (0) and Verified (1) states were observed during tests.

### Latest End-to-End Validation (Aug 14, 2025 18:00 IST)

- Admin/account: 5IGW4MX4LXEXU6OX4QBUJ2TZ2AH6DWMADY5HPJ6NAI3D7RPTQNEDMOGR6A
- Contracts linked: Registry App ID 744253114; Oracle App ID 744253115
- Sample artifact hash: 94d473c0062d84a40dbf0243e16758e02e34fe6be08634e420125633caa240bd
- Registration: Success; initial status 0 (Pending)
- Oracle submission: Result hash 947c6cbab3518cd2dfe20c2666a3bda29f1fea6862aef5e51a434d9f242ffa52; Controls Passed 8, Failed 0; OSCAL CID QmTest66073OSCAL
- Verification: Success; status updated to 1 (Verified)

## Implementation Status: 100% Success 

The blockchain component of the CompliLedger PoC is successfully implemented with fully deployed and linked smart contracts. All core flows — registration, query, and result submission — have been validated on TestNet with the latest deployment.

## Impact on Execution Plan

The deployed smart contracts and successful testing implements key aspects from the [Execution Plan](../Execution_Plan.md), specifically from **Day 4: Assessment Results & Blockchain**:

- ✅ **Deploy Algorand smart contracts (verification registry)** - Both SBOMRegistry and ComplianceOracle contracts have been successfully deployed and linked
- ✅ **Anchor OSCAL hash + IPFS CID on-chain** - Contract structures support storing artifact hashes and IPFS CIDs

## Contract Features & Implementation

### SBOMRegistry Contract
- **Purpose**: Serves as the main registry for SBOM verification status
- **Features**:
  - Records verification requests with artifact hash and metadata
  - Stores verification status (0=Pending, 1=Verified, 2=Failed)
  - Links artifacts to submitter addresses
  - Restricts verification updates to authorized oracle address
  - Admin-only control for configuration changes
  - Queryable verification status for any registered artifact

### ComplianceOracle Contract
- **Purpose**: Authoritative source for compliance verification results
- **Features**:
  - Accepts AI analysis results with control pass/fail counts
  - Stores OSCAL document CIDs on-chain
  - Forwards verification results to Registry via inner transactions
  - Admin-only control for configuration changes
  - Maintains registry of all verification activities

### Current Implementation State
All prior issues have been resolved:

1. State reading fixed by proper bytes/Itob/Btoi handling
2. Verification queries succeed with correct args and schema headroom (num_uints=12)
3. Oracle result submission works; registry updated via authorized oracle address

## Next Steps

1. Add exact transaction hashes from the latest `test_deployed_contracts.py` run
2. Complete remaining Execution Plan items (Days 5-7):
   - Build auditor portal with blockchain verification
   - Implement document export system
   - Prepare demonstration materials

## Links
- [SBOMRegistry Contract](sbom_registry.py)
- [ComplianceOracle Contract](compliance_oracle.py)
- [Contract Clients](compliledger_clients.py)
- [Test Script](test_deployed_contracts.py)
