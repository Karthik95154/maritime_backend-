import os
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    # Collections
    users = None
    roles = None
    vessels = None
    inspections = None
    inspection_jobs = None
    frame_results = None
    classification_results = None
    segmentation_results = None
    defect_results = None
    repair_estimations = None
    human_reviews = None
    reports = None
    audit_logs = None
    inspection_sessions = None
    analysis_sessions = None
    drydock_visits = None
    defect_registry = None
    temporal_tracks = None
    cds_results = None
    unique_defects = None
    area_results = None

db_instance = Database()

async def connect_to_mongo():
    logger.info(f"MongoDB URL: {settings.MONGODB_URL}")
    logger.info(f"Database: {settings.DATABASE_NAME}")
    
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]
    
    # Verify connection
    try:
        await db_instance.db.command("ping")
        logger.info("Successfully pinged MongoDB.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

    # Initialize collections
    db_instance.users = db_instance.db["users"]
    db_instance.roles = db_instance.db["roles"]
    db_instance.vessels = db_instance.db["vessels"]
    db_instance.inspections = db_instance.db["inspections"]
    db_instance.inspection_jobs = db_instance.db["inspection_jobs"]
    db_instance.frame_results = db_instance.db["frame_results"]
    db_instance.classification_results = db_instance.db["classification_results"]
    db_instance.segmentation_results = db_instance.db["segmentation_results"]
    db_instance.defect_results = db_instance.db["defect_results"]
    db_instance.repair_estimations = db_instance.db["repair_estimations"]
    db_instance.human_reviews = db_instance.db["human_reviews"]
    db_instance.reports = db_instance.db["reports"]
    db_instance.audit_logs = db_instance.db["audit_logs"]
    db_instance.inspection_sessions = db_instance.db["inspection_sessions"]
    db_instance.analysis_sessions = db_instance.db["analysis_sessions"]
    db_instance.drydock_visits = db_instance.db["drydock_visits"]
    db_instance.defect_registry = db_instance.db["defect_registry"]
    db_instance.temporal_tracks = db_instance.db["temporal_tracks"]
    db_instance.cds_results = db_instance.db["cds_results"]
    db_instance.unique_defects = db_instance.db["unique_defects"]
    db_instance.area_results = db_instance.db["area_results"]

    # Initialize indexes
    await db_instance.frame_results.create_index("inspection_id")
    await db_instance.cds_results.create_index("inspection_id")
    await db_instance.unique_defects.create_index("inspection_id")
    await db_instance.area_results.create_index("inspection_id")
    await db_instance.repair_estimations.create_index("inspection_id")
    await db_instance.reports.create_index("inspection_id")
    await db_instance.inspection_jobs.create_index("inspection_id")

    logger.info("Successfully connected to MongoDB and initialized collections.")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("Closed MongoDB connection.")

def get_db():
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db_instance.db
