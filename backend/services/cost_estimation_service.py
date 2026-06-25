import logging
import uuid
from datetime import datetime
from database import db_instance

logger = logging.getLogger(__name__)

async def run_cost_estimation(inspection_id: str, vessel_id: str = None, visit_id: str = None):
    logger.info(f"[{inspection_id}] Running Cost Estimation...")
    
    defects = await db_instance.defect_registry.find({"inspection_id": inspection_id}).to_list(length=None)
    
    if not defects:
        logger.info(f"[{inspection_id}] No defects found for cost estimation.")
        return
        
    # Simple business logic configuration
    BASE_COST = 500.0
    SEVERITY_MULTIPLIER = {
        "LOW": 1.0,
        "MEDIUM": 2.5,
        "HIGH": 5.0
    }
    
    from models import RepairEstimation
    records = []
    
    total_cost = 0.0
    
    for defect in defects:
        severity = defect.get("severity", "LOW").upper()
        # Mock area since we don't have true mask pixel counts in this MVP
        area = 2.5 if severity == "HIGH" else 1.0 
        
        multiplier = SEVERITY_MULTIPLIER.get(severity, 1.0)
        estimated_cost = BASE_COST * multiplier * area
        
        total_cost += estimated_cost
        
        r_record = RepairEstimation(
            estimation_id=str(uuid.uuid4()),
            defect_id=defect["defect_id"],
            inspection_id=inspection_id,
            vessel_id=vessel_id,
            visit_id=visit_id,
            severity=severity,
            area=area,
            estimated_cost=estimated_cost,
            currency="USD"
        )
        records.append(r_record.model_dump())
        
    if records:
        await db_instance.repair_estimations.insert_many(records)
        logger.info(f"[{inspection_id}] Generated {len(records)} cost estimations. Total Exposure: ${total_cost:,.2f}")
        
        # Optionally update DryDockVisit total_cost if we have visit_id
        if visit_id:
            await db_instance.drydock_visits.update_one(
                {"visit_id": visit_id},
                {"$inc": {"total_cost": total_cost, "total_defects": len(records)}}
            )
