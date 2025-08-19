from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Reuse existing utilities
from backend.app.services.resources.explore_controls import (
    load_default_controls,
    search_controls,
    list_controls,
    find_relevant_controls_for_smart_contract,
)

router = APIRouter()

# Cache controls at module import
_CONTROLS: Dict[str, Dict[str, Any]] = load_default_controls()
if not isinstance(_CONTROLS, dict) or not _CONTROLS:
    _CONTROLS = {}


def _families_from_controls() -> List[Dict[str, Any]]:
    fam: Dict[str, int] = {}
    for control_id in _CONTROLS.keys():
        key = control_id.split('-')[0].upper() if '-' in control_id else 'OTHER'
        fam[key] = fam.get(key, 0) + 1
    return [{"key": k, "count": v} for k, v in sorted(fam.items())]


def _shape_item(control_id: str, control: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": control_id,
        "title": control.get("title"),
        "category": control.get("category"),
        "criticality": control.get("criticality"),
    }


class RecommendRequest(BaseModel):
    artifact_text: Optional[str] = None
    artifact_path: Optional[str] = None
    limit: int = 5

    class Config:
        schema_extra = {
            "example": {
                "artifact_text": "ERC20 transfer requires role-based access control and pausable mechanisms",
                "limit": 3
            }
        }


@router.get("/families")
def get_families() -> Dict[str, Any]:
    """Return control families and counts for dropdowns."""
    if not _CONTROLS:
        raise HTTPException(status_code=500, detail="Controls not loaded")
    return {"families": _families_from_controls()}


@router.get("")
def get_controls(
    family: Optional[str] = Query(None, description="Control family prefix, e.g., AC, IA"),
    limit: Optional[int] = Query(50, ge=1, le=500),
    q: Optional[str] = Query(None, description="Search query"),
    field: Optional[str] = Query(None, description="Field to search in (e.g., title, category)"),
) -> Dict[str, Any]:
    """List or search controls with lightweight fields."""
    if not _CONTROLS:
        raise HTTPException(status_code=500, detail="Controls not loaded")

    items: Dict[str, Dict[str, Any]] = {}

    if q:
        items = search_controls(_CONTROLS, q, search_field=field or None)
        if limit:
            # Trim to limit while keeping deterministic order by key
            items = {k: items[k] for k in sorted(items.keys())[: limit]}
    else:
        fam = family.upper() if family else None
        items = list_controls(_CONTROLS, family=fam, limit=limit)

    shaped = [_shape_item(k, v) for k, v in items.items()]
    return {"items": shaped, "total": len(shaped)}


@router.post("/recommend")
def recommend_controls(payload: RecommendRequest) -> Dict[str, Any]:
    """Recommend relevant controls for a given artifact text or file.

    Request body example:
    {
      "artifact_text": "ERC20 transfer requires role-based access control and pausable mechanisms",
      "limit": 3
    }

    Response example (200):
    {
      "items": [
        {"id": "AC-3", "title": "Access Enforcement", "category": "Access Control", "criticality": "high", "relevance_score": 0.87},
        {"id": "AC-6", "title": "Least Privilege", "category": "Access Control", "criticality": "high", "relevance_score": 0.82}
      ],
      "total": 2
    }
    """
    if not _CONTROLS:
        raise HTTPException(status_code=500, detail="Controls not loaded")

    text = payload.artifact_text
    if not text and payload.artifact_path:
        try:
            with open(payload.artifact_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unable to read artifact_path: {e}")

    if not text:
        raise HTTPException(status_code=400, detail="Provide artifact_text or artifact_path")

    try:
        results = find_relevant_controls_for_smart_contract(text, num_results=max(1, min(payload.limit, 50)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Control recommendation failed: {e}")

    items = []
    for control_id, control, score in results:
        d = _shape_item(control_id, control)
        d["relevance_score"] = score
        items.append(d)

    return {"items": items, "total": len(items)}
