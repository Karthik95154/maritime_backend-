from fastapi import APIRouter, HTTPException
from database import db_instance
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/artifacts/{inspection_id}")
async def get_artifacts(inspection_id: str):
    logger.info(f"[{inspection_id}] Fetching artifacts...")
    
    # Query the collection where artifacts are being pushed by the storage APIs
    doc = await db_instance.db["inspection_artifacts"].find_one({"inspection_id": inspection_id})
    
    if not doc:
        logger.warning(f"[{inspection_id}] No artifacts found in DB.")
        # Return empty arrays to match the requested example response format
        return {
            "inspection_id": inspection_id,
            "frames": [],
            "annotated_images": [],
            "part_masks": [],
            "defect_masks": [],
            "area_results": [],
            "reports": []
        }
        
    return {
        "inspection_id": inspection_id,
        "frames": doc.get("frames", []),
        "annotated_images": doc.get("annotated_images", []),
        "part_masks": doc.get("part_masks", []),
        "defect_masks": doc.get("defect_masks", []),
        "area_results": doc.get("area_results", []),
        "reports": doc.get("reports", [])
    }
