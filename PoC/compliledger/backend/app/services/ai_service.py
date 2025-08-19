#!/usr/bin/env python3

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
import httpx
import sys

# Import the control explorer functionality
sys_path = os.path.dirname(os.path.abspath(__file__))
if sys_path not in sys.path:
    sys.path.append(sys_path)
from resources.explore_controls import find_relevant_controls_for_smart_contract, load_default_controls

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisLevel(str, Enum):
    """Analysis level for AI service"""
    BASIC = "basic"          # Basic checks
    STANDARD = "standard"    # Standard security analysis
    ADVANCED = "advanced"    # In-depth analysis


class AIService:
    """Service for AI-powered SBOM and artifact analysis"""
    
    def __init__(self):
        """Initialize AI service"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.api_url = os.getenv("GEMINI_API_URL", f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent")
        self.enabled = self.api_key is not None
        
        logger.info(f"AI Service initialized with model: {self.model}")
        
        # Load security control mappings
        self.security_controls = self._load_security_controls()
        logger.info(f"Loaded {len(self.security_controls)} security controls")
    
    def _load_security_controls(self):
        """Load security control mappings from JSON file"""
        try:
            return load_default_controls()
        except Exception as e:
            logger.warning(f"Failed to load security controls: {e}")
            return {}
    
    async def analyze_sbom(self, 
                        sbom_content: Dict[str, Any], 
                        level: AnalysisLevel = AnalysisLevel.STANDARD) -> Dict[str, Any]:
        """Analyze SBOM for security issues"""
        if not self.enabled:
            logger.warning("AI service not enabled (missing API key)")
            return self._generate_mock_analysis_results(sbom_content, level)
        
        try:
            # Create analysis prompt based on SBOM content
            prompt = self._create_sbom_analysis_prompt(sbom_content, level)
            
            # Call Gemini API
            analysis_results = await self._call_gemini_api(prompt)
            
            # Post-process and structure the results
            processed_results = self._process_analysis_results(analysis_results)
            
            # Return standardized result format
            return processed_results
        except Exception as e:
            logger.error(f"Error analyzing SBOM with AI: {str(e)}")
            # Return mock results in case of error
            return self._generate_mock_analysis_results(sbom_content, level)
    
    async def analyze_artifact(self, 
                           artifact_path: str,
                           metadata: Dict[str, Any],
                           level: AnalysisLevel = AnalysisLevel.STANDARD) -> Dict[str, Any]:
        """Analyze artifact (package, binary, etc.) for security issues"""
        if not self.enabled:
            logger.warning("AI service not enabled (missing API key)")
            return self._generate_mock_analysis_results(metadata, level)
            
        try:
            # For PoC, we're only analyzing the metadata, not the actual artifact
            # In a real implementation, this would extract features from the artifact
            prompt = self._create_artifact_analysis_prompt(metadata, level)
            
            # Call Gemini API
            analysis_results = await self._call_gemini_api(prompt)
            
            # Post-process and structure the results
            processed_results = self._process_analysis_results(analysis_results)
            
            # Return standardized result format
            return processed_results
        except Exception as e:
            logger.error(f"Error analyzing artifact with AI: {str(e)}")
            # Return mock results in case of error
            return self._generate_mock_analysis_results(metadata, level)
    
    def analyze_smart_contract(self, contract_code: str, num_controls: int = 10) -> Dict[str, Any]:
        """Analyze smart contract code and map relevant security controls"""
        try:
            # Find relevant security controls for the smart contract
            logger.info(f"Finding relevant controls for smart contract analysis")
            relevant_controls = find_relevant_controls_for_smart_contract(contract_code, num_controls)
            
            # Format the results
            control_mappings = []
            for control_id, control, score in relevant_controls:
                control_mappings.append({
                    "control_id": control_id,
                    "title": control.get("title", "Unknown"),
                    "category": control.get("category", "Security"),
                    "criticality": control.get("criticality", "medium"),
                    "relevance_score": score,
                    "description": control.get("description", "No description available")
                })
            
            # Generate response with contract analysis and control mappings
            result = {
                "analyzed_contract_length": len(contract_code),
                "total_controls_mapped": len(control_mappings),
                "control_mappings": control_mappings,
                "recommendation": self._generate_contract_recommendations(control_mappings, contract_code)
            }
            
            logger.info(f"Smart contract analysis complete, mapped {len(control_mappings)} controls")
            return result
        except Exception as e:
            logger.error(f"Error analyzing smart contract: {e}")
            return {
                "error": f"Failed to analyze smart contract: {str(e)}",
                "analyzed_contract_length": len(contract_code),
                "total_controls_mapped": 0,
                "control_mappings": []
            }
    
    def _create_sbom_analysis_prompt(self, 
                                sbom_content: Dict[str, Any], 
                                level: AnalysisLevel) -> str:
        """Create analysis prompt for SBOM"""
        # Extract relevant information from SBOM
        components = sbom_content.get("components", [])
        metadata = sbom_content.get("metadata", {})
        
        # Base prompt with instruction
        prompt = f"""
        You are a cybersecurity expert specializing in software supply chain security analysis. 
        Analyze this SBOM (Software Bill of Materials) for security issues and compliance with NIST standards.
        
        SBOM Information:
        - Name: {metadata.get('name', 'Unknown')}
        - Format: {metadata.get('format', 'Unknown')}
        - Number of Components: {len(components)}
        """
        
        # Add components information based on analysis level
        if level == AnalysisLevel.BASIC:
            # Add just a summary of components
            prompt += "\nKey Components:\n"
            for i, component in enumerate(components[:10]):  # Limit to 10 components for basic analysis
                prompt += f"- {component.get('name', 'Unknown')}: {component.get('version', 'Unknown')}\n"
        else:
            # Add detailed component information
            prompt += "\nDetailed Components:\n"
            component_limit = 50 if level == AnalysisLevel.ADVANCED else 25
            for i, component in enumerate(components[:component_limit]):
                prompt += f"- Name: {component.get('name', 'Unknown')}\n"
                prompt += f"  Version: {component.get('version', 'Unknown')}\n"
                prompt += f"  Type: {component.get('type', 'Unknown')}\n"
                if "publisher" in component:
                    prompt += f"  Publisher: {component.get('publisher', 'Unknown')}\n"
                if "purl" in component:
                    prompt += f"  PURL: {component.get('purl', 'Unknown')}\n"
                if "licenses" in component:
                    licenses = component.get("licenses", [])
                    license_names = [lic.get("license", {}).get("name", "Unknown") for lic in licenses]
                    prompt += f"  Licenses: {', '.join(license_names)}\n"
                
                # Advanced level includes vulnerabilities if present
                if level == AnalysisLevel.ADVANCED:
                    if "vulnerabilities" in component:
                        vulns = component.get("vulnerabilities", [])
                        prompt += f"  Vulnerabilities: {len(vulns)}\n"
                        for vuln in vulns[:3]:  # Limit to 3 vulns per component
                            prompt += f"    - ID: {vuln.get('id', 'Unknown')}\n"
                            prompt += f"      Severity: {vuln.get('severity', 'Unknown')}\n"
        
        # Analysis instructions based on level
        prompt += f"""
        
        Analysis Level: {level.value.upper()}
        
        Please provide the following analysis:
        1. Security Risk Assessment: Identify potential security risks in the components
        2. Compliance Status: Evaluate against NIST 800-218 (SSDF) controls and standards
        3. Recommendations: Provide actionable recommendations to address identified issues
        4. Overall Score: Assign a compliance score (0-100) based on your analysis
        
        Format your response as structured JSON with the following sections:
        - risk_assessment: Array of identified risks with severity levels
        - compliance_status: Mapping of NIST controls to compliance status (pass/fail)
        - recommendations: Array of actionable recommendations
        - overall_score: Numerical score (0-100)
        - findings: Array of detailed findings with control_id, severity, description, and recommendation
        
        Make sure your response is valid JSON that can be parsed.
        """
        
        return prompt
    
    def _create_artifact_analysis_prompt(self, 
                                     metadata: Dict[str, Any], 
                                     level: AnalysisLevel) -> str:
        """Create analysis prompt for artifact"""
        # Extract metadata information
        artifact_type = metadata.get("type", "unknown")
        artifact_name = metadata.get("name", "unknown")
        
        # Base prompt with instruction
        prompt = f"""
        You are a cybersecurity expert specializing in software security analysis.
        Analyze this software artifact metadata for security issues and compliance with NIST standards.
        
        Artifact Information:
        - Name: {artifact_name}
        - Type: {artifact_type}
        """
        
        # Add metadata details
        for key, value in metadata.items():
            if key not in ["name", "type"] and isinstance(value, (str, int, float, bool)):
                prompt += f"- {key}: {value}\n"
        
        # Analysis instructions based on level
        prompt += f"""
        
        Analysis Level: {level.value.upper()}
        
        Please provide the following analysis:
        1. Security Risk Assessment: Identify potential security risks based on the metadata
        2. Compliance Status: Evaluate against NIST 800-218 (SSDF) controls and standards
        3. Recommendations: Provide actionable recommendations to address identified issues
        4. Overall Score: Assign a compliance score (0-100) based on your analysis
        
        Format your response as structured JSON with the following sections:
        - risk_assessment: Array of identified risks with severity levels
        - compliance_status: Mapping of NIST controls to compliance status (pass/fail)
        - recommendations: Array of actionable recommendations
        - overall_score: Numerical score (0-100)
        - findings: Array of detailed findings with control_id, severity, description, and recommendation
        
        Make sure your response is valid JSON that can be parsed.
        """
        
        return prompt
    
    async def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API for analysis"""
        if not self.api_key:
            raise ValueError("Gemini API key not set")
        
        # Prepare request payload
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Lower temperature for more deterministic outputs
                "topP": 0.95,
                "topK": 40
            }
        }
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} {response.text}")
                raise Exception(f"Gemini API error: {response.status_code}")
            
            # Parse response
            response_data = response.json()
            
            # Extract generated content text
            try:
                text_content = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Extract JSON data from the response text
                json_str = self._extract_json_from_text(text_content)
                return json.loads(json_str)
            except Exception as e:
                logger.error(f"Error parsing Gemini response: {str(e)}")
                raise Exception(f"Failed to parse Gemini response: {str(e)}")
    
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON string from text response"""
        # Try to find JSON content between triple backticks
        import re
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        matches = re.findall(json_pattern, text)
        
        if matches:
            return matches[0]
        
        # If no JSON code block is found, try to find anything that looks like JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
            return text.strip()
        
        # If all else fails, return an error object
        return '{"error": "Could not extract valid JSON from response"}'
    
    def _process_analysis_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize analysis results"""
        # Ensure required sections exist with resilient defaults
        processed = {
            "risk_assessment": raw_results.get("risk_assessment", []) or [],
            "compliance_status": raw_results.get("compliance_status", {}) or {},
            "recommendations": raw_results.get("recommendations", []) or [],
            "overall_score": raw_results.get("overall_score", 0),
            "findings": raw_results.get("findings", []) or []
        }

        # Guard against unexpected types
        if not isinstance(processed["risk_assessment"], list):
            processed["risk_assessment"] = []
        if not isinstance(processed["recommendations"], list):
            processed["recommendations"] = []
        if not isinstance(processed["findings"], list):
            processed["findings"] = []
        if not isinstance(processed["compliance_status"], dict):
            processed["compliance_status"] = {}

        # Normalize compliance_status values to 'pass'/'fail'
        normalized_cs = {}
        for k, v in processed["compliance_status"].items():
            if isinstance(v, bool):
                normalized_cs[k] = "pass" if v else "fail"
            elif isinstance(v, str):
                val = v.strip().lower()
                if val in {"pass", "passed", "true", "yes"}:
                    normalized_cs[k] = "pass"
                elif val in {"fail", "failed", "false", "no"}:
                    normalized_cs[k] = "fail"
                else:
                    # Treat unknown as fail-safe default
                    normalized_cs[k] = "fail"
            else:
                # Non-string, non-boolean -> default to fail
                normalized_cs[k] = "fail"
        processed["compliance_status"] = normalized_cs
        
        # Calculate controls passed/failed
        controls_total = len(processed["compliance_status"])
        controls_passed = sum(1 for status in processed["compliance_status"].values() 
                              if isinstance(status, str) and status.lower() == "pass")
        
        # Add calculated metrics
        processed["controls_total"] = controls_total
        processed["controls_passed"] = controls_passed
        processed["controls_failed"] = controls_total - controls_passed
        
        # Ensure overall_score is an integer between 0-100
        try:
            score = int(processed["overall_score"])
            processed["overall_score"] = max(0, min(100, score))
        except (ValueError, TypeError):
            processed["overall_score"] = 0
        
        return processed
    
    def _generate_mock_analysis_results(self, 
                                   content: Dict[str, Any], 
                                   level: AnalysisLevel) -> Dict[str, Any]:
        """Generate mock analysis results for PoC"""
        # Different scores based on analysis level
        if level == AnalysisLevel.BASIC:
            score = 65
            controls_passed = 6
            controls_failed = 2
        elif level == AnalysisLevel.STANDARD:
            score = 85
            controls_passed = 8
            controls_failed = 2
        else:  # ADVANCED
            score = 75
            controls_passed = 10
            controls_failed = 4
        
        # Generate mock findings
        findings = [
            {
                "control_id": "PW.4.1",
                "severity": "medium",
                "description": "Insufficient integrity verification mechanisms for third-party components",
                "recommendation": "Implement digital signature verification for all third-party components"
            }
        ]
        
        if level != AnalysisLevel.BASIC:
            findings.append({
                "control_id": "PO.5.2",
                "severity": "high",
                "description": "Missing vulnerability tracking and response process",
                "recommendation": "Establish a vulnerability disclosure and response policy"
            })
        
        if level == AnalysisLevel.ADVANCED:
            findings.extend([
                {
                    "control_id": "PS.3.2",
                    "severity": "critical",
                    "description": "Critical components lack proper security vetting",
                    "recommendation": "Implement enhanced security reviews for critical components"
                },
                {
                    "control_id": "PW.7.1",
                    "severity": "low",
                    "description": "Inconsistent configuration management across environments",
                    "recommendation": "Standardize configuration management practices"
                }
            ])
        
        # Generate mock compliance status
        compliance_status = {
            "PW.4.1": "fail",
            "PO.1.1": "pass",
            "PO.3.2": "pass",
            "PS.1.1": "pass",
            "PS.2.1": "pass",
            "PS.3.1": "pass"
        }
        
        if level != AnalysisLevel.BASIC:
            compliance_status.update({
                "PO.5.2": "fail",
                "PW.2.1": "pass",
                "PW.8.2": "pass"
            })
        
        if level == AnalysisLevel.ADVANCED:
            compliance_status.update({
                "PS.3.2": "fail",
                "PW.7.1": "fail",
                "PO.4.1": "pass",
                "PO.5.1": "pass",
                "PW.1.2": "pass",
                "PW.6.2": "pass"
            })
        
        # Return mock results
        return {
            "risk_assessment": [
                {"risk": "Insufficient verification of third-party components", "severity": "medium"},
                {"risk": "Lack of vulnerability management process", "severity": "high"}
            ],
            "compliance_status": compliance_status,
            "recommendations": [
                "Implement digital signature verification for all components",
                "Establish a vulnerability disclosure and response policy",
                "Enhance security review process for critical components"
            ],
            "overall_score": score,
            "controls_total": controls_passed + controls_failed,
            "controls_passed": controls_passed,
            "controls_failed": controls_failed,
            "findings": findings
        }
    
    def _generate_contract_recommendations(self, control_mappings: List[Dict[str, Any]], contract_code: str) -> List[Dict[str, Any]]:
        """Generate recommendations based on mapped controls and contract code"""
        recommendations = []
        
        # Check for high priority control families
        has_supply_chain = any(cm["control_id"].startswith("sr-") for cm in control_mappings)
        has_crypto = any(cm["control_id"].startswith("sc-") for cm in control_mappings)
        has_integrity = any(cm["control_id"].startswith("si-") for cm in control_mappings)
        has_access_control = any(cm["control_id"].startswith("ac-") for cm in control_mappings)
        
        # Add recommendations based on identified control families
        if has_supply_chain:
            recommendations.append({
                "category": "Supply Chain Security",
                "description": "Implement supply chain integrity verification in the smart contract",
                "importance": "high"
            })
        
        if has_crypto:
            recommendations.append({
                "category": "Cryptographic Controls",
                "description": "Ensure cryptographic mechanisms are properly implemented and validated",
                "importance": "high"
            })
        
        if has_integrity:
            recommendations.append({
                "category": "Data Integrity",
                "description": "Implement additional integrity checks for on-chain data",
                "importance": "high"
            })
            
        if has_access_control:
            recommendations.append({
                "category": "Access Management",
                "description": "Review and strengthen access control mechanisms in the contract",
                "importance": "medium"
            })
        
        # Default recommendations if none were generated
        if not recommendations:
            recommendations.append({
                "category": "General Security",
                "description": "Conduct comprehensive security review of the smart contract",
                "importance": "medium"
            })
        
        return recommendations


