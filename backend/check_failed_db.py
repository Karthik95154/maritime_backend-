import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    uri = "mongodb+srv://karthik:Karthik951@cluster0.auw8xop.mongodb.net/?retryWrites=true&w=majority"
    client = AsyncIOMotorClient(uri)
    db = client.maritime_inspection
    
    # Get the latest failed session
    session = await db.inspection_sessions.find_one({"status": "FAILED"})
    if session:
        print(f"Failed Stage: {session.get('failed_stage')}")
        print(f"Error Type: {session.get('error_type')}")
        print(f"Error Message: {session.get('error_message')}")
        print(f"Traceback:\n{session.get('traceback')}")
    else:
        print("No failed sessions found.")

if __name__ == "__main__":
    asyncio.run(main())
