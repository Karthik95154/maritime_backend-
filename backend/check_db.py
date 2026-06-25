import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.maritime_ai
    fs = db.fs.files
    doc = await fs.find_one({"_id": ObjectId("6a3266facc5612c93ce8edd0")})
    if doc:
        print(f"File Size in DB: {doc['length']} bytes")
    else:
        print("Not found")

asyncio.run(main())
