import json
import os
from datetime import datetime, timezone
from typing import Any

import pymongo

from config import settings
from services.pipeline_logger import log_pipeline_error

sync_client = pymongo.MongoClient(settings.MONGODB_URL)
sync_db = sync_client[settings.DATABASE_NAME]
trace_collection = sync_db["pipeline_traces"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineTraceWriter:
    def __init__(self, session_id: str, output_path: str):
        self.session_id = session_id
        self.output_path = output_path
        self.trace_path = os.path.join(output_path, "pipeline_trace.json")
        self.entries: list[dict[str, Any]] = []
        os.makedirs(output_path, exist_ok=True)

    def record(
        self,
        *,
        service: str,
        port: int | None = None,
        service_url: str | None = None,
        event: str,
        status: str,
        started_at: str | None = None,
        duration_ms: float | None = None,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        issues: list[str] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": utc_now_iso(),
            "session_id": self.session_id,
            "service": service,
            "port": port,
            "service_url": service_url,
            "event": event,
            "status": status,
            "started_at": started_at,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "request": request or {},
            "response": response or {},
            "issues": issues or [],
            "note": note,
        }
        self.entries.append(entry)
        self.save()
        return entry

    def summary(self) -> dict[str, Any]:
        total_time_ms = round(
            sum(entry.get("duration_ms") or 0 for entry in self.entries),
            2,
        )
        issue_count = sum(len(entry.get("issues") or []) for entry in self.entries)
        return {
            "session_id": self.session_id,
            "trace_path": self.trace_path,
            "events": len(self.entries),
            "total_time_ms": total_time_ms,
            "issue_count": issue_count,
            "last_event": self.entries[-1] if self.entries else None,
        }

    def save(self) -> None:
        try:
            with open(self.trace_path, "w", encoding="utf-8") as file:
                json.dump(self.entries, file, indent=2, default=str)

            trace_collection.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "session_id": self.session_id,
                        "trace_path": self.trace_path,
                        "entries": self.entries,
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            log_pipeline_error(self.session_id, "trace", "failed to persist pipeline trace", error=str(exc))
            raise


def load_trace(session_id: str | None = None, trace_path: str | None = None) -> list[dict[str, Any]]:
    if session_id:
        doc = trace_collection.find_one({"session_id": session_id})
        if doc is not None:
            entries = doc.get("entries") or []
            if entries:
                return entries

    if not trace_path or not os.path.exists(trace_path):
        return []

    with open(trace_path, "r", encoding="utf-8") as file:
        return json.load(file)
