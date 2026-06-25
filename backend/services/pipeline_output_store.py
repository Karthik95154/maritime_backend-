from datetime import datetime
from typing import Any

import pymongo

from config import settings
from services.pipeline_logger import log_pipeline_event, log_pipeline_error

sync_client = pymongo.MongoClient(settings.MONGODB_URL)
sync_db = sync_client[settings.DATABASE_NAME]
outputs_collection = sync_db["pipeline_stage_outputs"]


def store_stage_output(
    session_id: str,
    stage_key: str,
    data: Any,
    *,
    file_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        outputs_collection.update_one(
            {"session_id": session_id, "stage_key": stage_key},
            {
                "$set": {
                    "session_id": session_id,
                    "stage_key": stage_key,
                    "data": data,
                    "file_path": file_path,
                    "metadata": metadata or {},
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        log_pipeline_event(
            session_id,
            stage_key,
            "output_stored",
            "stage output stored in MongoDB",
            file_path=file_path,
            metadata=metadata or {},
        )
    except Exception as exc:
        log_pipeline_error(session_id, stage_key, "failed to store stage output in MongoDB", error=str(exc))
        raise


def load_stage_output(session_id: str, stage_key: str) -> Any | None:
    doc = outputs_collection.find_one({"session_id": session_id, "stage_key": stage_key})
    if doc is None:
        return None
    return doc.get("data")


def list_stage_outputs(session_id: str) -> list[dict[str, Any]]:
    return list(outputs_collection.find({"session_id": session_id}, {"_id": 0}))
