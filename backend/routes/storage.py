import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from database import db_instance

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_OUTPUT_DIR = "outputs/sessions"

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _get_inspection_dir(inspection_id: str, subfolder: str) -> str:
    path = os.path.join(BASE_OUTPUT_DIR, inspection_id, subfolder)
    _ensure_dir(path)
    return path

async def _save_upload_file(upload_file: UploadFile, destination_path: str):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with open(destination_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            return
        except Exception as e:
            logger.info(f"\nRetry {attempt}")
            logger.error(f"Failed to save file {destination_path}: {e}")
            if attempt == max_retries:
                logger.info("\nFAILED")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not save file: {str(e)}"
                )
    upload_file.file.close()

# ==========================================
# UPLOAD APIS
# ==========================================

@router.post("/frame")
async def upload_frame(
    inspection_id: str = Form(...),
    frame_id: str = Form(...),
    timestamp: float = Form(None),
    file: UploadFile = File(...)
):
    if not inspection_id or not frame_id:
        raise HTTPException(status_code=400, detail="inspection_id and frame_id are required")
        
    filename = f"frame_{str(frame_id).zfill(6)}.jpg"
    logger.info(f"\nFRAME UPLOAD STARTED\nInspection: {inspection_id}\nFilename: {filename}")
    
    frames_dir = os.path.join("storage", "frames", inspection_id)
    os.makedirs(frames_dir, exist_ok=True)
    file_path = os.path.join(frames_dir, filename)
    
    await _save_upload_file(file, file_path)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="File save failed")
        
    abs_path = os.path.abspath(file_path)
    logger.info(f"\nFrame Saved:\nAbsolute Path: {abs_path}")
    
    backend_url_path = f"/api/v1/storage/frame/{inspection_id}/{filename}"
    
    from datetime import datetime
    await db_instance.db["inspection_artifacts"].update_one(
        {"inspection_id": inspection_id},
        {"$push": {"frames": {
            "frame_name": filename,
            "frame_path": backend_url_path,
            "created_at": datetime.utcnow().isoformat()
        }}},
        upsert=True
    )
    
    logger.info("\nMongo Updated\n\nReturning Success")
    
    return {
        "success": True,
        "frame_name": filename,
        "frame_path": backend_url_path
    }


@router.post("/defect")
async def upload_defect(
    inspection_id: str = Form(...),
    frame_id: str = Form(...),
    file: UploadFile = File(...)
):
    if not inspection_id or not frame_id:
        raise HTTPException(status_code=400, detail="inspection_id and frame_id are required")
        
    defects_dir = _get_inspection_dir(inspection_id, "defects")
    # Store with _annotated.jpg or similar, but the user requested saving it and returning path
    # Following user's example: frame_000085_annotated.jpg
    filename = f"frame_{str(frame_id).zfill(6)}_annotated.jpg"
    file_path = os.path.join(defects_dir, filename)
    
    await _save_upload_file(file, file_path)
    logger.info(f"[{inspection_id}] Saved defect to {file_path}")
    
    normalized_path = file_path.replace("\\", "/")
    
    await db_instance.db["inspection_artifacts"].update_one(
        {"inspection_id": inspection_id},
        {"$push": {"annotated_images": normalized_path}},
        upsert=True
    )
    
    logger.info("\nDEFECT UPLOADED\nMongo Updated")
    
    return {"success": True, "saved_path": normalized_path}


@router.post("/mask")
async def upload_mask(
    inspection_id: str = Form(...),
    frame_id: str = Form(...),
    mask_type: str = Form(...), # "part" or "defect"
    file: UploadFile = File(...)
):
    if not inspection_id or not frame_id or not mask_type:
        raise HTTPException(status_code=400, detail="inspection_id, frame_id, and mask_type are required")
        
    if mask_type not in ["part", "defect"]:
        raise HTTPException(status_code=400, detail="mask_type must be 'part' or 'defect'")
        
    masks_dir = _get_inspection_dir(inspection_id, "masks")
    # frame_000085_part.png or frame_000085_defect.png
    filename = f"frame_{str(frame_id).zfill(6)}_{mask_type}.png"
    file_path = os.path.join(masks_dir, filename)
    
    await _save_upload_file(file, file_path)
    logger.info(f"[{inspection_id}] Saved {mask_type} mask to {file_path}")
    
    normalized_path = file_path.replace("\\", "/")
    
    array_name = f"{mask_type}_masks" # part_masks or defect_masks
    await db_instance.db["inspection_artifacts"].update_one(
        {"inspection_id": inspection_id},
        {"$push": {array_name: normalized_path}},
        upsert=True
    )
    
    logger.info("\nMASK UPLOADED\nMongo Updated")
    
    return {"success": True, "saved_path": normalized_path}


