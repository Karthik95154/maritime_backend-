import logging
import os
import shutil
import uuid
from datetime import datetime
from database import db_instance

logger = logging.getLogger(__name__)

async def run_unique_defect_extraction(inspection_id: str, vessel_id: str = None, visit_id: str = None):
    logger.info(f"[{inspection_id}] Running Unique Defect Extraction...")
    
    # Fetch tracks
    tracks = await db_instance.temporal_tracks.find({"inspection_id": inspection_id}).to_list(length=None)
    
    if not tracks:
        logger.info(f"[{inspection_id}] No tracks to process for unique defects.")
        return
        
    session_dir = os.path.join("outputs", "sessions", inspection_id)
    frames_dir = os.path.join(session_dir, "frames")
    defects_dir = os.path.join(session_dir, "defects")
    os.makedirs(defects_dir, exist_ok=True)
    
    from models import DefectRegister
    records = []
    
    for track in tracks:
        track_id = track["track_id"]
        frame_ids = track.get("frame_ids", [])
        
        if not frame_ids:
            continue
            
        # Select best frame (just pick the middle one for MVP)
        best_frame_id = frame_ids[len(frame_ids) // 2]
        
        # Find the physical file
        src_frame_path = None
        for ext in ['.jpg', '.png']:
            possible_path = os.path.join(frames_dir, f"{best_frame_id}{ext}")
            if os.path.exists(possible_path):
                src_frame_path = possible_path
                break
                
        defect_id = str(uuid.uuid4())
        crop_path = ""
        
        if src_frame_path:
            # Generate crop (For MVP backend, we copy the best frame as the "crop" representation)
            # In a full CV env, cv2.imread and array slicing using detection bbox would occur here.
            ext = os.path.splitext(src_frame_path)[1]
            dst_crop = os.path.join(defects_dir, f"{defect_id}{ext}")
            shutil.copy(src_frame_path, dst_crop)
            crop_path = os.path.abspath(dst_crop)
            
        # Determine Severity based on defect_type heuristically
        d_type = track["defect_type"].lower()
        severity = "LOW"
        if "corrosion" in d_type or "crack" in d_type:
            severity = "HIGH"
        elif "peeling" in d_type or "rust" in d_type:
            severity = "MEDIUM"
            
        d_record = DefectRegister(
            defect_id=defect_id,
            inspection_id=inspection_id,
            vessel_id=vessel_id,
            visit_id=visit_id,
            part_name=track["part_name"],
            defect_type=track["defect_type"],
            severity=severity,
            crop_path=crop_path,
            status="OPEN"
        )
        records.append(d_record.model_dump())
        
    if records:
        await db_instance.defect_registry.insert_many(records)
        logger.info(f"[{inspection_id}] Inserted {len(records)} unique defects into Defect Register.")
