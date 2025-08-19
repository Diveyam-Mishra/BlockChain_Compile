# CompliLedger Technical Architecture
**OSCAL-Integrated Hybrid On-Chain AI SBOM Verification System**

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │  Blockchain     │
│   (Next.js)     │◄──►│   (Python)       │◄──►│  (Algorand)     │
│   Vercel        │    │   Railway        │    │  TestNet        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │                       ▼                       ▼
        │              ┌─────────────────┐    ┌─────────────────┐
        │              │  AI Processing  │    │  Smart Contract │
        │              │ (Gemini 2.5)    │    │   (PyTeal)      │
        │              │  Flash Model    │    │                 │
        │              └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Wallet Connect │    │  OSCAL Engine   │    │   IPFS Storage  │
│   (Pera SDK)    │    │  (Python)       │    │   (Pinning)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Technology Stack

### **Frontend Layer**
- **Framework**: Next.js 14+ (App Router)
- **Deployment**: Vercel
- **UI Components**: Tailwind CSS + shadcn/ui
- **Wallet Integration**: Pera Wallet SDK
- **State Management**: React Context + Zustand

### **Backend Layer**
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Deployment**: Railway
- **Database**: PostgreSQL (Railway managed)
- **Queue System**: Redis (background jobs)

### **Blockchain Layer**
- **Network**: Algorand TestNet
- **Smart Contracts**: PyTeal
- **SDK**: Algorand Python SDK (py-algorand-sdk)
- **Wallet Connection**: Pera Wallet Connect

### **AI/ML Layer**
- **LLM**: Google Gemini 2.5 Flash
- **Framework**: LangChain + Google AI SDK
- **Processing**: Async task queues with Celery

### **Storage & Standards**
- **File Storage**: IPFS (Pinata/Web3.Storage)
- **Standards**: OSCAL 1.1.x JSON Schema
- **Document Generation**: Python-based OSCAL library

---

## Smart Contract Architecture (PyTeal)

### **Core Contracts**

#### **1. SBOMRegistry Contract**
```python
# PyTeal Smart Contract Structure
class SBOMRegistry:
    def __init__(self):
        self.artifact_hash = Bytes("artifact_hash")
        self.oscal_cid = Bytes("oscal_cid") 
        self.verification_status = Int("status")
        self.timestamp = Int("timestamp")
        self.submitter = Bytes("submitter")
        self.profile_id = Bytes("profile_id")
```

**State Schema**:
- `artifact_hash`: SHA-256 of uploaded artifact
- `oscal_cid`: IPFS CID of OSCAL documents
- `verification_status`: 0=Pending, 1=Verified, 2=Failed
- `compliance_score`: Integer 0-100
- `profile_id`: NIST baseline identifier

#### **2. ComplianceOracle Contract**
```python
class ComplianceOracle:
    def __init__(self):
        self.oracle_address = Bytes("oracle_addr")
        self.ai_result_hash = Bytes("ai_hash")
        self.findings_count = Int("findings")
        self.controls_passed = Int("passed")
        self.controls_failed = Int("failed")
```

### **Transaction Types**

1. **Submit Verification Request**
   - Store artifact hash + metadata
   - Emit event for AI Oracle
   - Return transaction ID

2. **Oracle Response** 
   - Update verification status
   - Store OSCAL CID and results
   - Trigger completion event

3. **Query Verification**
   - Read-only calls for auditor portal
   - Return verification status + blockchain proof

---

## Backend API Architecture (Python/FastAPI)

### **Core Services**

#### **1. Artifact Processing Service**
```python
# File: services/artifact_processor.py
class ArtifactProcessor:
    async def parse_sbom(self, file_content: bytes) -> SBOMData
    async def parse_smart_contract(self, code: str) -> ContractData  
    async def generate_artifact_hash(self, data: bytes) -> str
    async def extract_dependencies(self, artifact: Any) -> List[Dependency]
```

#### **2. OSCAL Generator Service**  
```python
# File: services/oscal_generator.py
class OSCALGenerator:
    async def create_component_definition(
        self, artifact: ArtifactData, profile: str
    ) -> ComponentDefinition
    
    async def create_assessment_plan(
        self, component: ComponentDefinition
    ) -> AssessmentPlan
    
    async def create_assessment_results(
        self, findings: List[Finding]
    ) -> AssessmentResults
    
    async def create_poam(
        self, failed_controls: List[Control]
    ) -> POAM
```

