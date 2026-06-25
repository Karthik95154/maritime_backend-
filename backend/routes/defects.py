from fastapi import APIRouter, HTTPException
from database import get_db

router = APIRouter()

def _format_defect(defect, cost=None):
    cost_val = cost.get("estimated_cost", 0.0) if cost else 0.0
    return {
        "defectId": defect.get("defect_id"),
        "inspectionId": defect.get("inspection_id"),
        "vesselId": defect.get("vessel_id"),
        "visitId": defect.get("visit_id"),
        "cropPath": defect.get("crop_path"),
        "partName": defect.get("part_name"),
        "defectType": defect.get("defect_type"),
        "severity": defect.get("severity"),
        "status": defect.get("status"),
        "repairCost": cost_val,
        "createdAt": defect.get("created_at").isoformat() if defect.get("created_at") else None,
    }

@router.get("")
async def get_all_defects():
    db = get_db()
    docs = await db.defect_registry.find().sort("created_at", -1).to_list(length=None)
    costs = await db.repair_estimations.find().to_list(length=None)
    cost_map = {c["defect_id"]: c for c in costs}
    
    return [_format_defect(d, cost_map.get(d.get("defect_id"))) for d in docs]

@router.get("/{defect_id}")
async def get_defect(defect_id: str):
    db = get_db()
    defect = await db.defect_registry.find_one({"defect_id": defect_id})
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
        
    cost = await db.repair_estimations.find_one({"defect_id": defect_id})
    return _format_defect(defect, cost)

@router.get("/vessels/{vessel_id}")
async def get_vessel_defects(vessel_id: str):
    db = get_db()
    docs = await db.defect_registry.find({"vessel_id": vessel_id}).sort("created_at", -1).to_list(length=None)
    
    defect_ids = [d.get("defect_id") for d in docs]
    costs = await db.repair_estimations.find({"defect_id": {"$in": defect_ids}}).to_list(length=None)
    cost_map = {c["defect_id"]: c for c in costs}
    
    return [_format_defect(d, cost_map.get(d.get("defect_id"))) for d in docs]
