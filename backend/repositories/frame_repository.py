from typing import List, Dict, Any
from database import get_db

class FrameRepository:
    def __init__(self):
        pass

    @property
    def collection(self):
        return get_db().frame_results

    async def create_many(self, frames: List[Dict[str, Any]]) -> bool:
        if not frames:
            return False
        result = await self.collection.insert_many(frames)
        return len(result.inserted_ids) > 0

    async def get_by_inspection(self, inspection_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"inspection_id": inspection_id}).sort("frame_id", 1)
        frames = await cursor.to_list(length=None)
        return frames

    async def delete_by_inspection(self, inspection_id: str) -> bool:
        result = await self.collection.delete_many({"inspection_id": inspection_id})
        return result.deleted_count > 0

frame_repository = FrameRepository()
