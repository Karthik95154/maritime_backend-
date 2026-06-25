import logging
from datetime import datetime
from database import db_instance
import uuid

logger = logging.getLogger(__name__)

async def run_temporal_consistency(inspection_id: str, vessel_id: str = None, visit_id: str = None, classification: list = None, detection: list = None):
    logger.info(f"[{inspection_id}] Running Temporal Consistency...")
    
    # In a real CV pipeline, this would use IOU (Intersection over Union) matching
    # between bounding boxes across consecutive frames.
    # For MVP orchestration, we group by defect_type and part_name to form tracks.
    
    # Map frames to their classification part
    part_map = {}
    if classification:
        for c in classification:
            part_map[c["frame_id"]] = c["part_name"]
            
    # Group detections by defect type and part
    tracks = {}
    if detection:
        for d in detection:
            f_id = d["frame_id"]
            d_type = d["defect_type"]
            part = part_map.get(f_id, "unknown_part")
            
            key = f"{part}_{d_type}"
            if key not in tracks:
                tracks[key] = {
                    "track_id": str(uuid.uuid4()),
                    "part_name": part,
                    "defect_type": d_type,
                    "frame_ids": set()
                }
            tracks[key]["frame_ids"].add(f_id)
            
    # Insert tracks into Mongo
    from models import TemporalTrack
    records = []
    for key, track in tracks.items():
        t_record = TemporalTrack(
            track_id=track["track_id"],
            inspection_id=inspection_id,
            vessel_id=vessel_id,
            visit_id=visit_id,
            part_name=track["part_name"],
            defect_type=track["defect_type"],
            frame_ids=list(track["frame_ids"])
        )
        records.append(t_record.model_dump())
        
    if records:
        await db_instance.temporal_tracks.insert_many(records)
        logger.info(f"[{inspection_id}] Created {len(records)} temporal tracks.")
    else:
        logger.info(f"[{inspection_id}] No defects detected, 0 tracks created.")
