import os

from fastapi import APIRouter, HTTPException

from database import get_db
from services.pipeline_trace import load_trace

router = APIRouter(prefix="/pipeline", tags=["pipeline-trace"])


@router.get("/trace/{session_id}")
async def get_pipeline_trace(session_id: str):
    db = get_db()
    session = await db.inspection_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    output_path = session.get("output_path")
    trace_path = os.path.join(output_path, "pipeline_trace.json") if output_path else None
    trace_entries = load_trace(session_id=session_id, trace_path=trace_path)

    return {
        "session_id": session_id,
        "trace_path": trace_path,
        "event_count": len(trace_entries),
        "trace": trace_entries,
    }


@router.get("/trace/{session_id}/summary")
async def get_pipeline_trace_summary(session_id: str):
    db = get_db()
    session = await db.inspection_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    output_path = session.get("output_path")
    trace_path = os.path.join(output_path, "pipeline_trace.json") if output_path else None
    trace_entries = load_trace(session_id=session_id, trace_path=trace_path)
    total_time_ms = round(
        sum(entry.get("duration_ms") or 0 for entry in trace_entries),
        2,
    )
    issues = [issue for entry in trace_entries for issue in (entry.get("issues") or [])]

    return {
        "session_id": session_id,
        "trace_path": trace_path,
        "events": len(trace_entries),
        "total_time_ms": total_time_ms,
        "issue_count": len(issues),
        "issues": issues,
        "stages": [
            {
                "service": entry.get("service"),
                "port": entry.get("port"),
                "service_url": entry.get("service_url"),
                "status": entry.get("status"),
                "duration_ms": entry.get("duration_ms"),
                "issues": entry.get("issues") or [],
            }
            for entry in trace_entries
        ],
    }
