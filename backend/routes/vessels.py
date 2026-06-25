from fastapi import APIRouter, Depends
from database import get_db
from services.vessel_service import VesselService

router = APIRouter()

@router.get("")
async def list_vessels(db = Depends(get_db)):
    return await VesselService.list_vessels(db)

@router.get("/{imo_number}")
async def get_vessel(imo_number: str, db = Depends(get_db)):
    return await VesselService.get_vessel(imo_number, db)

@router.delete("/{imo_number}")
async def delete_vessel(imo_number: str, db = Depends(get_db)):
    return await VesselService.delete_vessel(imo_number, db)

@router.get("/{imo_number}/visits")
async def get_vessel_visits(imo_number: str, db = Depends(get_db)):
    return await VesselService.get_vessel_visits(imo_number, db)

@router.get("/{imo_number}/defects")
async def get_vessel_defects(imo_number: str, db = Depends(get_db)):
    return await VesselService.get_vessel_defects(imo_number, db)

@router.get("/{imo_number}/reports/compare")
async def compare_reports(imo_number: str, v1: str, v2: str, db = Depends(get_db)):
    return await VesselService.compare_reports(imo_number, v1, v2, db)
