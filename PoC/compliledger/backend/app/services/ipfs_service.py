import os
import json
import httpx
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union

# Load environment variables
load_dotenv()

class IPFSService:
    """
    Service for pinning documents to IPFS using Pinata
    """
    
    def __init__(self):
        """Initialize IPFS service with API credentials"""
        self.api_key = os.getenv("PINATA_API_KEY")
        self.api_secret = os.getenv("PINATA_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("PINATA_API_KEY and PINATA_API_SECRET environment variables are required")
        
        self.base_url = "https://api.pinata.cloud"
        # Do not set Content-Type globally; json vs multipart differ
        self.base_headers = {
            "pinata_api_key": self.api_key,
            "pinata_secret_api_key": self.api_secret,
        }
    
    async def pin_json(self, data: Any, name: str, artifact_hash: str) -> Dict[str, str]:
        """
        Pin JSON data to IPFS
        
        Args:
            data: JSON-serializable data to pin
            name: Name for the pin
            artifact_hash: Hash of the artifact for metadata
            
        Returns:
            Dictionary with IPFS hash (CID) and URL
        """
        try:
            # Prepare request body
            body = {
                "pinataContent": data,
                "pinataMetadata": {
                    "name": name,
                    "keyvalues": {
                        "artifactHash": artifact_hash,
                        "service": "compliledger",
                        "timestamp": str(int(datetime.now().timestamp()))
                    }
                }
            }
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/pinning/pinJSONToIPFS",
                    headers={**self.base_headers, "Content-Type": "application/json"},
                    json=body
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to pin to IPFS: {response.text}")
                
                result = response.json()
                
                return {
                    "ipfs_cid": result["IpfsHash"],
                    "ipfs_url": f"https://gateway.pinata.cloud/ipfs/{result['IpfsHash']}"
                }
                
        except Exception as e:
            # For PoC purposes, return mock data on failure
            import hashlib
            mock_hash = hashlib.sha256(f"{name}-{artifact_hash}".encode()).hexdigest()[:16]
            
            print(f"IPFS pinning error (returning mock CID): {str(e)}")
            
            return {
                "ipfs_cid": f"mock-ipfs-{mock_hash}",
                "ipfs_url": f"https://gateway.pinata.cloud/ipfs/mock-ipfs-{mock_hash}"
            }

    async def pin_file(
        self,
        file_bytes: bytes,
        name: str,
        artifact_hash: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Pin raw file bytes to IPFS via Pinata's pinFileToIPFS.

        Args:
            file_bytes: Raw file content
            name: Display name for Pinata pin metadata
            artifact_hash: Associated artifact hash for traceability
            filename: Optional filename for multipart form
            content_type: Optional MIME type

        Returns:
            Dict with ipfs_cid and ipfs_url
        """
        try:
            files = {
                "file": (
                    filename or name,
                    file_bytes,
                    content_type or "application/octet-stream",
                )
            }

            # Pinata allows metadata/options via separate fields in multipart
            metadata = {
                "name": name,
                "keyvalues": {
                    "artifactHash": artifact_hash,
                    "service": "compliledger",
                    "timestamp": str(int(datetime.now().timestamp())),
                },
            }

            data = {
                "pinataMetadata": json.dumps(metadata),
                # You may pass pinataOptions if needed
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/pinning/pinFileToIPFS",
                    headers=self.base_headers,
                    files=files,
                    data=data,
                )

                if response.status_code != 200:
                    raise Exception(f"Failed to pin file to IPFS: {response.text}")

                result = response.json()
                return {
                    "ipfs_cid": result["IpfsHash"],
                    "ipfs_url": f"https://gateway.pinata.cloud/ipfs/{result['IpfsHash']}",
                }
        except Exception as e:
            import hashlib
            mock_hash = hashlib.sha256(f"{name}-{artifact_hash}".encode()).hexdigest()[:16]
            print(f"IPFS file pinning error (returning mock CID): {str(e)}")
            return {
                "ipfs_cid": f"mock-ipfs-file-{mock_hash}",
                "ipfs_url": f"https://gateway.pinata.cloud/ipfs/mock-ipfs-file-{mock_hash}",
            }
    
    async def pin_directory(self, files: Dict[str, Any], dir_name: str, artifact_hash: str) -> Dict[str, str]:
        """
        Pin multiple files as a directory to IPFS
        
        Args:
            files: Dictionary mapping filenames to content
            dir_name: Name for the directory
            artifact_hash: Hash of the artifact for metadata
            
        Returns:
            Dictionary with IPFS hash (CID) and URL for the directory
        """
        try:
            # Create a temporary directory
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write files to temp directory
                for filename, content in files.items():
                    filepath = os.path.join(temp_dir, filename)
                    with open(filepath, "w") as f:
                        f.write(json.dumps(content, indent=2))
                
                # Upload directory using Pinata API
                # Note: In a real implementation, would use multipart form upload
                # For PoC, simulate with a single pin
                
                # Return mock data
                import hashlib
                mock_hash = hashlib.sha256(f"{dir_name}-{artifact_hash}".encode()).hexdigest()[:16]
                
                return {
                    "ipfs_cid": f"mock-ipfs-dir-{mock_hash}",
                    "ipfs_url": f"https://gateway.pinata.cloud/ipfs/mock-ipfs-dir-{mock_hash}"
                }
                
        except Exception as e:
            # For PoC purposes, return mock data on failure
            import hashlib
            mock_hash = hashlib.sha256(f"{dir_name}-{artifact_hash}".encode()).hexdigest()[:16]
            
            print(f"IPFS directory pinning error (returning mock CID): {str(e)}")
            
            return {
                "ipfs_cid": f"mock-ipfs-dir-{mock_hash}",
                "ipfs_url": f"https://gateway.pinata.cloud/ipfs/mock-ipfs-dir-{mock_hash}"
            }
    
    async def pin_oscal_documents(self, 
                                 oscal_bundle: Dict[str, Any], 
                                 artifact_hash: str) -> Dict[str, str]:
        """
        Pin OSCAL documents to IPFS
        
        Args:
            oscal_bundle: Bundle of OSCAL documents
            artifact_hash: Hash of the artifact
            
        Returns:
            Dictionary with IPFS hash (CID) and URLs for each document
        """
        # Prepare files dictionary
        files = {
            "component-definition.json": oscal_bundle["component_definition"],
            "assessment-plan.json": oscal_bundle["assessment_plan"],
            "assessment-results.json": oscal_bundle["assessment_results"],
            "poam.json": oscal_bundle["poam"]
        }
        
        # Pin directory
        result = await self.pin_directory(
            files=files,
            dir_name=f"oscal-{artifact_hash[:8]}",
            artifact_hash=artifact_hash
        )
        
        # Build document URLs
        cid = result["ipfs_cid"]
        base_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
        
        # Return CID and URLs for each document
        return {
            "directory_cid": cid,
            "directory_url": base_url,
            "component_definition": f"{base_url}/component-definition.json",
            "assessment_plan": f"{base_url}/assessment-plan.json",
            "assessment_results": f"{base_url}/assessment-results.json",
            "poam": f"{base_url}/poam.json"
        }

# Helper function to import datetime only when needed
def import_datetime():
    import datetime
    return datetime.datetime.now()
