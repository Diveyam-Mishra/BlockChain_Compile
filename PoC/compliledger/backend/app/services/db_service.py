#!/usr/bin/env python3

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create SQLAlchemy models
Base = declarative_base()

class VerificationRequest(Base):
    """Model for verification requests"""
    __tablename__ = "verification_requests"
    
    id = Column(Integer, primary_key=True)
    artifact_hash = Column(String(64), unique=True, index=True)
    profile_id = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    submitter_address = Column(String(64))
    submission_time = Column(DateTime, default=datetime.now)
    verification_time = Column(DateTime, nullable=True)
    
    # Blockchain information
    tx_id = Column(String(128), nullable=True)
    registry_app_id = Column(Integer)
    oracle_app_id = Column(Integer)
    
    # OSCAL and IPFS data
    initial_oscal_cid = Column(String(128), nullable=True)
    verified_oscal_cid = Column(String(128), nullable=True)
    
    # AI analysis results
    compliance_score = Column(Integer, default=0)
    controls_passed = Column(Integer, default=0)
    controls_failed = Column(Integer, default=0)
    
    # Related metadata and results
    sbom_metadata = Column(JSONB, default={})
    results = Column(JSONB, default={})
    findings = relationship("Finding", back_populates="verification_request")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "artifact_hash": self.artifact_hash,
            "profile_id": self.profile_id,
            "status": self.status,
            "submitter_address": self.submitter_address,
            "submission_time": self.submission_time.isoformat() if self.submission_time else None,
            "verification_time": self.verification_time.isoformat() if self.verification_time else None,
            "tx_id": self.tx_id,
            "registry_app_id": self.registry_app_id,
            "oracle_app_id": self.oracle_app_id,
            "initial_oscal_cid": self.initial_oscal_cid,
            "verified_oscal_cid": self.verified_oscal_cid,
            "compliance_score": self.compliance_score,
            "controls_passed": self.controls_passed,
            "controls_failed": self.controls_failed,
            "metadata": self.metadata,
            "results": self.results,
            "findings": [finding.to_dict() for finding in self.findings]
        }


