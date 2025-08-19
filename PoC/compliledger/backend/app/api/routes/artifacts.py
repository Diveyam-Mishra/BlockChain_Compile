from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Optional, Dict, Any
import uuid
import json

# Import services
from app.services.artifact_processor import ArtifactProcessor
from app.services.storage_service import StorageService

# Create router
router = APIRouter()

# In-memory storage for PoC (would use database in production)
artifacts_store = {}

def get_artifact_processor():
    """Dependency for artifact processor service"""
    return ArtifactProcessor()

def get_storage_service():
    """Dependency for storage service"""
    return StorageService()

@router.post("/upload", summary="Upload an artifact for analysis")
async def upload_artifact(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    processor: ArtifactProcessor = Depends(get_artifact_processor),
    storage: StorageService = Depends(get_storage_service),
):
    """
    Upload an artifact (SBOM or Smart Contract) for analysis
    
    - **file**: SBOM JSON file or Smart Contract source code
    - **description**: Optional description of the artifact
    """
    try:
        content = await file.read()
        
        # Process the artifact based on file type
        if file.filename.endswith((".json", ".xml")) and "sbom" in file.filename.lower():
            # Parse as SBOM
            artifact = await processor.parse_sbom(content)
        else:
            # Parse as smart contract
            artifact = await processor.parse_smart_contract(content.decode('utf-8'))
        
        # Generate unique artifact ID
        artifact_id = str(uuid.uuid4())
        
        # Generate artifact hash
        artifact_hash = await processor.generate_artifact_hash(content)
        
        # Add metadata
        artifact["id"] = artifact_id
        artifact["hash"] = artifact_hash
        artifact["filename"] = file.filename
        artifact["description"] = description
        
        # Extract dependencies
        artifact["dependencies"] = await processor.extract_dependencies(artifact)
        
        # Store artifact content
        await storage.store_artifact(artifact_id, content)
        
        # Store artifact metadata
        artifacts_store[artifact_id] = artifact
        
        return {
            "artifact_id": artifact_id,
            "artifact_hash": artifact_hash,
            "type": artifact["type"],
            "status": "parsed",
            "filename": file.filename,
            "dependencies_count": len(artifact["dependencies"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process artifact: {str(e)}")

@router.get("/", summary="List all uploaded artifacts")
async def list_artifacts():
    """
    Get a list of all uploaded artifacts
    """
    artifacts_list = []
    
    for artifact_id, artifact in artifacts_store.items():
        artifacts_list.append({
            "artifact_id": artifact_id,
            "type": artifact["type"],
            "filename": artifact["filename"],
            "hash": artifact["hash"],
            "description": artifact.get("description")
        })
    
    return {
        "artifacts": artifacts_list,
        "count": len(artifacts_list)
    }

@router.get("/{artifact_id}", summary="Get artifact details")
async def get_artifact(artifact_id: str):
    """
    Get detailed information about a specific artifact
    
    - **artifact_id**: ID of the artifact to retrieve
    """
    if artifact_id not in artifacts_store:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    artifact = artifacts_store[artifact_id]
    
    # Remove raw content for response
    artifact_response = {k: v for k, v in artifact.items() if k != "content"}
    
    return artifact_response

@router.get("/profiles", summary="Get available compliance profiles")
async def get_profiles():
    """
    Get list of available compliance profiles for verification
    """
    # Static list of profiles for PoC
    profiles = [
        {
            "id": "nist-800-53-low",
            "name": "NIST 800-53 (Low)",
            "description": "NIST 800-53 Low-Impact Baseline",
            "controls_count": 115
        },
        {
            "id": "nist-800-53-moderate",
            "name": "NIST 800-53 (Moderate)",
            "description": "NIST 800-53 Moderate-Impact Baseline",
            "controls_count": 261
        },
        {
            "id": "nist-800-53-high",
            "name": "NIST 800-53 (High)",
            "description": "NIST 800-53 High-Impact Baseline",
            "controls_count": 325
        }
    ]
    
    return {"profiles": profiles}
