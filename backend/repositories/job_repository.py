import os
from typing import Optional, Dict, Any
from database import get_db

class JobRepository:
    def __init__(self):
        pass
        
    @property
    def collection(self):
        return get_db().inspection_jobs

    async def create_job(self, inspection_id: str, video_path: str) -> dict:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        job = {
            "inspection_id": inspection_id,
            "status": "VIDEO_UPLOADED",
            "video_path": video_path,
            "created_at": now,
            "updated_at": now
        }
        await self.collection.insert_one(job)
        return job

    async def get_job(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"inspection_id": inspection_id})

    async def update_status(self, inspection_id: str, status: str, extra_data: dict = None) -> bool:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        update_doc = {
            "status": status,
            "updated_at": now
        }
        if extra_data:
            update_doc.update(extra_data)
            
        result = await self.collection.update_one(
            {"inspection_id": inspection_id},
            {"$set": update_doc}
        )
        return result.modified_count > 0

job_repository = JobRepository()
