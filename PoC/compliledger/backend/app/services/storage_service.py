import os
import json
import hashlib
from typing import Dict, Any, Optional
import base64

class StorageService:
    """
    Service for handling artifact storage
    
    For PoC, uses file system storage
    Production version would use a database/blob storage
    """
    
    def __init__(self):
        """Initialize storage service"""
        # Create base storage directory
        self.storage_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "storage"
        )
        
        # Create directories if they don't exist
        self.artifacts_dir = os.path.join(self.storage_dir, "artifacts")
        self.oscal_dir = os.path.join(self.storage_dir, "oscal")
        
        os.makedirs(self.artifacts_dir, exist_ok=True)
        os.makedirs(self.oscal_dir, exist_ok=True)
    
    async def store_artifact(self, artifact_id: str, content: bytes) -> Dict[str, Any]:
        """
        Store artifact content
        
        Args:
            artifact_id: ID of the artifact
            content: Raw content to store
            
        Returns:
            Storage details including path and size
        """
        # Generate filename from ID
        filename = f"{artifact_id}.bin"
        filepath = os.path.join(self.artifacts_dir, filename)
        
        # Write content to file
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Return storage details
        return {
            "path": filepath,
            "size": len(content),
            "id": artifact_id
        }
    
    async def store_oscal_documents(self, artifact_id: str, oscal_bundle: Dict[str, Any]) -> Dict[str, str]:
        """
        Store OSCAL documents for an artifact
        
        Args:
            artifact_id: ID of the artifact
            oscal_bundle: Bundle of OSCAL documents
            
        Returns:
            Dictionary of file paths for each document
        """
        # Create artifact directory
        artifact_dir = os.path.join(self.oscal_dir, artifact_id)
        os.makedirs(artifact_dir, exist_ok=True)
        
        # Store each document
        paths = {}
        
        for doc_type, content in oscal_bundle.items():
            filename = f"{doc_type}.json"
            filepath = os.path.join(artifact_dir, filename)
            
            with open(filepath, "w") as f:
                json.dump(content, f, indent=2)
            
            paths[doc_type] = filepath
        
        return paths
    
    async def get_artifact(self, artifact_id: str) -> Optional[bytes]:
        """
        Retrieve artifact content
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            Raw content of the artifact, or None if not found
        """
        filepath = os.path.join(self.artifacts_dir, f"{artifact_id}.bin")
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "rb") as f:
            return f.read()
    
    async def get_oscal_document(self, artifact_id: str, doc_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OSCAL document
        
        Args:
            artifact_id: ID of the artifact
            doc_type: Type of OSCAL document (component_definition, assessment_plan, etc.)
            
        Returns:
            Document content, or None if not found
        """
        filepath = os.path.join(self.oscal_dir, artifact_id, f"{doc_type}.json")
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r") as f:
            return json.load(f)
    
    async def list_artifacts(self) -> Dict[str, Any]:
        """
        List all stored artifacts
        
        Returns:
            Dictionary of artifact IDs and metadata
        """
        artifacts = {}
        
        for filename in os.listdir(self.artifacts_dir):
            if filename.endswith(".bin"):
                artifact_id = filename.split(".")[0]
                filepath = os.path.join(self.artifacts_dir, filename)
                
                artifacts[artifact_id] = {
                    "id": artifact_id,
                    "path": filepath,
                    "size": os.path.getsize(filepath),
                    "last_modified": os.path.getmtime(filepath)
                }
        
        return artifacts
    
    async def generate_artifact_hash(self, content: bytes) -> str:
        """
        Generate SHA-256 hash for artifact content
        
        Args:
            content: Raw artifact content
            
        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(content).hexdigest()
    
    async def store_verification_result(self, verification_id: str, result: Dict[str, Any]) -> str:
        """
        Store verification result
        
        Args:
            verification_id: ID of the verification request
            result: Verification result data
            
        Returns:
            Path to stored result
        """
        # Create verification results directory if it doesn't exist
        results_dir = os.path.join(self.storage_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Store result
        filepath = os.path.join(results_dir, f"{verification_id}.json")
        
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)
        
        return filepath
