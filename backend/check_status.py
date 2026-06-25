import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from backend.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    session = await db.inspection_sessions.find_one(sort=[('created_at', -1)])
    if session:
        print(f"Session status: {session.get('status')}")
        print(f"Progress: {session.get('progress')}")
        print(f"Current stage: {session.get('current_stage')}")
        print(f"Pipeline error (if any): {session.get('pipeline_error')}")
    client.close()

asyncio.run(main())
