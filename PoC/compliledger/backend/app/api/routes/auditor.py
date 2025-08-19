from fastapi import APIRouter, Query, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
import datetime
from pydantic import BaseModel

# Import services
from app.services.blockchain_service import AlgorandService
from compliledger.contracts.contract_integration import ContractIntegrationService

# Create router
router = APIRouter()

def get_blockchain_service():
    """Dependency for blockchain service"""
    return AlgorandService()

def get_contract_integration_service():
    """Dependency for contract integration / registry client"""
    return ContractIntegrationService()

# In-memory attestations store (PoC)
_attestations: Dict[str, List[Dict[str, Any]]] = {}

class AttestationBody(BaseModel):
    artifact_hash: str
    auditor_id: Optional[str] = None
    statement: str
    evidence_url: Optional[str] = None
    status: Optional[str] = "attested"  # e.g., attested/qualified/revoked

    class Config:
        schema_extra = {
            "example": {
                "artifact_hash": "b3f58a6e0c5228d74c2c15a4493be3429685eb8ae80f5638c545bc73ebd06768",
                "auditor_id": "aud-123",
                "statement": "Reviewed against NIST 800-53 moderate profile and found compliant.",
                "evidence_url": "https://example.com/evidence/report.pdf",
                "status": "attested"
            }
        }