class Finding(Base):
    """Model for compliance findings"""
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("verification_requests.id"))
    severity = Column(String(20))
    control_id = Column(String(50))
    description = Column(Text)
    recommendation = Column(Text)
    status = Column(String(20), default="open")
    
    verification_request = relationship("VerificationRequest", back_populates="findings")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "severity": self.severity,
            "control_id": self.control_id,
            "description": self.description,
            "recommendation": self.recommendation,
            "status": self.status
        }


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        """Initialize database connection"""
        # Get database connection string from environment
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "compliledger")
        
        # Create SQLAlchemy engine
        self.db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def initialize(self):
        """Initialize database schema"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            # For PoC, continue even if database fails
            logger.warning("Continuing without database for PoC purposes")
    
    async def create_verification_request(self, 
                                      artifact_hash: str, 
                                      profile_id: str,
                                      submitter_address: str,
                                      metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new verification request"""
        try:
            async with self.async_session() as session:
                async with session.begin():
                    request = VerificationRequest(
                        artifact_hash=artifact_hash,
                        profile_id=profile_id,
                        submitter_address=submitter_address,
                        metadata=metadata,
                        registry_app_id=int(os.getenv("REGISTRY_APP_ID", "0")),
                        oracle_app_id=int(os.getenv("ORACLE_APP_ID", "0"))
                    )
                    session.add(request)
                    await session.flush()
                    await session.refresh(request)
                    return request.to_dict()
        except Exception as e:
            logger.error(f"Error creating verification request: {str(e)}")
            # For PoC, return mock data on database failure
            return self._generate_mock_request(artifact_hash, profile_id, submitter_address, metadata)
    
    async def update_verification_status(self,
                                     artifact_hash: str,
                                     tx_id: str,
                                     status: str,
                                     results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update verification status"""
        try:
            async with self.async_session() as session:
                async with session.begin():
                    from sqlalchemy import select
                    stmt = select(VerificationRequest).where(VerificationRequest.artifact_hash == artifact_hash)
                    result = await session.execute(stmt)
                    request = result.scalars().first()
                    if not request:
                        logger.warning(f"Verification request not found for hash: {artifact_hash}")
                        return None
                    
                    request.status = status
                    request.tx_id = tx_id
                    request.verification_time = datetime.now()
                    request.initial_oscal_cid = results.get("initial_oscal_cid")
                    request.verified_oscal_cid = results.get("verified_oscal_cid")
                    request.compliance_score = results.get("compliance_score", 0)
                    request.controls_passed = results.get("controls_passed", 0)
                    request.controls_failed = results.get("controls_failed", 0)
                    request.results = results
                    
                    # Add findings if present
                    for finding_data in results.get("findings", []):
                        finding = Finding(
                            request_id=request.id,
                            severity=finding_data.get("severity", "medium"),
                            control_id=finding_data.get("control_id", "unknown"),
                            description=finding_data.get("description", ""),
                            recommendation=finding_data.get("recommendation", ""),
                            status="open"
                        )
                        session.add(finding)
                    
                    await session.flush()
                    await session.refresh(request)
                    return request.to_dict()
        except Exception as e:
            logger.error(f"Error updating verification status: {str(e)}")
            # For PoC, return mock data on database failure
            return self._generate_mock_updated_request(artifact_hash, tx_id, status, results)
    
    async def get_verification_request(self, artifact_hash: str) -> Optional[Dict[str, Any]]:
        """Get verification request by artifact hash"""
        try:
            async with self.async_session() as session:
                from sqlalchemy import select
                stmt = select(VerificationRequest).where(VerificationRequest.artifact_hash == artifact_hash)
                result = await session.execute(stmt)
                request = result.scalars().first()
                if request:
                    return request.to_dict()
                return None
        except Exception as e:
            logger.error(f"Error getting verification request: {str(e)}")
            # For PoC, return mock data on database failure
            return self._generate_mock_request(artifact_hash, "default", "", {})
    
    def _generate_mock_request(self, 
                          artifact_hash: str,
                          profile_id: str,
                          submitter_address: str,
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock verification request data for PoC"""
        return {
            "id": 1,
            "artifact_hash": artifact_hash,
            "profile_id": profile_id,
            "status": "pending",
            "submitter_address": submitter_address,
            "submission_time": datetime.now().isoformat(),
            "verification_time": None,
            "tx_id": None,
            "registry_app_id": int(os.getenv("REGISTRY_APP_ID", "0")),
            "oracle_app_id": int(os.getenv("ORACLE_APP_ID", "0")),
            "initial_oscal_cid": None,
            "verified_oscal_cid": None,
            "compliance_score": 0,
            "controls_passed": 0,
            "controls_failed": 0,
            "metadata": metadata,
            "results": {},
            "findings": []
        }
    
    def _generate_mock_updated_request(self,
                                  artifact_hash: str,
                                  tx_id: str,
                                  status: str,
                                  results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock updated verification request data for PoC"""
        return {
            "id": 1,
            "artifact_hash": artifact_hash,
            "profile_id": "default",
            "status": status,
            "submitter_address": "",
            "submission_time": (datetime.now().replace(minute=datetime.now().minute-5)).isoformat(),
            "verification_time": datetime.now().isoformat(),
            "tx_id": tx_id,
            "registry_app_id": int(os.getenv("REGISTRY_APP_ID", "0")),
            "oracle_app_id": int(os.getenv("ORACLE_APP_ID", "0")),
            "initial_oscal_cid": results.get("initial_oscal_cid"),
            "verified_oscal_cid": results.get("verified_oscal_cid"),
            "compliance_score": results.get("compliance_score", 0),
            "controls_passed": results.get("controls_passed", 0),
            "controls_failed": results.get("controls_failed", 0),
            "metadata": {},
            "results": results,
            "findings": []
        }


# Example usage
async def test_database():
    """Test database service"""
    db = DatabaseService()
    await db.initialize()
    
    # Create a verification request
    artifact_hash = "4efbe4768fa2182cf72a93cdab95f8a7b5637b6233302cfc2775228eab3c1ac0"
    request = await db.create_verification_request(
        artifact_hash=artifact_hash,
        profile_id="default",
        submitter_address="5IGW4MX4LXEXU6OX4QBUJ2TZ2AH6DWMADY5HPJ6NAI3D7RPTQNEDMOGR6A",
        metadata={"name": "Sample SBOM", "format": "cyclonedx"}
    )
    
    print("\n===== Created Verification Request =====")
    print(json.dumps(request, indent=2))
    
    # Update verification status
    results = {
        "initial_oscal_cid": "QmTest123InitialCID",
        "verified_oscal_cid": "QmTest456VerifiedCID",
        "compliance_score": 85,
        "controls_passed": 8,
        "controls_failed": 2,
        "findings": [
            {
                "severity": "high",
                "control_id": "CM-2",
                "description": "Missing baseline configuration",
                "recommendation": "Establish and document baseline configurations"
            }
        ]
    }
    
    updated = await db.update_verification_status(
        artifact_hash=artifact_hash,
        tx_id="VAVNE3CAHKMGS2QTSD45VILQFY7GX5R44SJHRQ3DTSY4NUJN2H3A",
        status="verified",
        results=results
    )
    
    print("\n===== Updated Verification Status =====")
    print(json.dumps(updated, indent=2))
    
    # Get verification request
    retrieved = await db.get_verification_request(artifact_hash)
    
    print("\n===== Retrieved Verification Request =====")
    print(json.dumps(retrieved, indent=2))

if __name__ == "__main__":
    asyncio.run(test_database())
