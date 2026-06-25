import logging
from datetime import datetime
from core.ai_client import trigger_generic_worker
from database import db_instance
from services.pipeline_logger import log_pipeline_event, log_stage_start, log_stage_complete, log_stage_failure
from core.pipeline_registry import PIPELINE_STAGES
import traceback
import sys

logger = logging.getLogger(__name__)

async def _update_status(inspection_id: str, status: str, progress: int, stage_name: str):
    logger.info(f"[{inspection_id}] Updating UI progress to {progress}%, stage to {stage_name}")
    await db_instance.inspection_jobs.update_one(
        {"inspection_id": inspection_id},
        {"$set": {
            "status": status,
            "updated_at": datetime.utcnow()
        }}
    )
    
    await db_instance.inspection_sessions.update_one(
        {"session_id": inspection_id},
        {"$set": {
            "progress": progress,
            "current_stage": stage_name,
            "status": "processing" if progress < 100 else "completed"
        }}
    )

async def _fail_pipeline(inspection_id: str, stage_name: str, last_successful_stage: str, error_type: str, error_message: str, traceback_str: str):
    error_str = error_message or "Worker Connection Error"
    logger.error(f"[{inspection_id}] Pipeline failed at {stage_name}: {error_str}")
    
    # Update Session
    await db_instance.inspection_sessions.update_one(
        {"session_id": inspection_id},
        {"$set": {
            "status": "FAILED",
            "failed_stage": stage_name,
            "last_successful_stage": last_successful_stage,
            "error_type": error_type,
            "error_message": error_str,
            "traceback": traceback_str,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Update Job
    await db_instance.inspection_jobs.update_one(
        {"inspection_id": inspection_id},
        {"$set": {
            "status": "FAILED",
            "failed_stage": stage_name,
            "last_successful_stage": last_successful_stage,
            "error_type": error_type,
            "error_message": error_str,
            "traceback": traceback_str,
            "updated_at": datetime.utcnow()
        }}
    )

async def _run_pipeline_loop(inspection_id: str, start_index: int = 0):
    current_stage_name = "unknown"
    last_successful_stage = None
    started_at = datetime.utcnow()
    try:
        session = await db_instance.analysis_sessions.find_one({"session_id": inspection_id})
        vessel_id = session.get("vessel_id") if session else None
        visit_id = session.get("visit_id") if session else None
        
        # Populate last_successful_stage if resuming
        insp_session = await db_instance.inspection_sessions.find_one({"session_id": inspection_id})
        if insp_session:
             last_successful_stage = insp_session.get("last_successful_stage")

        for i in range(start_index, len(PIPELINE_STAGES)):
            stage = PIPELINE_STAGES[i]
            current_stage_name = stage['name']
            stage_display = f"{current_stage_name.upper()}"
            started_at = datetime.utcnow()
            
            await log_stage_start(inspection_id, current_stage_name, started_at)
            
            # 1. Update status to running
            await _update_status(
                inspection_id, 
                f"{stage_display}_RUNNING", 
                stage["progress_start"], 
                f"{stage['stage_name']} Running"
            )
            
            # 2. Call Worker Generic Contract
            response = await trigger_generic_worker(stage, inspection_id, vessel_id, visit_id)
            
            duration = (datetime.utcnow() - started_at).total_seconds()
            
            # 3. HITL Check
            if response and response.get("status") == "needs_review":
                logger.info(f"[{inspection_id}] Pipeline paused for human review at stage: {current_stage_name}")
                
                await db_instance.inspection_sessions.update_one(
                    {"session_id": inspection_id},
                    {"$set": {
                        "review_checkpoint": current_stage_name,
                        "review_status": "pending_review",
                        "status": "needs_review"
                    }}
                )
                await db_instance.inspection_jobs.update_one(
                    {"inspection_id": inspection_id},
                    {"$set": {
                        "status": "PAUSED_FOR_REVIEW",
                        "updated_at": datetime.utcnow()
                    }}
                )
                return
            
            # 4. Success Log
            out_artifacts = response.get("artifacts", []) if response else []
            await log_stage_complete(inspection_id, current_stage_name, started_at, duration, out_artifacts)
            last_successful_stage = current_stage_name
            
            # 5. Update status to completed
            await _update_status(
                inspection_id, 
                f"{stage_display}_COMPLETED", 
                stage["progress_end"], 
                f"{stage['stage_name']} Completed"
            )
            
        # If we made it through all stages without pausing
        if session:
            await db_instance.analysis_sessions.update_one(
                {"session_id": inspection_id},
                {"$set": {"status": "Completed"}}
            )
        await _update_status(inspection_id, "COMPLETED", 100, "Pipeline Completed")
        logger.info(f"[{inspection_id}] Orchestration Pipeline Fully Completed.")
        
    except Exception as e:
        duration = (datetime.utcnow() - started_at).total_seconds()
        exc_type = type(e).__name__
        msg = str(e)
        tb_str = traceback.format_exc()
        
        await log_stage_failure(inspection_id, current_stage_name, started_at, duration, exc_type, msg, tb_str)
        await _fail_pipeline(inspection_id, current_stage_name, last_successful_stage, exc_type, msg, tb_str)
        raise

async def start_pipeline(inspection_id: str):
    logger.info(f"Starting orchestration pipeline for {inspection_id}")
    
    session = await db_instance.inspection_sessions.find_one({"session_id": inspection_id})
    start_index = 0
    
    if session and session.get("status") == "FAILED" and session.get("last_successful_stage"):
        last_success = session.get("last_successful_stage")
        logger.info(f"[{inspection_id}] Recovering pipeline. Last successful stage was: {last_success}")
        for i, stage in enumerate(PIPELINE_STAGES):
            if stage["name"] == last_success:
                start_index = i + 1
                break
                
    if start_index == 0:
        await db_instance.inspection_jobs.update_one(
            {"inspection_id": inspection_id},
            {"$set": {"status": "UPLOADED", "updated_at": datetime.utcnow()}},
            upsert=True
        )
    
    await _run_pipeline_loop(inspection_id, start_index=start_index)

async def resume_pipeline(inspection_id: str):
    logger.info(f"Resuming orchestration pipeline for {inspection_id} after HITL review")
    
    session = await db_instance.inspection_sessions.find_one({"session_id": inspection_id})
    if not session:
        raise Exception(f"Session not found for inspection: {inspection_id}")
        
    checkpoint = session.get("review_checkpoint")
    if not checkpoint:
        raise Exception("No review checkpoint found. Cannot resume.")
        
    # Find the index to resume from (the stage after the checkpoint)
    start_index = 0
    for i, stage in enumerate(PIPELINE_STAGES):
        if stage["name"] == checkpoint:
            start_index = i + 1
            break
            
    if start_index >= len(PIPELINE_STAGES):
        logger.info(f"[{inspection_id}] Resumed at the end of the pipeline. No more stages.")
        # Mark as completed
        await db_instance.analysis_sessions.update_one(
            {"session_id": inspection_id},
            {"$set": {"status": "Completed"}}
        )
        await _update_status(inspection_id, "COMPLETED", 100, "Pipeline Completed")
        return
        
    # Clear review flags
    await db_instance.inspection_sessions.update_one(
        {"session_id": inspection_id},
        {"$set": {
            "review_checkpoint": None,
            "review_status": "approved"
        }}
    )
        
    await _run_pipeline_loop(inspection_id, start_index=start_index)

class OrchestrationService:
    def start_job(self, inspection_id: str):
        import asyncio
        asyncio.create_task(start_pipeline(inspection_id))
        
    def resume_job(self, inspection_id: str):
        import asyncio
        asyncio.create_task(resume_pipeline(inspection_id))

orchestration_service = OrchestrationService()
