from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add proper import paths
SCRIPT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.append(str(BACKEND_DIR))

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title="CompliLedger API",
    description="OSCAL-Integrated Hybrid On-Chain AI SBOM Verification System",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import API routers (package-relative)
from .api.routes import artifacts, verification, auditor, controls, ipfs

# Include API routers
app.include_router(artifacts.router, prefix="/api/v1/artifacts", tags=["artifacts"])
app.include_router(verification.router, prefix="/api/v1/verification", tags=["verification"])
app.include_router(auditor.router, prefix="/api/v1/auditor", tags=["auditor"])
app.include_router(controls.router, prefix="/api/v1/controls", tags=["controls"])
app.include_router(ipfs.router, prefix="/api/v1/ipfs", tags=["ipfs"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "CompliLedger API",
        "version": "0.1.0"
    }

# Run application if executed directly
if __name__ == "__main__":
    import uvicorn
    # Prefer Railway's PORT if provided, fallback to API_PORT, then 8000
    port_str = os.getenv("PORT") or os.getenv("API_PORT", "8000")
    uvicorn.run(
        "compliledger.backend.app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(port_str),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
