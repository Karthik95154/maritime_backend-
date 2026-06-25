from datetime import datetime
from typing import Any

import pymongo
from loguru import logger

from config import settings

sync_client = pymongo.MongoClient(settings.MONGODB_URL)
sync_db = sync_client[settings.DATABASE_NAME]
events_collection = sync_db["app_events"]


def log_app_event(
    event: str,
    message: str,
    *,
    user_email: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    level: str = "info",
    **details: Any,
) -> None:
    payload = {
        "timestamp": datetime.utcnow(),
        "event": event,
        "message": message,
        "user_email": user_email,
        "session_id": session_id,
        "request_id": request_id,
        "details": details,
    }
    events_collection.insert_one(payload)

    prefix = "[app]"
    if user_email:
        prefix = f"{prefix}[{user_email}]"
    if session_id:
        prefix = f"{prefix}[{session_id}]"
    if request_id:
        prefix = f"{prefix}[{request_id}]"

    entry = f"{prefix} {event}: {message}"
    if details:
        entry += f" | {details}"
    getattr(logger, level, logger.info)(entry)


def log_app_error(event: str, message: str, **details: Any) -> None:
    log_app_event(event, message, level="error", **details)
