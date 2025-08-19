from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.ipfs_service import IPFSService

router = APIRouter()


def get_ipfs_service():
    return IPFSService()


class PinJsonBody(BaseModel):
    name: str
    artifact_hash: str
    data: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "name": "oscal-initial",
                "artifact_hash": "94d473c0062d84a40dbf0243e16758e02e34fe6be08634e420125633caa240bd",
                "data": {"hello": "world"}
            }
        }


@router.post("/pin-json", summary="Pin JSON to IPFS (Pinata)")
async def pin_json(
    body: PinJsonBody,
    ipfs: IPFSService = Depends(get_ipfs_service),
) -> Dict[str, str]:
    """Pin an arbitrary JSON document to IPFS via Pinata.

    Request body example:
    {
      "name": "oscal-initial",
      "artifact_hash": "94d4...240bd",
      "data": {"hello": "world"}
    }

    Returns 200 with `{ "cid": "...", "url": "..." }` on success; 500 on service errors.
    """
    try:
        res = await ipfs.pin_json(data=body.data, name=body.name, artifact_hash=body.artifact_hash)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pin JSON failed: {e}")


@router.post("/pin-file", summary="Pin file to IPFS (Pinata)")
async def pin_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    artifact_hash: Optional[str] = Form(None),
    ipfs: IPFSService = Depends(get_ipfs_service),
) -> Dict[str, str]:
    """Pin an uploaded file to IPFS via Pinata.

    - form fields: `file` (binary), `name` (optional), `artifact_hash` (required)
    - returns `{ "cid": "...", "url": "..." }` on success
    - 400 if `artifact_hash` missing
    - 500 on service errors
    """
    if not artifact_hash:
        raise HTTPException(status_code=400, detail="artifact_hash is required")

    display_name = name or (file.filename or "artifact")

    try:
        content = await file.read()
        res = await ipfs.pin_file(
            file_bytes=content,
            name=display_name,
            artifact_hash=artifact_hash,
            filename=file.filename,
            content_type=file.content_type,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pin file failed: {e}")


@router.get("/resolve/{cid}", summary="Resolve a CID to gateway URL")
async def resolve_cid(cid: str) -> Dict[str, str]:
    """Return public gateway URLs for a CID.

    Responds 200 with Pinata and ipfs.io URLs; 400 if CID empty.
    """
    if not cid:
        raise HTTPException(status_code=400, detail="cid is required")
    # Prefer Pinata gateway, but any public gateway works
    return {
        "cid": cid,
        "url": f"https://gateway.pinata.cloud/ipfs/{cid}",
        "alt_url": f"https://ipfs.io/ipfs/{cid}",
    }
