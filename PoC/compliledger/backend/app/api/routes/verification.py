from fastapi import APIRouter, Form, Depends, HTTPException, Body
from typing import Optional, Dict, Any, List
import uuid
import datetime
import json
import sys
from pathlib import Path

# Add contracts directory to path
ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent.absolute()
CONTRACTS_DIR = ROOT_DIR / "compliledger" / "contracts"
sys.path.append(str(ROOT_DIR))

# Import services
from app.services.ai_analyzer import GeminiAnalyzer
from app.services.oscal_generator import OSCALGenerator
from app.services.blockchain_service import AlgorandService
from app.services.ipfs_service import IPFSService
from app.services.smart_contract_analyzer import SmartContractAnalyzer
from app.services.storage_service import StorageService
from compliledger.contracts.contract_integration import ContractIntegrationService

# Create router
router = APIRouter()

# In-memory storage for PoC (would use database in production)
verification_requests = {}

def get_ai_analyzer():
    """Dependency for AI analyzer service"""
    return GeminiAnalyzer()

def get_oscal_generator():
    """Dependency for OSCAL generator service"""
    return OSCALGenerator()

def get_blockchain_service():
    """Dependency for blockchain service"""
    return AlgorandService()

def get_ipfs_service():
    """Dependency for IPFS service"""
    return IPFSService()

def get_contract_integration_service():
    """Dependency for contract integration service"""
    return ContractIntegrationService()

def get_smart_contract_analyzer():
    """Dependency for Solidity analyzer"""
    return SmartContractAnalyzer()

def get_storage_service():
    """Dependency for storage service"""
    return StorageService()