@router.post("/area")
async def upload_area(
    inspection_id: str = Form(...),
    frame_id: str = Form(...),
    file: UploadFile = File(...)
):
    if not inspection_id or not frame_id:
        raise HTTPException(status_code=400, detail="inspection_id and frame_id are required")
        
    area_dir = _get_inspection_dir(inspection_id, "area")
    filename = f"frame_{str(frame_id).zfill(6)}_area.png"
    file_path = os.path.join(area_dir, filename)
    
    await _save_upload_file(file, file_path)
    logger.info(f"[{inspection_id}] Saved area result to {file_path}")
    
    normalized_path = file_path.replace("\\", "/")
    
    await db_instance.db["inspection_artifacts"].update_one(
        {"inspection_id": inspection_id},
        {"$push": {"area_results": normalized_path}},
        upsert=True
    )
    
    logger.info("\nAREA JSON UPLOADED\nMongo Updated")
    
    return {"success": True, "saved_path": normalized_path}


@router.post("/report")
async def upload_report(
    inspection_id: str = Form(...),
    report_type: str = Form(...),
    file: UploadFile = File(...)
):
    if not inspection_id or not report_type:
        raise HTTPException(status_code=400, detail="inspection_id and report_type are required")
        
    reports_dir = _get_inspection_dir(inspection_id, "reports")
    # e.g., report.pdf or summary.pdf based on report_type or uploaded filename
    extension = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    filename = f"{report_type}{extension}"
    file_path = os.path.join(reports_dir, filename)
    
    await _save_upload_file(file, file_path)
    logger.info(f"[{inspection_id}] Saved report to {file_path}")
    
    normalized_path = file_path.replace("\\", "/")
    
    await db_instance.db["inspection_artifacts"].update_one(
        {"inspection_id": inspection_id},
        {"$push": {"reports": normalized_path}},
        upsert=True
    )
    
    logger.info("\nREPORT SAVED\nMongo Updated")
    
    return {"success": True, "saved_path": normalized_path}


# ==========================================
# DOWNLOAD APIS
# ==========================================

def _get_file_response(inspection_id: str, subfolder: str, filename: str):
    file_path = os.path.join(BASE_OUTPUT_DIR, inspection_id, subfolder, filename)
    if not os.path.exists(file_path):
        logger.warning(f"File not found for download: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"[{inspection_id}] Serving file {file_path}")
    return FileResponse(file_path)


@router.get("/frame/{inspection_id}/{filename}")
async def download_frame(inspection_id: str, filename: str):
    logger.info(f"\nFRAME DOWNLOAD REQUEST\n\nInspection: {inspection_id}\nFilename: {filename}")
    
    file_path = os.path.join("storage", "frames", inspection_id, filename)
    resolved_path = os.path.abspath(file_path)
    file_exists = os.path.exists(file_path)
    
    logger.info(f"\nResolved Path: {resolved_path}\n\nFile Exists: {file_exists}")
    
    if not file_exists:
        logger.warning(f"\nFrame not found\nInspection: {inspection_id}\nFilename: {filename}\nExpected Path: {resolved_path}")
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)

@router.get("/defect/{inspection_id}/{filename}")
async def download_defect(inspection_id: str, filename: str):
    return _get_file_response(inspection_id, "defects", filename)

@router.get("/mask/{inspection_id}/{filename}")
async def download_mask(inspection_id: str, filename: str):
    return _get_file_response(inspection_id, "masks", filename)

@router.get("/area/{inspection_id}/{filename}")
async def download_area(inspection_id: str, filename: str):
    return _get_file_response(inspection_id, "area", filename)

@router.get("/report/{inspection_id}/{filename}")
async def download_report(inspection_id: str, filename: str):
    return _get_file_response(inspection_id, "reports", filename)
