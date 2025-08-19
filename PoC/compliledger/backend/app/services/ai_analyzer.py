import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# Load environment variables
load_dotenv()

class GeminiAnalyzer:
    """
    Service for AI-powered analysis of artifacts using Google Gemini
    """
    
    def __init__(self):
        """Initialize the Gemini API client"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def analyze_sbom(self, sbom_data: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Analyze SBOM data for compliance against specified profile
        
        Args:
            sbom_data: Parsed SBOM data
            profile_id: ID of compliance profile to check against
            
        Returns:
            Dict containing analysis results
        """
        # Get profile definition
        profile = self._get_profile_definition(profile_id)
        
        # Format prompt for Gemini
        prompt = self._format_sbom_prompt(sbom_data, profile)
        
        # Generate analysis with Gemini
        response = await self._generate_analysis(prompt)
        
        # Parse AI response
        results = self._parse_sbom_analysis(response, profile)
        
        return results
    
    async def analyze_smart_contract(self, contract_data: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Analyze smart contract for security vulnerabilities and compliance
        
        Args:
            contract_data: Parsed smart contract data
            profile_id: ID of compliance profile to check against
            
        Returns:
            Dict containing analysis results
        """
        # Get profile definition
        profile = self._get_profile_definition(profile_id)
        
        # Format prompt for Gemini
        prompt = self._format_contract_prompt(contract_data, profile)
        
        # Generate analysis with Gemini
        response = await self._generate_analysis(prompt)
        
        # Parse AI response
        results = self._parse_contract_analysis(response, profile)
        
        return results
    
    async def _generate_analysis(self, prompt: str) -> str:
        """
        Generate analysis using Gemini API
        """
        try:
            # Use Gemini model to analyze
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Failed to generate AI analysis: {str(e)}")
    
    def _format_sbom_prompt(self, sbom_data: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """
        Format prompt for SBOM analysis
        """
        # Extract important SBOM components
        components = sbom_data.get("components", [])
        component_list = "\n".join([
            f"- Name: {c.get('name', 'Unknown')}, Version: {c.get('version', 'Unknown')}, Type: {c.get('type', 'Unknown')}"
            for c in components[:50]  # Limit to 50 components to avoid token limits
        ])
        
        # Extract controls from profile
        control_list = "\n".join([
            f"- {control['id']}: {control['name']}"
            for control in profile.get("controls", [])
        ])
        
        # Construct the prompt
        prompt = f"""
        You are a cybersecurity compliance expert. Analyze the following Software Bill of Materials (SBOM) for compliance with the specified security controls.

        ## SBOM Information:
        - Name: {sbom_data.get('name', 'Unknown')}
        - Format: {sbom_data.get('format', 'Unknown')}
        - Component Count: {len(components)}
        
        ## Key Components:
        {component_list}
        
        ## Compliance Profile: {profile.get('name', 'Unknown')}
        ## Controls to Verify:
        {control_list}
        
        ## Analysis Instructions:
        1. Identify any components with known vulnerabilities or security issues.
        2. Evaluate compliance with each of the security controls listed above.
        3. For each control, determine if it is satisfied (PASS) or not (FAIL).
        4. Provide specific evidence for each control's compliance status.
        5. Suggest remediation steps for any failed controls.
        6. Calculate an overall compliance score (0-100).
        
        ## Response Format:
        Provide your analysis in JSON format with the following structure:
        ```json
        {{
            "overall_score": <score 0-100>,
            "summary": "<brief summary of findings>",
            "control_results": [
                {{
                    "control_id": "<control id>",
                    "status": "<PASS|FAIL>",
                    "evidence": "<specific evidence for status>",
                    "remediation": "<remediation steps if FAIL>"
                }},
                ...
            ],
            "vulnerable_components": [
                {{
                    "name": "<component name>",
                    "version": "<version>",
                    "vulnerabilities": ["<vuln1>", "<vuln2>", ...],
                    "recommendation": "<fix recommendation>"
                }},
                ...
            ]
        }}
        ```
        
        Ensure your response is ONLY the JSON object, with no additional text before or after.
        """
        
        return prompt
    
    def _format_contract_prompt(self, contract_data: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """
        Format prompt for smart contract analysis
        """
        # Extract important contract info
        functions = contract_data.get("functions", [])
        function_list = "\n".join([
            f"- {f.get('name', 'Unknown')}({f.get('params', '')}): {f.get('returns', '')}"
            for f in functions
        ])
        
        # Extract controls from profile
        control_list = "\n".join([
            f"- {control['id']}: {control['name']}"
            for control in profile.get("controls", [])
        ])
        
        # Construct the prompt
        prompt = f"""
        You are a smart contract security expert. Analyze the following smart contract for security vulnerabilities and compliance with the specified security controls.

        ## Smart Contract Information:
        - Name: {contract_data.get('name', 'Unknown')}
        - Language: {contract_data.get('language', 'Unknown')}
        - Code Size: {contract_data.get('code_size', 0)} bytes
        
        ## Functions:
        {function_list}
        
        ## Imports:
        {", ".join(contract_data.get('imports', []))}
        
        ## Compliance Profile: {profile.get('name', 'Unknown')}
        ## Controls to Verify:
        {control_list}
        
        ## Analysis Instructions:
        1. Identify any potential security vulnerabilities or weaknesses in the contract.
        2. Evaluate compliance with each of the security controls listed above.
        3. For each control, determine if it is satisfied (PASS) or not (FAIL).
        4. Provide specific evidence for each control's compliance status.
        5. Suggest remediation steps for any failed controls.
        6. Calculate an overall compliance score (0-100).
        
        ## Response Format:
        Provide your analysis in JSON format with the following structure:
        ```json
        {{
            "overall_score": <score 0-100>,
            "summary": "<brief summary of findings>",
            "control_results": [
                {{
                    "control_id": "<control id>",
                    "status": "<PASS|FAIL>",
                    "evidence": "<specific evidence for status>",
                    "remediation": "<remediation steps if FAIL>"
                }},
                ...
            ],
            "vulnerabilities": [
                {{
                    "name": "<vulnerability name>",
                    "description": "<description>",
                    "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
                    "recommendation": "<fix recommendation>"
                }},
                ...
            ]
        }}
        ```
        
        Ensure your response is ONLY the JSON object, with no additional text before or after.
        """
        
        return prompt
    
    def _parse_sbom_analysis(self, ai_response: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AI response for SBOM analysis
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json(ai_response)
            analysis = json.loads(json_str)
            
            # Count passed and failed controls
            passed = sum(1 for c in analysis.get("control_results", []) if c.get("status") == "PASS")
            failed = sum(1 for c in analysis.get("control_results", []) if c.get("status") == "FAIL")
            
            # Format result
            result = {
                "compliance_score": analysis.get("overall_score", 0),
                "summary": analysis.get("summary", ""),
                "controls": {
                    "total": len(analysis.get("control_results", [])),
                    "passed": passed,
                    "failed": failed
                },
                "control_results": analysis.get("control_results", []),
                "vulnerable_components": analysis.get("vulnerable_components", []),
                "ai_generated": True,
                "model": "gemini-1.5-flash",
                "profile": profile.get("name")
            }
            
            return result
        except Exception as e:
            raise Exception(f"Failed to parse AI analysis: {str(e)}")
    
    def _parse_contract_analysis(self, ai_response: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AI response for smart contract analysis
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json(ai_response)
            analysis = json.loads(json_str)
            
            # Count passed and failed controls
            passed = sum(1 for c in analysis.get("control_results", []) if c.get("status") == "PASS")
            failed = sum(1 for c in analysis.get("control_results", []) if c.get("status") == "FAIL")
            
            # Format result
            result = {
                "compliance_score": analysis.get("overall_score", 0),
                "summary": analysis.get("summary", ""),
                "controls": {
                    "total": len(analysis.get("control_results", [])),
                    "passed": passed,
                    "failed": failed
                },
                "control_results": analysis.get("control_results", []),
                "vulnerabilities": analysis.get("vulnerabilities", []),
                "ai_generated": True,
                "model": "gemini-1.5-flash",
                "profile": profile.get("name")
            }
            
            return result
        except Exception as e:
            raise Exception(f"Failed to parse AI analysis: {str(e)}")
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text that might include markdown code blocks
        """
        # Look for JSON in code blocks
        import re
        
        # Try to extract from markdown code blocks
        matches = re.findall(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if matches:
            return matches[0]
        
        # If no markdown blocks, check for JSON object directly
        match = re.search(r"(\{[\s\S]+\})", text)
        if match:
            return match.group(1)
        
        # If neither approach works, return the original text
        return text
    
    def _get_profile_definition(self, profile_id: str) -> Dict[str, Any]:
        """
        Get profile definition by ID
        
        For PoC, using simplified mock profiles
        In production, would load from database or standards library
        """
        profiles = {
            "nist-800-53-low": {
                "name": "NIST 800-53 (Low)",
                "description": "NIST 800-53 Low-Impact Baseline",
                "controls": [
                    {"id": "AC-2", "name": "Account Management"},
                    {"id": "AC-3", "name": "Access Enforcement"},
                    {"id": "AC-17", "name": "Remote Access"},
                    {"id": "AU-2", "name": "Audit Events"},
                    {"id": "CM-6", "name": "Configuration Settings"},
                    {"id": "IA-2", "name": "Identification and Authentication"}
                ]
            },
            "nist-800-53-moderate": {
                "name": "NIST 800-53 (Moderate)",
                "description": "NIST 800-53 Moderate-Impact Baseline",
                "controls": [
                    {"id": "AC-2", "name": "Account Management"},
                    {"id": "AC-3", "name": "Access Enforcement"},
                    {"id": "AC-17", "name": "Remote Access"},
                    {"id": "AU-2", "name": "Audit Events"},
                    {"id": "CM-6", "name": "Configuration Settings"},
                    {"id": "CM-7", "name": "Least Functionality"},
                    {"id": "IA-2", "name": "Identification and Authentication"},
                    {"id": "SC-7", "name": "Boundary Protection"},
                    {"id": "SC-8", "name": "Transmission Confidentiality"},
                    {"id": "SI-4", "name": "Information System Monitoring"}
                ]
            },
            "nist-800-53-high": {
                "name": "NIST 800-53 (High)",
                "description": "NIST 800-53 High-Impact Baseline",
                "controls": [
                    {"id": "AC-2", "name": "Account Management"},
                    {"id": "AC-3", "name": "Access Enforcement"},
                    {"id": "AC-17", "name": "Remote Access"},
                    {"id": "AU-2", "name": "Audit Events"},
                    {"id": "AU-6", "name": "Audit Review, Analysis, and Reporting"},
                    {"id": "CM-3", "name": "Configuration Change Control"},
                    {"id": "CM-6", "name": "Configuration Settings"},
                    {"id": "CM-7", "name": "Least Functionality"},
                    {"id": "IA-2", "name": "Identification and Authentication"},
                    {"id": "SC-7", "name": "Boundary Protection"},
                    {"id": "SC-8", "name": "Transmission Confidentiality"},
                    {"id": "SC-28", "name": "Protection of Information at Rest"},
                    {"id": "SI-3", "name": "Malicious Code Protection"},
                    {"id": "SI-4", "name": "Information System Monitoring"},
                    {"id": "SI-7", "name": "Software, Firmware, and Information Integrity"}
                ]
            }
        }
        
        return profiles.get(profile_id, {"name": "Unknown Profile", "controls": []})