@router.get("/status/{artifact_hash}", summary="Query on-chain verification status by artifact hash")
async def verification_status(
    artifact_hash: str,
    contract_service: ContractIntegrationService = Depends(get_contract_integration_service),
):
    """Return the current on-chain status for the artifact hash.

    Status codes: 0=Pending, 1=Verified, 2=Failed
    """
    try:
        client = getattr(contract_service, "registry_client", None)
        app_id = getattr(contract_service, "registry_app_id", 0)
        if not client or not isinstance(app_id, int) or app_id <= 0:
            raise HTTPException(status_code=503, detail="Registry client not initialized")

        code = client.query_verification_status(artifact_hash)
        status = "Pending" if code == 0 else "Verified" if code == 1 else "Failed"
        return {
            "artifact_hash": artifact_hash,
            "registry_app_id": app_id,
            "status_code": code,
            "status": status,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status query failed: {e}")

@router.get("/reports/{artifact_hash}", summary="List OSCAL report URLs for an artifact")
async def list_reports_for_artifact(artifact_hash: str):
    """Return OSCAL report URLs (initial and verified) for the latest completed run.

    Scans in-memory verification_requests for the newest completed entry with a
    matching artifact_hash and returns URLs derived from stored CIDs.
    """
    # Find latest completed request for this hash
    latest = None
    latest_ts = None
    for req_id, rec in verification_requests.items():
        try:
            result = rec.get("result") or {}
            ah = result.get("artifact_hash") or rec.get("artifact_hash")
            status = rec.get("status")
            if status != "completed":
                continue
            if ah != artifact_hash:
                continue
            ts = rec.get("completed_at") or rec.get("updated_at")
            # Use string timestamp ordering fallback if parsing fails
            if latest is None or (ts and (latest_ts is None or str(ts) > str(latest_ts))):
                latest = rec
                latest_ts = ts
        except Exception:
            continue

    if not latest:
        raise HTTPException(status_code=404, detail="No completed reports found for artifact_hash")

    result = latest.get("result", {})
    # Prefer verified CID, fall back to initial if present
    verified_cid = result.get("verified_oscal_cid")
    initial_cid = result.get("initial_oscal_cid")

    def mk_urls(cid: str) -> Dict[str, str]:
        base = f"https://gateway.pinata.cloud/ipfs/{cid}"
        return {
            "directory_cid": cid,
            "directory_url": base,
            "component_definition": f"{base}/component-definition.json",
            "assessment_plan": f"{base}/assessment-plan.json",
            "assessment_results": f"{base}/assessment-results.json",
            "poam": f"{base}/poam.json",
        }

    payload: Dict[str, Any] = {"artifact_hash": artifact_hash}
    if verified_cid:
        payload["verified"] = mk_urls(verified_cid)
    if initial_cid:
        payload["initial"] = mk_urls(initial_cid)

    if not payload.get("verified") and not payload.get("initial"):
        raise HTTPException(status_code=404, detail="No OSCAL CIDs stored for this artifact")

    return payload

@router.post("/submit", summary="Submit artifact for verification")
async def submit_verification(
    artifact_id: str = Form(...),
    profile_id: str = Form(...),
    wallet_address: str = Form(...),
    ai_analyzer: GeminiAnalyzer = Depends(get_ai_analyzer),
    oscal_gen: OSCALGenerator = Depends(get_oscal_generator),
    blockchain: AlgorandService = Depends(get_blockchain_service),
    ipfs: IPFSService = Depends(get_ipfs_service),
):
    """
    Submit an artifact for AI analysis and blockchain verification
    
    - **artifact_id**: ID of the uploaded artifact
    - **profile_id**: ID of the compliance profile to verify against
    - **wallet_address**: Algorand wallet address of the submitter
    """
    # Check if artifact exists
    from .artifacts import artifacts_store
    if artifact_id not in artifacts_store:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Get artifact
    artifact = artifacts_store[artifact_id]
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Create verification request
    verification_requests[request_id] = {
        "artifact_id": artifact_id,
        "profile_id": profile_id,
        "wallet_address": wallet_address,
        "status": "pending",
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "progress": 0
    }
    
    # Start async verification process
    # For PoC, we'll simulate this with a background task
    # In production, use Celery or similar task queue
    verification_requests[request_id]["task_id"] = "mock-task-id"
    
    # Return verification request ID
    return {
        "verification_request_id": request_id,
        "status": "submitted",
        "artifact_hash": artifact["hash"]
    }

@router.get("/{request_id}/status", summary="Get verification status")
async def get_verification_status(request_id: str):
    """
    Get the status of a verification request
    
    - **request_id**: ID of the verification request
    """
    if request_id not in verification_requests:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    request = verification_requests[request_id]
    
    # For PoC, simulate progress
    # In production, get real progress from background task
    if request["status"] == "pending":
        # Increment progress by 10% each time status is checked
        request["progress"] = min(90, request.get("progress", 0) + 10)
        
        # If progress is 90%, consider it completed
        if request["progress"] >= 90:
            request["status"] = "completed"
            request["progress"] = 100
            request["completed_at"] = datetime.datetime.now().isoformat()
            request["blockchain_txn_id"] = "mock-txn-id"
            request["oscal_cid"] = "mock-ipfs-cid"
    
    return {
        "request_id": request_id,
        "status": request["status"],
        "progress": request["progress"],
        "created_at": request["created_at"],
        "updated_at": datetime.datetime.now().isoformat(),
        "completed_at": request.get("completed_at"),
        "blockchain_txn_id": request.get("blockchain_txn_id"),
        "oscal_cid": request.get("oscal_cid")
    }

@router.post("/blockchain-integration", summary="Process artifact through blockchain integration")
async def blockchain_integration(
    artifact_data: Dict[str, Any] = Body(...),
    profile_id: str = Body("default"),
    contract_service: ContractIntegrationService = Depends(get_contract_integration_service)
):
    """
    Process an artifact through the full verification pipeline and store results on-chain
    
    - **artifact_data**: Complete artifact data including hash and analysis results
    - **profile_id**: Optional profile ID to use for verification (default: 'default')
    """
    
    # Validate required fields
    if not artifact_data.get("hash"):
        raise HTTPException(status_code=400, detail="Artifact hash is required")
    
    if not artifact_data.get("name"):
        raise HTTPException(status_code=400, detail="Artifact name is required")
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    try:
        # Process artifact through contract integration service
        result = await contract_service.process_artifact(artifact_data, profile_id)
        
        # Store result in verification_requests (for PoC)
        verification_requests[request_id] = {
            "status": "completed",
            "progress": 100,
            "created_at": datetime.datetime.now().isoformat(),
            "completed_at": datetime.datetime.now().isoformat(),
            "blockchain_txn_id": "actual-txn-from-contract",
            "oscal_cid": result.get("verified_oscal_cid"),
            "registry_tx_id": result.get("registry_tx_id"),
            "registry_tx_url": result.get("registry_tx_url"),
            "oracle_tx_id": result.get("oracle_tx_id"),
            "oracle_tx_url": result.get("oracle_tx_url"),
            "result": result
        }
        
        # Return the full result with request ID
        return {
            "request_id": request_id,
            "status": "success",
            "artifact_hash": artifact_data.get("hash"),
            "profile_id": profile_id,
            "oscal_cid": result.get("verified_oscal_cid"),
            "oscal_url": result.get("verified_oscal_url"),
            "registry_app_id": result.get("registry_app_id"),
            "oracle_app_id": result.get("oracle_app_id"),
            "registry_tx_id": result.get("registry_tx_id"),
            "registry_tx_url": result.get("registry_tx_url"),
            "oracle_tx_id": result.get("oracle_tx_id"),
            "oracle_tx_url": result.get("oracle_tx_url"),
            "compliance_score": result.get("compliance_score", 0),
            "message": "Artifact successfully processed through blockchain integration"
        }
        
    except Exception as e:
        # Log the error
        print(f"Error in blockchain integration: {str(e)}")
        
        # Return error response
        raise HTTPException(status_code=500, detail=f"Integration error: {str(e)}")

@router.post("/blockchain-integration/by-artifact/{artifact_id}", summary="Process artifact through blockchain integration by artifact_id")
async def blockchain_integration_by_artifact(
    artifact_id: str,
    profile_id: str = Body("default"),
    contract_service: ContractIntegrationService = Depends(get_contract_integration_service),
    analyzer: SmartContractAnalyzer = Depends(get_smart_contract_analyzer),
    storage: StorageService = Depends(get_storage_service),
):
    """
    Convenience endpoint: look up an uploaded artifact by ID and run the full
    verification pipeline (AI → OSCAL → IPFS → Algorand) without the caller
    needing to construct artifact_data manually.

    - **artifact_id**: ID returned from /api/v1/artifacts/upload
    - **profile_id**: Optional profile ID (default: 'default')
    """

    # Lazy import to avoid circular dependency at module import time
    from .artifacts import artifacts_store

    # Validate artifact
    if artifact_id not in artifacts_store:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact = artifacts_store[artifact_id]

    # Build minimal artifact_data required by the integration flow
    artifact_data: Dict[str, Any] = {
        "hash": artifact.get("hash"),
        "name": artifact.get("filename") or artifact_id,
        "type": artifact.get("type"),
        # Include any other useful metadata if present
        "description": artifact.get("description"),
        "dependencies": artifact.get("dependencies"),
    }

    if not artifact_data.get("hash"):
        raise HTTPException(status_code=400, detail="Stored artifact is missing hash")

    # If this is a Solidity smart contract, analyze it and attach results
    try:
        if artifact.get("type") == "smart_contract" and artifact.get("language") == "solidity":
            raw = await storage.get_artifact(artifact_id)
            if raw:
                src = raw.decode("utf-8", errors="ignore")
                analysis = analyzer.analyze_solidity(src)
                artifact_data["analysis_results"] = analysis
    except Exception:
        # Proceed without analysis if anything fails (graceful degradation)
        artifact_data.setdefault("analysis_results", {})

    # Generate unique request ID
    request_id = str(uuid.uuid4())

    try:
        result = await contract_service.process_artifact(artifact_data, profile_id)

        # Store quick reference (PoC in-memory)
        verification_requests[request_id] = {
            "status": "completed",
            "progress": 100,
            "created_at": datetime.datetime.now().isoformat(),
            "completed_at": datetime.datetime.now().isoformat(),
            "blockchain_txn_id": "actual-txn-from-contract",
            "oscal_cid": result.get("verified_oscal_cid"),
            "result": result,
            "artifact_id": artifact_id,
            "profile_id": profile_id,
            "registry_tx_id": result.get("registry_tx_id"),
            "registry_tx_url": result.get("registry_tx_url"),
            "oracle_tx_id": result.get("oracle_tx_id"),
            "oracle_tx_url": result.get("oracle_tx_url"),
        }

        return {
            "request_id": request_id,
            "status": "success",
            "artifact_id": artifact_id,
            "artifact_hash": artifact_data.get("hash"),
            "profile_id": profile_id,
            "oscal_cid": result.get("verified_oscal_cid"),
            "oscal_url": result.get("verified_oscal_url"),
            "registry_app_id": result.get("registry_app_id"),
            "oracle_app_id": result.get("oracle_app_id"),
            "registry_tx_id": result.get("registry_tx_id"),
            "registry_tx_url": result.get("registry_tx_url"),
            "oracle_tx_id": result.get("oracle_tx_id"),
            "oracle_tx_url": result.get("oracle_tx_url"),
            "compliance_score": result.get("compliance_score", 0),
            "message": "Artifact successfully processed through blockchain integration",
        }

    except Exception as e:
        print(f"Error in blockchain integration by artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration error: {str(e)}")

@router.get("/{request_id}/results", summary="Get verification results")
async def get_verification_results(request_id: str):
    """
    Get the results of a completed verification
    
    - **request_id**: ID of the verification request
    """
    if request_id not in verification_requests:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    request = verification_requests[request_id]
    
    if request["status"] != "completed":
        raise HTTPException(status_code=400, detail="Verification not completed yet")
    
    # For PoC, generate mock results
    results = {
        "request_id": request_id,
        "artifact_id": request["artifact_id"],
        "profile_id": request["profile_id"],
        "wallet_address": request["wallet_address"],
        "compliance_score": 85,
        "controls": {
            "total": 50,
            "passed": 42,
            "failed": 8,
            "not_applicable": 0
        },
        "blockchain_proof": {
            "txn_id": request.get("blockchain_txn_id"),
            "timestamp": request.get("completed_at"),
            "network": "algorand-testnet"
        },
        "oscal_documents": {
            "component_definition": {
                "cid": f"{request.get('oscal_cid')}/component-definition.json",
                "url": f"https://ipfs.io/ipfs/{request.get('oscal_cid')}/component-definition.json"
            },
            "assessment_plan": {
                "cid": f"{request.get('oscal_cid')}/assessment-plan.json",
                "url": f"https://ipfs.io/ipfs/{request.get('oscal_cid')}/assessment-plan.json"
            },
            "assessment_results": {
                "cid": f"{request.get('oscal_cid')}/assessment-results.json",
                "url": f"https://ipfs.io/ipfs/{request.get('oscal_cid')}/assessment-results.json"
            },
            "poam": {
                "cid": f"{request.get('oscal_cid')}/poam.json",
                "url": f"https://ipfs.io/ipfs/{request.get('oscal_cid')}/poam.json"
            }
        }
    }
    
    return results

@router.get("/{request_id}/download", summary="Download OSCAL documents")
async def download_oscal_documents(request_id: str):
    """
    Get download links for OSCAL documents
    
    - **request_id**: ID of the verification request
    """
    if request_id not in verification_requests:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    request = verification_requests[request_id]
    
    if request["status"] != "completed":
        raise HTTPException(status_code=400, detail="Verification not completed yet")
    
    # For PoC, return mock download links
    return {
        "download_links": {
            "all": f"/api/v1/verification/{request_id}/download/all",
            "component_definition": f"/api/v1/verification/{request_id}/download/component-definition",
            "assessment_plan": f"/api/v1/verification/{request_id}/download/assessment-plan",
            "assessment_results": f"/api/v1/verification/{request_id}/download/assessment-results",
            "poam": f"/api/v1/verification/{request_id}/download/poam"
        }
    }
