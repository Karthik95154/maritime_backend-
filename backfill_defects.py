import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add backend to sys.path so we can import its modules
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.config import settings
from backend.modules.defect_matching_engine import DefectMatchingEngine

async def main():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    engine = DefectMatchingEngine(db=db)
    
    sessions = await db.inspection_sessions.find().to_list(length=None)
    for s in sessions:
        session_id = s.get("session_id")
        output_path = s.get("output_path")
        if not output_path:
            continue
        repair_json = os.path.join(output_path, "module_5_repair_estimation_output", "repair_estimation_outputs.json")
        if os.path.exists(repair_json):
            print(f"Processing session {session_id}...")
            try:
                await engine.process_session(session_id, repair_json)
                print(f"Successfully backfilled session {session_id}")
            except Exception as e:
                print(f"Error backfilling session {session_id}: {e}")
        else:
            print(f"Repair JSON not found for session {session_id}")

    print("Backfill complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
