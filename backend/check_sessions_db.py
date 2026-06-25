import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    uri = "mongodb+srv://karthik:Karthik951@cluster0.auw8xop.mongodb.net/?retryWrites=true&w=majority"
    client = AsyncIOMotorClient(uri)
    db = client.maritime_inspection
    
    sessions = await db.inspection_sessions.find().sort("created_at", -1).limit(5).to_list(length=None)
    for s in sessions:
        print(f"Session ID: {s.get('session_id')} | Status: {s.get('status')} | Stage: {s.get('current_stage')}")
        print(f"Progress: {s.get('progress')}")

if __name__ == "__main__":
    asyncio.run(main())
