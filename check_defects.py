import asyncio
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from backend.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    session = await db.inspection_sessions.find_one(sort=[('created_at', -1)])
    if session:
        print(f"Session ID: {session.get('session_id')}")
        
        output_path = session.get("output_path")
        
        # Adjust output_path since we are running in d:\maritime_web_codex
        # and output_path might be relative to backend/
        if output_path and not output_path.startswith(os.path.sep):
            full_path = os.path.join("backend", output_path)
        else:
            full_path = output_path
            
        print(f"Full Output Path: {full_path}")
        
        if full_path and os.path.exists(full_path):
            repair_json = os.path.join(full_path, "module_5_repair_estimation_output", "repair_estimation_outputs.json")
            if os.path.exists(repair_json):
                with open(repair_json, "r") as f:
                    data = json.load(f)
                    print(f"Defect Count in repair JSON: {len(data.get('defect_repairs', {}))}")
            else:
                print("No repair JSON found.")
            
            unique_json = os.path.join(full_path, "module_4_unique_defect_frame_output", "unique_defect_outputs.json")
            if os.path.exists(unique_json):
                with open(unique_json, "r") as f:
                    data = json.load(f)
                    print(f"Defect Count in unique JSON: {len(data)}")
            else:
                print("No unique JSON found.")
        else:
            print("Output path does not exist on disk.")
    client.close()

asyncio.run(main())
