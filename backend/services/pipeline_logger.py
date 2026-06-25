from datetime import datetime
from typing import Any

import pymongo
from loguru import logger

from config import settings

sync_client = pymongo.MongoClient(settings.MONGODB_URL)
sync_db = sync_client[settings.DATABASE_NAME]
events_collection = sync_db["pipeline_events"]


def log_pipeline_event(
    session_id: str | None,
    stage: str,
    event: str,
    message: str,
    *,
    level: str = "info",
    **details: Any,
) -> None:
    payload = {
        "timestamp": datetime.utcnow(),
        "session_id": session_id,
        "stage": stage,
        "event": event,
        "message": message,
        "details": details,
    }
    events_collection.insert_one(payload)

    prefix = f"[{session_id}]" if session_id else "[pipeline]"
    entry = f"{prefix}[{stage}] {event}: {message}"

    log_method = getattr(logger, level, logger.info)
    log_method(entry)


def log_pipeline_error(session_id: str | None, stage: str, message: str, **details: Any) -> None:
    log_pipeline_event(session_id, stage, "error", message, level="error", **details)

async def log_stage_start(inspection_id: str, stage_name: str, started_at: datetime):
    msg = (
        "=" * 57 + "\n"
        f"Inspection ID : {inspection_id}\n\n"
        f"Stage : {stage_name.upper()}\n\n"
        "Status : RUNNING\n\n"
        f"Started : {started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        + "=" * 57
    )
    logger.info(f"\n{msg}")

async def log_stage_complete(inspection_id: str, stage_name: str, started_at: datetime, duration: float, artifacts: list[str]):
    msg = (
        "=" * 57 + "\n"
        f"Inspection ID : {inspection_id}\n\n"
        f"Stage : {stage_name.upper()}\n\n"
        "Completed Successfully\n\n"
        f"Duration : {duration:.2f} sec\n\n"
        "Output Artifacts:\n"
    )
    for art in artifacts:
        msg += f"- {art}\n"
    msg += "=" * 57
    logger.info(f"\n{msg}")
    
    from database import db_instance
    await db_instance.pipeline_trace.insert_one({
        "inspection_id": inspection_id,
        "stage": stage_name,
        "status": "COMPLETED",
        "started_at": started_at,
        "completed_at": datetime.utcnow(),
        "duration": duration,
        "input_artifacts": [], # Filled elsewhere if needed
        "output_artifacts": artifacts
    })

async def log_stage_failure(inspection_id: str, stage_name: str, started_at: datetime, duration: float, exc_type: str, message: str, traceback_str: str):
    msg = (
        "=" * 57 + "\n"
        f"Inspection ID : {inspection_id}\n\n"
        f"Stage : {stage_name.upper()}\n\n"
        "Status : FAILED\n\n"
        "Exception Type :\n"
        f"{exc_type}\n\n"
        "Message :\n"
        f"{message}\n\n"
        "Traceback :\n"
        f"{traceback_str}\n\n"
        "Duration :\n"
        f"{duration:.2f} sec\n"
        + "=" * 57
    )
    logger.info(f"\n{msg}")

    from database import db_instance
    await db_instance.pipeline_trace.insert_one({
        "inspection_id": inspection_id,
        "stage": stage_name,
        "status": "FAILED",
        "started_at": started_at,
        "failed_at": datetime.utcnow(),
        "duration": duration,
        "exception_type": exc_type,
        "error_message": message,
        "traceback": traceback_str
    })
