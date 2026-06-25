from fastapi import APIRouter, Request
from pydantic import BaseModel

from services.app_activity_logger import log_app_event, log_app_error

router = APIRouter(prefix="/app-events", tags=["app-events"])


class AppEventPayload(BaseModel):
    event: str
    message: str
    user_email: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    route: str | None = None
    component: str | None = None
    action: str | None = None
    metadata: dict | None = None


@router.post("")
async def record_app_event(payload: AppEventPayload, request: Request):
    try:
        log_app_event(
            payload.event,
            payload.message,
            user_email=payload.user_email,
            session_id=payload.session_id,
            request_id=payload.request_id,
            route=payload.route,
            component=payload.component,
            action=payload.action,
            metadata=payload.metadata or {},
            source="frontend",
            remote_host=request.client.host if request.client else None,
        )
        return {"status": "ok"}
    except Exception as exc:
        log_app_error("app_event_record_failed", "failed to store app event", error=str(exc))
        return {"status": "error", "detail": str(exc)}