@router.get("/search", summary="Search for verified artifacts")
async def search_artifacts(
    control_id: Optional[str] = Query(None, description="NIST Control ID (e.g., 'AC-3')"),
    artifact_hash: Optional[str] = Query(None, description="SHA-256 hash of the artifact"),
    company_name: Optional[str] = Query(None, description="Company name"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """
    Search for verified artifacts by control ID, hash, company, or date range
    
    At least one search parameter must be provided
    """
    # Ensure at least one search parameter is provided
    if not any([control_id, artifact_hash, company_name, from_date]):
        raise HTTPException(status_code=400, detail="At least one search parameter is required")
    
    # For PoC, generate mock results
    # In production, query the database
    mock_results = []
    
    if control_id:
        # Mock results for control ID search
        mock_results.extend([
            {
                "verification_id": "mock-verification-1",
                "artifact_hash": "89a4c23f5b8e7d6a1c9b0e3f2d1a5c8b7e9f0d3a",
                "compliance_score": 85,
                "control_status": "satisfied",
                "evidence": "Proper access control implementation found",
                "verified_at": "2025-08-01T10:15:30Z"
            },
            {
                "verification_id": "mock-verification-2",
                "artifact_hash": "7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c",
                "compliance_score": 70,
                "control_status": "not-satisfied",
                "evidence": "Missing proper access controls",
                "verified_at": "2025-08-05T14:22:10Z"
            }
        ])
    
    if artifact_hash:
        # Mock results for artifact hash search
        mock_results.extend([
            {
                "verification_id": "mock-verification-3",
                "artifact_hash": artifact_hash,
                "profile_id": "nist-800-53-moderate",
                "compliance_score": 92,
                "controls_passed": 48,
                "controls_failed": 4,
                "verified_at": "2025-08-10T09:45:12Z",
                "blockchain_txn_id": "mock-txn-id-3"
            }
        ])
    
    # Calculate pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_results = mock_results[start_idx:end_idx]
    
    return {
        "results": paginated_results,
        "total": len(mock_results),
        "page": page,
        "page_size": page_size,
        "pages": (len(mock_results) + page_size - 1) // page_size
    }

@router.get("/status/{artifact_hash}", summary="On-chain status lookup (auditor)")
async def status_lookup(
    artifact_hash: str,
    contract_service: ContractIntegrationService = Depends(get_contract_integration_service),
):
    """Auditor-facing status: 0=Pending, 1=Verified, 2=Failed.

    Returns 200 when registry client is initialized via environment.
    Returns 503 when missing `REGISTRY_APP_ID`/`ALGORAND_MNEMONIC`.

    Response example (200):
    {
      "artifact_hash": "...",
      "registry_app_id": 744253114,
      "status_code": 1,
      "status": "Verified"
    }
    """
    client = getattr(contract_service, "registry_client", None)
    app_id = getattr(contract_service, "registry_app_id", 0)
    if not client or not isinstance(app_id, int) or app_id <= 0:
        raise HTTPException(status_code=503, detail="Registry client not initialized")
    try:
        code = client.query_verification_status(artifact_hash)
        status = "Pending" if code == 0 else "Verified" if code == 1 else "Failed"
        return {"artifact_hash": artifact_hash, "registry_app_id": app_id, "status_code": code, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status query failed: {e}")

@router.get("/reports/{artifact_hash}", summary="List OSCAL report URLs (auditor)")
async def auditor_reports(artifact_hash: str):
    """Proxy to verification reports endpoint for convenience.

    Response example (200):
    {
      "artifact_hash": "...",
      "verified": {
        "directory_cid": "Qm...",
        "directory_url": "https://gateway.pinata.cloud/ipfs/Qm...",
        "component_definition": ".../component-definition.json",
        "assessment_plan": ".../assessment-plan.json",
        "assessment_results": ".../assessment-results.json",
        "poam": ".../poam.json"
      }
    }
    """
    # Lazy import to avoid circular
    from app.api.routes.verification import list_reports_for_artifact  # type: ignore
    return await list_reports_for_artifact(artifact_hash)  # reuse logic

@router.get("/verify/{artifact_hash}", summary="Verify artifact on blockchain")
async def verify_artifact_on_blockchain(
    artifact_hash: str,
    blockchain: AlgorandService = Depends(get_blockchain_service)
):
    """
    Independently verify an artifact on the Algorand blockchain
    
    - **artifact_hash**: SHA-256 hash of the artifact to verify
    """
    try:
        # In production, would call blockchain service to query status
        # For PoC, return mock verification data
        
        mock_verification = {
            "verified": True,
            "artifact_hash": artifact_hash,
            "status": "verified",
            "blockchain_proof": {
                "network": "algorand-testnet",
                "app_id": 12345678,
                "txn_id": f"mock-txn-for-{artifact_hash[:8]}",
                "block": 12345678,
                "timestamp": "2025-08-10T09:45:12Z",
                "explorer_url": f"https://testnet.algoexplorer.io/tx/mock-txn-for-{artifact_hash[:8]}"
            },
            "oscal_documents": {
                "cid": f"mock-ipfs-cid-for-{artifact_hash[:8]}",
                "component_definition_url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{artifact_hash[:8]}/component-definition.json",
                "assessment_results_url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{artifact_hash[:8]}/assessment-results.json"
            }
        }
        
        return mock_verification
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify artifact: {str(e)}")

@router.post("/attestations", summary="Submit an auditor attestation")
async def submit_attestation(body: AttestationBody):
    """Store an auditor attestation for an artifact (PoC in-memory).

    Request example:
    {
      "artifact_hash": "b3f58a6e0c5228d74c2c15a4493be3429685eb8ae80f5638c545bc73ebd06768",
      "auditor_id": "aud-123",
      "statement": "Reviewed and compliant",
      "evidence_url": "https://example.com/evidence/report.pdf",
      "status": "attested"
    }
    """
    rec = {
        "artifact_hash": body.artifact_hash,
        "auditor_id": body.auditor_id or "anonymous",
        "statement": body.statement,
        "evidence_url": body.evidence_url,
        "status": body.status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _attestations.setdefault(body.artifact_hash, []).append(rec)
    return {"status": "accepted", "attestation": rec}

@router.get("/attestations/{artifact_hash}", summary="List auditor attestations for an artifact")
async def list_attestations(artifact_hash: str):
    """List attestations previously submitted for an artifact hash."""
    items = _attestations.get(artifact_hash, [])
    return {"artifact_hash": artifact_hash, "count": len(items), "items": items}

@router.get("/oscal/{verification_id}", summary="Access OSCAL documents")
async def get_oscal_documents(verification_id: str):
    """
    Access OSCAL documents for a verified artifact
    
    - **verification_id**: ID of the verification record
    """
    # For PoC, return mock OSCAL document links
    mock_oscal = {
        "verification_id": verification_id,
        "oscal_documents": {
            "component_definition": {
                "cid": f"mock-ipfs-cid-for-{verification_id}/component-definition.json",
                "url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{verification_id}/component-definition.json"
            },
            "assessment_plan": {
                "cid": f"mock-ipfs-cid-for-{verification_id}/assessment-plan.json",
                "url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{verification_id}/assessment-plan.json"
            },
            "assessment_results": {
                "cid": f"mock-ipfs-cid-for-{verification_id}/assessment-results.json",
                "url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{verification_id}/assessment-results.json"
            },
            "poam": {
                "cid": f"mock-ipfs-cid-for-{verification_id}/poam.json",
                "url": f"https://ipfs.io/ipfs/mock-ipfs-cid-for-{verification_id}/poam.json"
            }
        }
    }
    
    return mock_oscal

@router.get("/audit-trail/{company_id}", summary="Export compliance audit trail")
async def export_audit_trail(company_id: str):
    """
    Export compliance history and audit trail for a company
    
    - **company_id**: ID of the company
    """
    # For PoC, return mock audit trail data
    mock_audit_trail = {
        "company_id": company_id,
        "company_name": f"Company {company_id}",
        "audit_period": {
            "from": "2025-01-01T00:00:00Z",
            "to": "2025-08-13T00:00:00Z"
        },
        "verification_count": 12,
        "compliance_trend": [
            {"date": "2025-01-15", "score": 75},
            {"date": "2025-02-15", "score": 78},
            {"date": "2025-03-15", "score": 80},
            {"date": "2025-04-15", "score": 85},
            {"date": "2025-05-15", "score": 82},
            {"date": "2025-06-15", "score": 88},
            {"date": "2025-07-15", "score": 90},
            {"date": "2025-08-13", "score": 92}
        ],
        "verifications": [
            {
                "id": f"{company_id}-verification-1",
                "date": "2025-08-10T09:45:12Z",
                "artifact_hash": "89a4c23f5b8e7d6a1c9b0e3f2d1a5c8b7e9f0d3a",
                "compliance_score": 92,
                "profile": "nist-800-53-moderate",
                "blockchain_txn_id": "mock-txn-id-1"
            },
            {
                "id": f"{company_id}-verification-2",
                "date": "2025-07-15T14:22:10Z",
                "artifact_hash": "7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c",
                "compliance_score": 90,
                "profile": "nist-800-53-moderate",
                "blockchain_txn_id": "mock-txn-id-2"
            }
        ]
    }
    
    return mock_audit_trail
