from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from config import settings
import uuid
import os

router = APIRouter()

assets_dir = os.path.join(settings.upload_folder, "assets")
os.makedirs(assets_dir, exist_ok=True)

@router.get("/assets/{file_id}")
async def get_asset(file_id: str):
    # Ensure no path traversal
    safe_file_id = os.path.basename(file_id)
    file_path = os.path.join(assets_dir, safe_file_id)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)

@router.post("/internal/upload")
async def internal_upload(
    file: UploadFile = File(...),
):
    # Generate unique id
    safe_filename = os.path.basename(file.filename)
    file_id = f"{uuid.uuid4()}_{safe_filename}"
    file_path = os.path.join(assets_dir, file_id)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    return {
        "file_id": file_id,
        "filename": safe_filename,
        "url": f"/api/v1/assets/{file_id}"
    }
