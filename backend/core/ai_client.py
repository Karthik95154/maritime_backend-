import httpx
import logging
import os
from database import db_instance

logger = logging.getLogger(__name__)

from config import settings

async def trigger_generic_worker(stage_config: dict, inspection_id: str, vessel_id: str = None, visit_id: str = None):
    # Check if this stage should run locally on CPU
    is_local = stage_config.get("is_local", False)
    
    if is_local:
        logger.info(f"[{inspection_id}] Executing LOCAL stage: {stage_config['name']}")
        from services.local_worker_service import local_worker
        return await local_worker.execute_local_stage(
            stage_config["name"], 
            inspection_id, 
            vessel_id, 
            visit_id
        )

    logger.info(f"[{inspection_id}] Executing REMOTE stage: {stage_config['name']}")

    # Determine URL for remote execution
    env_key = stage_config.get("endpoint_env")
    worker_url = os.getenv(env_key, getattr(settings, env_key, ""))
    if not worker_url:
        logger.warning(f"[{inspection_id}] No URL configured for {stage_config['name']}, falling back to localhost:8000")
        worker_url = "http://localhost:8000"
        
    logger.info(f"[{inspection_id}] Resolving worker URL for {stage_config['name']} pipeline: {worker_url}")
    
    requires_video = stage_config.get("requires_video", False)
    
    async with httpx.AsyncClient(timeout=3600) as client:
        url = f"{worker_url}/process/{inspection_id}"
        
        try:
            logger.info(f"[{inspection_id}] Starting httpx POST request to {stage_config['name']} Worker...")
            
            msg = (
                "HTTP Request Started\n"
                "↓\n"
                "Worker Connected\n"
                "↓\n"
                "Worker Running\n"
                "↓"
            )
            logger.info(f"\n{msg}")
            
            if requires_video:
                inspection_doc = await db_instance.inspections.find_one({"inspection_id": inspection_id})
                if not inspection_doc or not inspection_doc.get("video_path"):
                    raise Exception(f"Video path not found in DB for inspection_id: {inspection_id}")
                
                video_path = inspection_doc["video_path"]
                if not os.path.exists(video_path):
                    raise Exception(f"Backend error: Video file not found at local path: {video_path}")
                
                with open(video_path, "rb") as f:
                    files = {
                        "video": (
                            "original_video.mp4",
                            f,
                            "video/mp4"
                        )
                    }
                    response = await client.post(url, files=files)
            else:
                # Standard JSON payload worker contract
                payload = {
                    "inspection_id": inspection_id,
                    "vessel_id": vessel_id,
                    "visit_id": visit_id
                }
                response = await client.post(url, json=payload)
                
            response.raise_for_status()
            logger.info(f"[{inspection_id}] {stage_config['name']} Worker request completed. STATUS: {response.status_code}")
            
            msg = (
                "Worker Response Received\n"
                "↓\n"
                "Artifacts Uploaded\n"
                "↓\n"
                "SUCCESS"
            )
            logger.info(f"\n{msg}")
            
            content_type = response.headers.get("content-type", "")
            if "application/zip" in content_type:
                output_dir = os.path.join(os.getcwd(), "outputs")
                os.makedirs(output_dir, exist_ok=True)
                zip_path = os.path.join(output_dir, f"{inspection_id}_output.zip")
                with open(zip_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"[{inspection_id}] Saved ZIP response to {zip_path}")
                return {"status": "success", "file_path": zip_path}

            return response.json()
            
        except httpx.TimeoutException as e:
            logger.info("\nTimeout")
            logger.error(f"[{inspection_id}] Timeout calling {stage_config['name']} Worker: {e}")
            raise Exception("Worker timed out") from e
        except httpx.ConnectError as e:
            logger.info("\nConnection Refused")
            logger.error(f"[{inspection_id}] Connection Refused calling {stage_config['name']} Worker: {e}")
            raise Exception("Worker connection refused") from e
        except Exception as e:
            logger.info("\nHTTP Error")
            logger.error(f"[{inspection_id}] Error calling {stage_config['name']} Worker: {e}")
            raise