# Example usage
async def test_ai_service():
    """Test AI service"""
    ai_service = AIService()
    
    # Create sample SBOM for testing
    sample_sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "name": "Test Application",
            "format": "CycloneDX"
        },
        "components": [
            {
                "type": "library",
                "name": "flask",
                "version": "2.0.1",
                "purl": "pkg:pypi/flask@2.0.1",
                "publisher": "Flask Team"
            },
            {
                "type": "library",
                "name": "requests",
                "version": "2.28.1",
                "purl": "pkg:pypi/requests@2.28.1"
            }
        ]
    }
    
    # Test basic analysis
    print("\n===== Basic SBOM Analysis =====")
    basic_results = await ai_service.analyze_sbom(sample_sbom, AnalysisLevel.BASIC)
    print(json.dumps(basic_results, indent=2))
    
    # Test standard analysis
    print("\n===== Standard SBOM Analysis =====")
    standard_results = await ai_service.analyze_sbom(sample_sbom, AnalysisLevel.STANDARD)
    print(json.dumps(standard_results, indent=2))
    
    # Test artifact analysis
    print("\n===== Artifact Analysis =====")
    artifact_metadata = {
        "name": "test-package.tar.gz",
        "type": "source-archive",
        "language": "python",
        "has_signature": False,
        "size_bytes": 1024000
    }
    artifact_results = await ai_service.analyze_artifact("test-package.tar.gz", artifact_metadata)
    print(json.dumps(artifact_results, indent=2))
    
    # Test smart contract analysis
    print("\n===== Smart Contract Analysis =====")
    contract_code = """
    from pyteal import *
    
    def approval_program():
        # Global variables
        global_owner = Bytes("owner")
        global_counter = Bytes("counter")
        
        # Operations
        op_increment = Bytes("inc")
        op_decrement = Bytes("dec")
        
        # Initialize global state
        init = Seq([
            App.globalPut(global_owner, Txn.sender()),
            App.globalPut(global_counter, Int(0)),
            Return(Int(1))
        ])
        
        # Check if sender is the owner
        is_owner = Txn.sender() == App.globalGet(global_owner)
        
        # Handle increment operation
        increment = Seq([
            App.globalPut(global_counter, App.globalGet(global_counter) + Int(1)),
            Return(Int(1))
        ])
        
        # Handle decrement operation
        decrement = Seq([
            App.globalPut(global_counter, App.globalGet(global_counter) - Int(1)),
            Return(Int(1))
        ])
        
        # Main approval program logic
        program = Cond(
            [Txn.application_id() == Int(0), init],
            [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_owner)],
            [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_owner)],
            [Txn.application_args[0] == op_increment, increment],
            [Txn.application_args[0] == op_decrement, decrement]
        )
        
        return program
        
    def clear_state_program():
        return Return(Int(1))
    """
    contract_results = ai_service.analyze_smart_contract(contract_code)
    print(json.dumps(contract_results, indent=2))


if __name__ == "__main__":
    asyncio.run(test_ai_service())
