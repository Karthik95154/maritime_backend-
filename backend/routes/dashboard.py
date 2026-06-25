from fastapi import APIRouter
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("")
async def get_dashboard():
    return await AnalyticsService.get_dashboard()
