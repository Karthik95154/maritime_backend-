from fastapi import APIRouter, Depends
from database import get_db
from services.inspection_service import InspectionService

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(db = Depends(get_db)):
    return await InspectionService.get_dashboard(db)

@router.get("/inspections")
async def list_inspections(db = Depends(get_db)):
    return await InspectionService.list_inspections(db)

@router.get("/batches")
async def list_batches(db = Depends(get_db)):
    return await InspectionService.list_batches(db)

@router.get("/inspections/latest")
async def latest_inspection(db = Depends(get_db)):
    return await InspectionService.latest_inspection(db)

@router.get("/inspections/{session_id}/progress")
async def inspection_progress(session_id: str, db = Depends(get_db)):
    return await InspectionService.inspection_progress(session_id, db)

@router.get("/inspections/{session_id}/defects")
async def inspection_defects(session_id: str, db = Depends(get_db)):
    return await InspectionService.inspection_defects(session_id, db)

@router.get("/inspections/{session_id}/visualization")
async def inspection_visualization(session_id: str, db = Depends(get_db)):
    return await InspectionService.inspection_visualization(session_id, db)

@router.get("/inspections/{session_id}/report")
async def inspection_report(session_id: str, db = Depends(get_db)):
    return await InspectionService.inspection_report(session_id, db)

@router.get("/inspections/{session_id}/progression")
async def inspection_progression(session_id: str, db = Depends(get_db)):
    return await InspectionService.inspection_progression(session_id, db)

@router.delete("/inspections/{session_id}")
async def delete_inspection(session_id: str, db = Depends(get_db)):
    return await InspectionService.delete_inspection(session_id, db)

@router.get("/inspection/{inspection_id}/status")
async def get_inspection_status(inspection_id: str, db = Depends(get_db)):
    return await InspectionService.get_inspection_status(inspection_id, db)

@router.get("/inspection/{inspection_id}/frames")
async def get_inspection_frames(inspection_id: str, db = Depends(get_db)):
    return await InspectionService.get_inspection_frames(inspection_id, db)

@router.get("/inspection/{inspection_id}/cds-results")
async def get_inspection_cds_results(inspection_id: str, db = Depends(get_db)):
    return await InspectionService.get_inspection_cds_results(inspection_id, db)

@router.get("/inspection/{inspection_id}/report")
async def get_inspection_report(inspection_id: str, db = Depends(get_db)):
    return await InspectionService.get_inspection_report(inspection_id, db)

@router.get("/pipeline-metrics")
async def get_pipeline_metrics(db = Depends(get_db)):
    return await InspectionService.get_pipeline_metrics(db)
