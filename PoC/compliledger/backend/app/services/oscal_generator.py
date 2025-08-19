import json
import uuid
import datetime
from typing import Dict, List, Any, Optional

class OSCALGenerator:
    """
    Service for generating OSCAL-compliant documents from artifact analysis results
    """
    
    def __init__(self):
        """Initialize OSCAL generator"""
        self.uuid_ns = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Namespace for consistent UUIDs
    
    async def generate_component_definition(self, artifact: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate OSCAL Component Definition from artifact and analysis results
        
        Args:
            artifact: The parsed artifact data
            analysis_results: The AI analysis results
            
        Returns:
            OSCAL-compliant Component Definition document
        """
        # Generate document UUID based on artifact hash for consistency
        doc_uuid = str(uuid.uuid5(self.uuid_ns, artifact.get("hash", "")))
        
        # Create timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Define basic metadata
        metadata = {
            "title": f"Component Definition for {artifact.get('name', 'Unknown Component')}",
            "version": "1.0.0",
            "oscal-version": "1.0.0",
            "last-modified": timestamp,
            "uuid": doc_uuid,
            "parties": [
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "organization",
                    "name": "CompliLedger Verification System"
                }
            ],
            "roles": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "Generator",
                    "description": "OSCAL document generator"
                }
            ]
        }
        
        # Define components based on artifact type
        components = []
        
        if artifact.get("type") == "sbom":
            # Create component for SBOM metadata
            components.append({
                "uuid": str(uuid.uuid4()),
                "type": "software",
                "title": artifact.get("name", "Unknown Software"),
                "description": artifact.get("description", "Software component from SBOM"),
                "purpose": "software-package",
                "properties": [
                    {"name": "artifact-hash", "value": artifact.get("hash", "")},
                    {"name": "sbom-format", "value": artifact.get("format", "unknown")},
                    {"name": "verified", "value": "true" if analysis_results.get("compliance_score", 0) > 70 else "false"}
                ]
            })
            
            # Add components from the SBOM
            for idx, comp in enumerate(artifact.get("components", [])[:20]):  # Limit for document size
                components.append({
                    "uuid": str(uuid.uuid4()),
                    "type": "software",
                    "title": comp.get("name", f"Component {idx}"),
                    "description": f"Version: {comp.get('version', 'Unknown')}",
                    "properties": [
                        {"name": "version", "value": comp.get("version", "unknown")},
                        {"name": "component-type", "value": comp.get("type", "library")}
                    ]
                })
                
        elif artifact.get("type") == "smart_contract":
            # Create component for smart contract
            components.append({
                "uuid": str(uuid.uuid4()),
                "type": "software",
                "title": artifact.get("name", "Smart Contract"),
                "description": f"Smart contract written in {artifact.get('language', 'Unknown')}",
                "purpose": "smart-contract",
                "properties": [
                    {"name": "artifact-hash", "value": artifact.get("hash", "")},
                    {"name": "language", "value": artifact.get("language", "unknown")},
                    {"name": "verified", "value": "true" if analysis_results.get("compliance_score", 0) > 70 else "false"}
                ]
            })
            
            # Add functions as control implementations
            for func in artifact.get("functions", []):
                components[-1].setdefault("control-implementations", []).append({
                    "uuid": str(uuid.uuid4()),
                    "source": "internal",
                    "description": f"Function: {func.get('name', 'Unknown')}",
                    "implemented-requirements": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "description": f"Parameters: {func.get('params', '')}",
                            "control-id": "AC-3"  # Simplified mapping for PoC
                        }
                    ]
                })
        
        # Create component definition
        component_definition = {
            "component-definition": {
                "uuid": doc_uuid,
                "metadata": metadata,
                "components": components,
                "back-matter": {
                    "resources": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": "Analysis Results",
                            "description": "AI-generated analysis results",
                            "props": [
                                {"name": "compliance-score", "value": str(analysis_results.get("compliance_score", 0))}
                            ]
                        }
                    ]
                }
            }
        }
        
        return component_definition
    
    async def generate_assessment_plan(self, artifact: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Generate OSCAL Assessment Plan for the artifact verification
        
        Args:
            artifact: The parsed artifact data
            profile_id: The compliance profile ID
            
        Returns:
            OSCAL-compliant Assessment Plan document
        """
        # Generate document UUID based on artifact hash + profile ID for consistency
        doc_uuid = str(uuid.uuid5(self.uuid_ns, artifact.get("hash", "") + profile_id))
        
        # Create timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Basic metadata
        metadata = {
            "title": f"Assessment Plan for {artifact.get('name', 'Unknown Component')}",
            "version": "1.0.0",
            "oscal-version": "1.0.0",
            "last-modified": timestamp,
            "uuid": doc_uuid
        }
        
        # Get profile info
        profile_info = self._get_profile_info(profile_id)
        
        # Create assessment plan
        assessment_plan = {
            "assessment-plan": {
                "uuid": doc_uuid,
                "metadata": metadata,
                "import-ap": {
                    "href": f"#profile:{profile_id}"
                },
                "reviewed-controls": {
                    "control-selections": [
                        {
                            "description": f"Controls from {profile_info.get('name', 'Unknown Profile')}",
                            "include-all": {}
                        }
                    ]
                },
                "tasks": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "AI-Powered Analysis",
                        "description": "Automated analysis of artifact using Gemini AI",
                        "timing": {
                            "on-date": timestamp.split("T")[0]
                        },
                        "tasks": [
                            {
                                "uuid": str(uuid.uuid4()),
                                "title": "Vulnerability Scan",
                                "description": "Scan for known vulnerabilities and weaknesses"
                            },
                            {
                                "uuid": str(uuid.uuid4()),
                                "title": "Compliance Check",
                                "description": "Check compliance against security controls"
                            }
                        ]
                    }
                ],
                "back-matter": {
                    "resources": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": "Artifact",
                            "description": f"Artifact: {artifact.get('name', 'Unknown')}",
                            "props": [
                                {"name": "artifact-hash", "value": artifact.get("hash", "")}
                            ]
                        }
                    ]
                }
            }
        }
        
        return assessment_plan
    
    async def generate_assessment_results(self, artifact: Dict[str, Any], analysis_results: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Generate OSCAL Assessment Results from AI analysis
        
        Args:
            artifact: The parsed artifact data
            analysis_results: The AI analysis results
            profile_id: The compliance profile ID
            
        Returns:
            OSCAL-compliant Assessment Results document
        """
        # Generate document UUID based on artifact hash + profile ID for consistency
        doc_uuid = str(uuid.uuid5(self.uuid_ns, artifact.get("hash", "") + profile_id + "results"))
        
        # Create timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Basic metadata
        metadata = {
            "title": f"Assessment Results for {artifact.get('name', 'Unknown Component')}",
            "version": "1.0.0",
            "oscal-version": "1.0.0",
            "last-modified": timestamp,
            "uuid": doc_uuid
        }
        
        # Get profile info
        profile_info = self._get_profile_info(profile_id)
        
        # Map AI analysis results to OSCAL findings
        findings = []
        for result in analysis_results.get("control_results", []):
            finding = {
                "uuid": str(uuid.uuid4()),
                "title": f"Finding for control {result.get('control_id', 'Unknown')}",
                "description": result.get("evidence", "No evidence provided"),
                "target": {
                    "type": "component",
                    "target-id": artifact.get("hash", ""),
                    "title": artifact.get("name", "Unknown")
                },
                "status": "satisfied" if result.get("status") == "PASS" else "not-satisfied"
            }
            
            # Add remediation for failed controls
            if result.get("status") == "FAIL" and "remediation" in result:
                finding["remediation"] = {
                    "uuid": str(uuid.uuid4()),
                    "description": result.get("remediation", "No remediation provided")
                }
            
            findings.append(finding)
        
        # Create assessment results
        assessment_results = {
            "assessment-results": {
                "uuid": doc_uuid,
                "metadata": metadata,
                "import-ap": {
                    "href": f"#assessment-plan:{artifact.get('hash', '')}-{profile_id}"
                },
                "results": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "AI Analysis Results",
                        "description": analysis_results.get("summary", "AI-generated analysis results"),
                        "start": timestamp,
                        "end": timestamp,
                        "findings": findings
                    }
                ],
                "back-matter": {
                    "resources": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": "Compliance Summary",
                            "description": f"Overall score: {analysis_results.get('compliance_score', 0)}/100",
                            "props": [
                                {"name": "compliance-score", "value": str(analysis_results.get("compliance_score", 0))},
                                {"name": "controls-passed", "value": str(analysis_results.get("controls", {}).get("passed", 0))},
                                {"name": "controls-failed", "value": str(analysis_results.get("controls", {}).get("failed", 0))}
                            ]
                        }
                    ]
                }
            }
        }
        
        return assessment_results
    
    async def generate_poam(self, artifact: Dict[str, Any], analysis_results: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Generate OSCAL Plan of Action and Milestones (POA&M) from failed controls
        
        Args:
            artifact: The parsed artifact data
            analysis_results: The AI analysis results
            profile_id: The compliance profile ID
            
        Returns:
            OSCAL-compliant POA&M document
        """
        # Generate document UUID
        doc_uuid = str(uuid.uuid5(self.uuid_ns, artifact.get("hash", "") + profile_id + "poam"))
        
        # Create timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Basic metadata
        metadata = {
            "title": f"Plan of Action and Milestones for {artifact.get('name', 'Unknown Component')}",
            "version": "1.0.0",
            "oscal-version": "1.0.0",
            "last-modified": timestamp,
            "uuid": doc_uuid
        }
        
        # Filter for failed controls
        failed_controls = [
            control for control in analysis_results.get("control_results", [])
            if control.get("status") == "FAIL"
        ]
        
        # Generate remediation items
        poam_items = []
        for idx, control in enumerate(failed_controls):
            poam_items.append({
                "uuid": str(uuid.uuid4()),
                "title": f"Remediate {control.get('control_id', 'Unknown Control')}",
                "description": control.get("remediation", "No remediation provided"),
                "props": [
                    {"name": "control-id", "value": control.get("control_id", "")},
                    {"name": "evidence", "value": control.get("evidence", "")}
                ],
                "status": "planned",
                "remarks": "Generated by AI analysis"
            })
        
        # Create POA&M
        poam = {
            "plan-of-action-and-milestones": {
                "uuid": doc_uuid,
                "metadata": metadata,
                "system-id": {
                    "identifier-type": "https://compliledger.com/ns/system-ids",
                    "id": artifact.get("hash", "")
                },
                "poam-items": poam_items,
                "back-matter": {
                    "resources": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": "Assessment Results",
                            "description": "Reference to assessment results",
                            "props": [
                                {"name": "artifact-hash", "value": artifact.get("hash", "")},
                                {"name": "profile-id", "value": profile_id}
                            ]
                        }
                    ]
                }
            }
        }
        
        return poam
    
    async def generate_oscal_bundle(self, artifact: Dict[str, Any], analysis_results: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        """
        Generate a bundle of all required OSCAL documents
        
        Args:
            artifact: The parsed artifact data
            analysis_results: The AI analysis results
            profile_id: The compliance profile ID
            
        Returns:
            Dictionary with all generated OSCAL documents
        """
        component_def = await self.generate_component_definition(artifact, analysis_results)
        assessment_plan = await self.generate_assessment_plan(artifact, profile_id)
        assessment_results = await self.generate_assessment_results(artifact, analysis_results, profile_id)
        poam = await self.generate_poam(artifact, analysis_results, profile_id)
        
        return {
            "component_definition": component_def,
            "assessment_plan": assessment_plan,
            "assessment_results": assessment_results,
            "poam": poam
        }
    
    def _get_profile_info(self, profile_id: str) -> Dict[str, str]:
        """
        Get profile information by ID
        
        For PoC, using simplified mock profiles
        In production, would load from database or standards library
        """
        profiles = {
            "nist-800-53-low": {
                "name": "NIST 800-53 (Low)",
                "description": "NIST 800-53 Low-Impact Baseline"
            },
            "nist-800-53-moderate": {
                "name": "NIST 800-53 (Moderate)",
                "description": "NIST 800-53 Moderate-Impact Baseline"
            },
            "nist-800-53-high": {
                "name": "NIST 800-53 (High)",
                "description": "NIST 800-53 High-Impact Baseline"
            }
        }
        
        return profiles.get(profile_id, {"name": "Unknown Profile", "description": "Unknown Profile"})