#### **3. AI Analysis Service**
```python
# File: services/ai_analyzer.py
import google.generativeai as genai

class GeminiAnalyzer:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def analyze_security_controls(
        self, artifact: ArtifactData, 
        controls: List[Control]
    ) -> AnalysisResults:
        
        prompt = self._build_analysis_prompt(artifact, controls)
        response = await self.model.generate_content_async(prompt)
        return self._parse_ai_response(response)
    
    def _build_analysis_prompt(self, artifact, controls) -> str:
        return f"""
        Analyze this {artifact.type} for NIST 800-53 compliance:
        
        Artifact: {artifact.metadata}
        Controls to evaluate: {[c.id for c in controls]}
        
        For each control, determine:
        1. Implementation status (satisfied/not-satisfied/not-applicable)
        2. Evidence or gaps found
        3. Risk level if not satisfied
        4. Specific recommendations
        
        Return structured JSON response.
        """
```

#### **4. Blockchain Service**
```python
# File: services/blockchain_service.py
from algosdk import algod_client, transaction
from algosdk.account import address_from_private_key

class AlgorandService:
    def __init__(self):
        self.algod_client = algod_client.AlgodClient(
            algod_token="",
            algod_address="https://testnet-api.algonode.cloud"
        )
    
    async def submit_verification_request(
        self, artifact_hash: str, 
        profile_id: str,
        submitter_address: str
    ) -> str:
        # Create application call transaction
        app_call_txn = transaction.ApplicationCallTxn(
            sender=submitter_address,
            sp=self.algod_client.suggested_params(),
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[
                "submit_verification",
                artifact_hash.encode(),
                profile_id.encode()
            ]
        )
        return await self._sign_and_send(app_call_txn)
    
    async def update_verification_result(
        self, request_id: str,
        oscal_cid: str, 
        compliance_score: int
    ) -> str:
        # Oracle updates verification status
        pass
```

---

## Frontend Architecture (Next.js)

### **Folder Structure**
```
src/
├── app/
│   ├── company/              # Company portal pages
│   │   ├── upload/
│   │   ├── verify/
│   │   └── results/
│   ├── auditor/              # Auditor portal pages  
│   │   ├── search/
│   │   ├── verify/
│   │   └── reports/
│   └── api/                  # API routes (proxy to Railway)
├── components/
│   ├── ui/                   # shadcn components
│   ├── wallet/               # Pera wallet integration
│   ├── forms/                # Upload forms
│   └── charts/               # Compliance dashboards
├── hooks/
│   ├── useWallet.ts          # Pera wallet hook
│   ├── useAlgorand.ts        # Blockchain interactions
│   └── useOSCAL.ts           # OSCAL document handling
├── lib/
│   ├── algorand.ts           # Algorand SDK setup
│   ├── api.ts                # Railway API client
│   └── utils.ts              # Helper functions
└── types/
    ├── algorand.ts           # Blockchain types
    ├── oscal.ts              # OSCAL schema types
    └── api.ts                # API response types
```

### **Key Components**

#### **Wallet Integration (Pera SDK)**
```typescript
// hooks/useWallet.ts
import { PeraWalletConnect } from "@perawallet/connect"

export const useWallet = () => {
  const [peraWallet] = useState(() => new PeraWalletConnect())
  const [accounts, setAccounts] = useState<string[]>([])

  const connectWallet = async () => {
    try {
      const newAccounts = await peraWallet.connect()
      setAccounts(newAccounts)
      peraWallet.connector?.on("disconnect", () => {
        setAccounts([])
      })
    } catch (error) {
      console.error("Wallet connection failed:", error)
    }
  }

  const signTransaction = async (txn: Transaction) => {
    return await peraWallet.signTransaction([txn])
  }

  return { accounts, connectWallet, signTransaction, peraWallet }
}
```

#### **Algorand Integration**
```typescript  
// lib/algorand.ts
import algosdk from "algosdk"

const algodClient = new algosdk.Algodv2(
  "",
  "https://testnet-api.algonode.cloud", 
  443
)

export const submitVerificationRequest = async (
  artifactHash: string,
  profileId: string,
  senderAddress: string,
  signTxn: (txn: Transaction[]) => Promise<Uint8Array[]>
) => {
  const suggestedParams = await algodClient.getTransactionParams().do()
  
  const appCallTxn = algosdk.makeApplicationCallTxnFromObject({
    from: senderAddress,
    appIndex: APP_ID,
    onComplete: algosdk.OnApplicationComplete.NoOpOC,
    appArgs: [
      new Uint8Array(Buffer.from("submit_verification")),
      new Uint8Array(Buffer.from(artifactHash)),
      new Uint8Array(Buffer.from(profileId))
    ],
    suggestedParams
  })

  const signedTxn = await signTxn([appCallTxn])
  const { txId } = await algodClient.sendRawTransaction(signedTxn).do()
  
  await algosdk.waitForConfirmation(algodClient, txId, 4)
  return txId
}
```

