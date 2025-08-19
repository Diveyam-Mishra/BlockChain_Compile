import hashlib
import json
import re
from typing import Dict, List, Any, Optional

class ArtifactProcessor:
    """
    Service for processing artifacts (SBOMs and smart contracts)
    """
    
    async def parse_sbom(self, file_content: bytes) -> Dict[str, Any]:
        """
        Parse SBOM file content into structured data
        """
        try:
            # Parse JSON content
            sbom_data = json.loads(file_content.decode('utf-8'))
            
            # Detect SBOM format
            sbom_format = self._detect_sbom_format(sbom_data)
            
            # Extract components based on format
            components = self._extract_sbom_components(sbom_data, sbom_format)
            
            # Extract metadata
            metadata = self._extract_sbom_metadata(sbom_data, sbom_format)
            
            return {
                "type": "sbom",
                "format": sbom_format,
                "name": metadata.get("name", "Unnamed SBOM"),
                "version": metadata.get("version", "1.0.0"),
                "components": components,
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Failed to parse SBOM: {str(e)}")
    
    async def parse_smart_contract(self, code: str) -> Dict[str, Any]:
        """
        Parse smart contract code into structured data
        """
        try:
            # Detect language
            language = self._detect_contract_language(code)
            
            # Extract functions
            functions = self._extract_functions(code, language)
            
            # Extract imports/dependencies
            imports = self._extract_imports(code, language)
            
            # Get contract name
            contract_name = self._extract_contract_name(code, language)
            
            return {
                "type": "smart_contract",
                "language": language,
                "name": contract_name,
                "code_size": len(code),
                "functions": functions,
                "imports": imports
            }
        except Exception as e:
            raise ValueError(f"Failed to parse smart contract: {str(e)}")
    
    async def generate_artifact_hash(self, data: bytes) -> str:
        """
        Generate SHA-256 hash of artifact data
        """
        return hashlib.sha256(data).hexdigest()
    
    async def extract_dependencies(self, artifact: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract dependencies from artifact data
        """
        dependencies = []
        
        if artifact["type"] == "sbom":
            for component in artifact.get("components", []):
                dependencies.append({
                    "name": component.get("name", "Unknown"),
                    "version": component.get("version", "Unknown"),
                    "type": component.get("type", "library"),
                    "source": "sbom"
                })
        
        elif artifact["type"] == "smart_contract":
            for imp in artifact.get("imports", []):
                dependencies.append({
                    "name": imp,
                    "version": "latest",
                    "type": "import",
                    "source": "code"
                })
        
        return dependencies
    
    def _detect_sbom_format(self, data: Dict[str, Any]) -> str:
        """
        Detect SBOM format (CycloneDX, SPDX, etc.)
        """
        if "bomFormat" in data and data["bomFormat"] == "CycloneDX":
            return "CycloneDX"
        elif "SPDXID" in data:
            return "SPDX"
        elif "components" in data or "Components" in data:
            return "generic"
        return "unknown"
    
    def _extract_sbom_components(self, data: Dict[str, Any], sbom_format: str) -> List[Dict[str, Any]]:
        """
        Extract components from SBOM based on format
        """
        components = []
        
        if sbom_format == "CycloneDX":
            for component in data.get("components", []):
                components.append({
                    "name": component.get("name", "Unknown"),
                    "version": component.get("version", "Unknown"),
                    "type": component.get("type", "library"),
                    "purl": component.get("purl", "")
                })
        
        elif sbom_format == "SPDX":
            for package in data.get("packages", []):
                components.append({
                    "name": package.get("name", "Unknown"),
                    "version": package.get("versionInfo", "Unknown"),
                    "type": "library",
                    "spdx_id": package.get("SPDXID", "")
                })
        
        elif sbom_format == "generic":
            # Handle "components" or "Components" keys
            comp_list = data.get("components", data.get("Components", []))
            for component in comp_list:
                components.append({
                    "name": component.get("name", component.get("Name", "Unknown")),
                    "version": component.get("version", component.get("Version", "Unknown")),
                    "type": component.get("type", component.get("Type", "library"))
                })
        
        return components
    
    def _extract_sbom_metadata(self, data: Dict[str, Any], sbom_format: str) -> Dict[str, Any]:
        """
        Extract metadata from SBOM based on format
        """
        metadata = {}
        
        if sbom_format == "CycloneDX":
            if "metadata" in data:
                md = data["metadata"]
                metadata = {
                    "name": md.get("component", {}).get("name", "Unknown"),
                    "version": md.get("component", {}).get("version", "1.0.0"),
                    "timestamp": md.get("timestamp", ""),
                    "tools": [t.get("name", "Unknown Tool") for t in md.get("tools", [])]
                }
        
        elif sbom_format == "SPDX":
            metadata = {
                "name": data.get("name", "Unknown"),
                "version": "1.0.0",
                "created": data.get("created", ""),
                "creator": data.get("creator", "")
            }
        
        elif sbom_format == "generic":
            metadata = {
                "name": data.get("name", data.get("Name", "Unknown")),
                "version": data.get("version", data.get("Version", "1.0.0")),
                "description": data.get("description", data.get("Description", ""))
            }
        
        return metadata
    
    def _detect_contract_language(self, code: str) -> str:
        """
        Detect smart contract language based on code patterns
        """
        # Check for Solidity
        if re.search(r'pragma\s+solidity|contract\s+\w+|interface\s+\w+|library\s+\w+', code):
            return "solidity"
        
        # Check for PyTeal
        if re.search(r'from\s+pyteal\s+import|import\s+pyteal|App\.globalPut|Txn\.sender\(\)', code):
            return "pyteal"
        
        # Check for TEAL
        if re.search(r'#pragma\s+version|txn\s+ApplicationID|txn\s+Sender|global|gtxn', code):
            return "teal"
        
        # Default to unknown
        return "unknown"
    
    def _extract_functions(self, code: str, language: str) -> List[Dict[str, str]]:
        """
        Extract function definitions from code
        """
        functions = []
        
        if language == "solidity":
            # Match Solidity functions
            pattern = r'function\s+(\w+)\s*\(([^)]*)\)(?:\s+(?:public|private|external|internal|view|pure))?\s*(?:returns\s*\(([^)]*)\))?\s*(?:{\s*|\s*;)'
            matches = re.finditer(pattern, code)
            
            for match in matches:
                name = match.group(1)
                params = match.group(2).strip()
                returns = match.group(3).strip() if match.group(3) else ""
                
                functions.append({
                    "name": name,
                    "params": params,
                    "returns": returns,
                    "type": "function"
                })
        
        elif language == "pyteal":
            # Match PyTeal functions
            pattern = r'def\s+(\w+)\s*\(([^)]*)\)'
            matches = re.finditer(pattern, code)
            
            for match in matches:
                name = match.group(1)
                params = match.group(2).strip()
                
                functions.append({
                    "name": name,
                    "params": params,
                    "type": "function"
                })
        
        return functions
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """
        Extract import statements from code
        """
        imports = []
        
        if language == "solidity":
            # Match Solidity imports
            pattern = r'import\s+(?:"|\'|{)([^";}]+)'
            matches = re.finditer(pattern, code)
            
            for match in matches:
                imports.append(match.group(1).strip())
        
        elif language == "pyteal":
            # Match PyTeal imports
            pattern = r'(?:from\s+([^\s]+)\s+import|import\s+([^\s]+))'
            matches = re.finditer(pattern, code)
            
            for match in matches:
                imp = match.group(1) if match.group(1) else match.group(2)
                imports.append(imp)
        
        return imports
    
    def _extract_contract_name(self, code: str, language: str) -> str:
        """
        Extract contract name from code
        """
        if language == "solidity":
            # Match Solidity contract name
            match = re.search(r'contract\s+(\w+)', code)
            if match:
                return match.group(1)
        
        elif language == "pyteal":
            # Match class name or main function name
            class_match = re.search(r'class\s+(\w+)', code)
            if class_match:
                return class_match.group(1)
            
            func_match = re.search(r'def\s+(\w+)_program', code)
            if func_match:
                return func_match.group(1)
        
        # Default name if none found
        return "UnnamedContract"
