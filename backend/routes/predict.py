import os
import uuid
import shutil
import asyncio
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from database import get_db
from models import InspectionSession, Vessel, DryDockVisit, AnalysisSession
from services.pipeline_logger import log_pipeline_event

router = APIRouter()

# =========================================================
# GLOBAL THREAD POOL
# =========================================================

executor = ThreadPoolExecutor(max_workers=1)

# =========================================================
# BACKGROUND WRAPPER
# =========================================================
# Legacy wrappers removed. Handled by orchestration_service.py


# =========================================================
# HELPER: Ensure Vessel & Visit exist
# =========================================================
async def ensure_vessel_and_visit(db, imo_number, vessel_name, vessel_type, gross_tonnage, visit_id=None):
    if not imo_number:
        return None, None
        
    vessel = await db.vessels.find_one({"imo": imo_number})
    if not vessel:
        vessel = Vessel(
            vessel_id=imo_number,
            imo=imo_number,
            vessel_name=vessel_name or "Unknown",
            vessel_type=vessel_type,
            gross_tonnage=gross_tonnage,
            total_visits=0,
            total_reports=0
        )
        await db.vessels.insert_one(vessel.model_dump())
    
    if visit_id:
        visit = await db.drydock_visits.find_one({"visit_id": visit_id})
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        # Update report version on append
        new_version = visit.get("report_version", 0) + 1
        await db.drydock_visits.update_one({"visit_id": visit_id}, {"$set": {"report_version": new_version}})
    else:
        # Create a new visit
        vessel_doc = await db.vessels.find_one({"imo": imo_number})
        visit_number = await db.drydock_visits.count_documents({"ship_id": imo_number}) + 1
        visit_id = str(uuid.uuid4())
        visit = DryDockVisit(
            visit_id=visit_id,
            ship_id=imo_number,
            visit_number=visit_number,
            report_version=1
        )
        await db.drydock_visits.insert_one(visit.model_dump())
        await db.vessels.update_one({"imo": imo_number}, {"$inc": {"total_visits": 1}})
        
    return imo_number, visit_id


# =========================================================
# PREDICT ENDPOINT (BATCH)
# =========================================================

@router.post("/predict/batch")
async def predict_videos(
    videos: list[UploadFile] = File(...),
    vessel_name: str | None = Form(default=None),
    imo_number: str | None = Form(default=None),
    vessel_type: str | None = Form(default=None),
    gross_tonnage: str | None = Form(default=None),
    inspector_name: str | None = Form(default=None),
    location: str | None = Form(default=None),
    inspection_date: str | None = Form(default=None),
    comments: str | None = Form(default=None),
    visit_id: str | None = Form(default=None),
):

    if not videos:
        raise HTTPException(
            status_code=400,
            detail="At least one video is required"
        )

    db = get_db()
    
    # 1. Resolve Vessel & Visit
    resolved_imo, resolved_visit_id = await ensure_vessel_and_visit(
        db, imo_number, vessel_name, vessel_type, gross_tonnage, visit_id
    )

    batch_id = str(uuid.uuid4()) # Keep batch_id for backwards compatibility
    
    # Find previous frame JSONs for this visit
    previous_frame_jsons = []
    if resolved_visit_id:
        previous_sessions = await db.analysis_sessions.find({"visit_id": resolved_visit_id}).to_list(length=None)
        for sess in previous_sessions:
            prev_session_id = sess.get("session_id")
            if prev_session_id:
                prev_json_path = os.path.join(
                    "outputs", "sessions", prev_session_id, 
                    "module_1_frame_extraction_output", "extracted_frames.json"
                )
                if os.path.exists(prev_json_path):
                    previous_frame_jsons.append(prev_json_path)

    from repositories.job_repository import job_repository
    from services.orchestration_service import orchestration_service
    from config import settings

    session_ids = []

    for video in videos:
        # Generate inspection_id for each video
        inspection_id = str(uuid.uuid4())
        session_ids.append(inspection_id)
        
        # Save locally in persistent session directory
        video_dir = os.path.join(settings.output_folder, inspection_id)
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(os.path.join(video_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(video_dir, "frames"), exist_ok=True)
        os.makedirs(os.path.join(video_dir, "defects"), exist_ok=True)
        os.makedirs(os.path.join(video_dir, "masks"), exist_ok=True)
        os.makedirs(os.path.join(video_dir, "reports"), exist_ok=True)
        
        video_path = os.path.abspath(os.path.join(video_dir, "uploads", "original_video.mp4"))
        
        with open(video_path, "wb") as f:
            f.write(await video.read())

        # Create job
        from datetime import datetime
        
        # Missing inspections insert (Issue 3)
        inspection_doc = {
            "inspection_id": inspection_id,
            "batch_id": batch_id,
            "video_name": video.filename,
            "video_path": video_path,
            "status": "VIDEO_UPLOADED",
            "created_at": datetime.utcnow()
        }
        from database import db_instance
        await db_instance.inspections.insert_one(inspection_doc)

        job_doc = {
            "inspection_id": inspection_id,
            "status": "PENDING_FRAME_EXTRACTION",
            "created_at": datetime.utcnow()
        }
        await db_instance.inspection_jobs.insert_one(job_doc)

        # Legacy InspectionSession (For compatibility)
        new_session = InspectionSession(
            session_id=inspection_id,
            batch_id=batch_id,
            video_name=video.filename,
            vessel_name=vessel_name,
            imo_number=imo_number,
            vessel_type=vessel_type,
            gross_tonnage=gross_tonnage,
            inspector_name=inspector_name,
            location=location,
            inspection_date=inspection_date,
            comments=comments,
            video_path=video_path,
            output_path="",
            status="processing",
            progress=0,
            current_stage="Queued"
        )
        await db_instance.inspection_sessions.insert_one(new_session.model_dump())

        log_pipeline_event(
            inspection_id,
            "upload",
            "video_stored",
            "uploaded video stored locally",
            file_path=video_path,
            original_name=video.filename,
        )

        # Enterprise Lifecycle Session
        if resolved_imo:
            await db_instance.vessels.update_one({"imo": resolved_imo}, {"$inc": {"total_reports": 1}})
            analysis = AnalysisSession(
                session_id=inspection_id,
                vessel_id=resolved_imo,
                visit_id=resolved_visit_id,
                uploaded_videos=[video.filename],
                status="processing"
            )
            await db_instance.analysis_sessions.insert_one(analysis.model_dump())

        # Trigger Orchestration
        from services.orchestration_service import start_pipeline
        import asyncio
        asyncio.create_task(start_pipeline(inspection_id))
        
        log_pipeline_event(
            inspection_id,
            "orchestrator",
            "background_job_started",
            "orchestrator background job started",
        )

    return {
        "batch_id": batch_id,
        "visit_id": resolved_visit_id,
        "session_ids": session_ids,
        "status": "processing",
        "count": len(videos)
    }