---

## API Endpoints

### **Company Portal APIs**
```python
# Railway Backend APIs
POST /api/v1/artifacts/upload
    - Multipart file upload (SBOM/Smart Contract)
    - Returns: artifact_id, hash, parsing_status

GET /api/v1/profiles
    - List available compliance baselines
    - Returns: NIST 800-53, ISO 27001, etc.

POST /api/v1/verification/submit
    - Trigger AI analysis + blockchain submission  
    - Body: { artifact_id, profile_id, wallet_address }
    - Returns: verification_request_id, algorand_txn_id

GET /api/v1/verification/{request_id}/status
    - Poll verification progress
    - Returns: status, progress%, ai_findings

GET /api/v1/verification/{request_id}/results
    - Get final OSCAL documents + compliance score
    - Returns: oscal_files, blockchain_proof, pdf_export

POST /api/v1/verification/{request_id}/download
    - Download OSCAL files (ZIP)
    - Returns: component-definition.json, assessment-results.json, etc.
```

### **Auditor Portal APIs**
```python  
GET /api/v1/auditor/search
    - Query: control_id, artifact_hash, company_name, date_range
    - Returns: verification_records[], pagination

GET /api/v1/auditor/verify/{artifact_hash}
    - Independent blockchain verification
    - Returns: algorand_txn_id, verification_status, timestamps

GET /api/v1/auditor/oscal/{verification_id}
    - Access OSCAL documents for verified artifacts
    - Returns: oscal_documents[], ipfs_links[]

GET /api/v1/auditor/audit-trail/{company_id}
    - Export compliance history
    - Returns: audit_trail.json, compliance_trend_data
```

---

## Data Flow

### **Verification Process Flow**
```
1. Frontend Upload
   ├── File → Next.js → Railway API
   ├── Parse & Hash → Store in PostgreSQL  
   └── Return artifact_id

2. Compliance Analysis  
   ├── Select NIST Profile → Load Controls
   ├── Submit to Blockchain → Get txn_id
   ├── Trigger AI Analysis → Gemini 2.5 Flash
   └── Generate OSCAL Documents

3. Blockchain Anchoring
   ├── OSCAL Files → IPFS → Get CID
   ├── Results Hash + CID → Algorand
   └── Update verification status

4. Auditor Verification
   ├── Search Portal → Query Database  
   ├── Blockchain Verification → Algorand Explorer
   └── Download OSCAL → IPFS Retrieval
```

### **AI Analysis Pipeline**
```python
# Async processing with Celery + Redis
@celery.app.task
async def process_verification_request(request_id: str):
    # 1. Load artifact and controls
    artifact = await get_artifact(request_id)
    controls = await load_nist_controls(artifact.profile_id)
    
    # 2. AI Analysis with Gemini
    analyzer = GeminiAnalyzer()
    findings = await analyzer.analyze_security_controls(artifact, controls)
    
    # 3. Generate OSCAL Documents
    oscal_gen = OSCALGenerator()
    assessment_results = await oscal_gen.create_assessment_results(findings)
    poam = await oscal_gen.create_poam(findings.failed_controls)
    
    # 4. Store to IPFS
    ipfs_cid = await store_to_ipfs({
        "assessment_results": assessment_results,
        "poam": poam
    })
    
    # 5. Update Blockchain
    blockchain = AlgorandService()  
    await blockchain.update_verification_result(
        request_id, ipfs_cid, findings.compliance_score
    )
    
    return {"status": "completed", "score": findings.compliance_score}
```

---

## Security & Performance

### **Security Measures**
- **API Authentication**: JWT tokens + rate limiting
- **Wallet Security**: Client-side signing only
- **Data Privacy**: No sensitive data on-chain (only hashes)
- **OSCAL Validation**: Schema enforcement before storage

### **Performance Optimizations**  
- **Async Processing**: Celery background jobs
- **Caching**: Redis for frequent queries
- **CDN**: Vercel Edge Network
- **Database**: Connection pooling + indexing

### **Monitoring**
- **Backend**: Railway metrics + custom dashboards
- **Frontend**: Vercel Analytics  
- **Blockchain**: Algorand Indexer for transaction monitoring
- **AI**: Gemini API usage tracking

This architecture provides a robust, scalable foundation for the CompliLedger PoC while leveraging the specified technology stack effectively.~