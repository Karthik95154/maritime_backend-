import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    session = await db.inspection_sessions.find_one()
    if session:
        print(f"Session path: {session.get('output_path')}")
    else:
        print("No sessions found")
    client.close()

asyncio.run(main())
