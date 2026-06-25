import os
import httpx
from loguru import logger
from fastapi import FastAPI
from config import settings
from database import connect_to_mongo, close_mongo_connection
from services.pipeline_logger import log_pipeline_event
from core.api_gateway import setup_api_gateway

# Configure central logger
logger.add(
    "backend.log",
    rotation="100 MB"
)

# Initialize bare FastAPI app
app = FastAPI(
    title=settings.project_name,
    version="1.0.0"
)

# Attach Gateway Layer (Routers, Middleware, Exception Handlers)
setup_api_gateway(app)

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    log_pipeline_event(None, "startup", "backend_start", "backend startup complete", api_base=settings.api_v1_str)
    
    gpu_url = os.getenv("GPU_SERVICE_URL", "https://postbox-onscreen-desecrate.ngrok-free.dev").rstrip("/")
    logger.info(f"GPU_SERVICE_URL = {gpu_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{gpu_url}/health", headers={"ngrok-skip-browser-warning": "69420"})
            logger.info("[GPU HEALTH CHECK]")
            logger.info(f"Status: {response.status_code}")
            logger.info(response.text)
    except Exception as e:
        logger.warning(f"[GPU HEALTH CHECK FAILED] Worker offline. Details: {e}. Will retry during orchestration.")
        
@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()
    log_pipeline_event(None, "shutdown", "backend_stop", "backend shutdown started")
