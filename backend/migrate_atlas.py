import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    local_client = AsyncIOMotorClient('mongodb://localhost:27017/')
    atlas_client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    
    local_db = local_client['maritime_inspection']
    atlas_db = atlas_client['maritime_inspection']
    
    # Collections to migrate
    collections_to_migrate = [
        "users",
        "roles",
        "vessels",
        "inspection_sessions",
        "analysis_sessions",
        "drydock_visits",
        "defect_registry"
    ]
    
    for coll_name in collections_to_migrate:
        print(f"Migrating collection: {coll_name}")
        local_coll = local_db[coll_name]
        atlas_coll = atlas_db[coll_name]
        
        # Get all documents from local
        docs = await local_coll.find({}).to_list(length=None)
        
        if docs:
            try:
                # Insert to Atlas
                await atlas_coll.insert_many(docs)
                print(f"  -> Successfully migrated {len(docs)} documents.")
            except Exception as e:
                print(f"  -> Failed migrating {coll_name}: {e}")
        else:
            print(f"  -> Collection {coll_name} is empty or does not exist locally.")
            
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
