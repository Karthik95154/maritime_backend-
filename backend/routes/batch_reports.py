from fastapi import APIRouter, HTTPException
from database import get_db

router = APIRouter()

def _format_report(report):
    return {
        "reportId": report.get("report_id"),
        "inspectionId": report.get("inspection_id"),
        "vesselId": report.get("vessel_id"),
        "visitId": report.get("visit_id"),
        "documentPath": report.get("file_path"),
        "generatedAt": report.get("generated_at").isoformat() if report.get("generated_at") else None,
    }

@router.get("")
async def get_all_reports():
    db = get_db()
    reports = await db.reports.find().sort("generated_at", -1).to_list(length=None)
    return [_format_report(r) for r in reports]

@router.get("/{report_id}")
async def get_report(report_id: str):
    db = get_db()
    report = await db.reports.find_one({"report_id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _format_report(report)

@router.get("/vessels/{vessel_id}")
async def get_vessel_reports(vessel_id: str):
    db = get_db()
    reports = await db.reports.find({"vessel_id": vessel_id}).sort("generated_at", -1).to_list(length=None)
    return [_format_report(r) for r in reports]

@router.get("/visits/{visit_id}")
async def get_visit_reports(visit_id: str):
    db = get_db()
    reports = await db.reports.find({"visit_id": visit_id}).sort("generated_at", -1).to_list(length=None)
    return [_format_report(r) for r in reports]
