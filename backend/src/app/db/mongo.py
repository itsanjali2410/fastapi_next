"""
MongoDB connection management using Motor (async driver)
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo_db = MongoDB()


async def connect_to_mongo():
    """Establish connection to MongoDB on startup."""
    try:
        mongo_db.client = AsyncIOMotorClient(settings.MONGO_URL)
        mongo_db.db = mongo_db.client[settings.DB_NAME]
        print(f"✅ Connected to MongoDB database: {settings.DB_NAME}")
    except Exception as e:
        print("❌ Error connecting to MongoDB:", e)
        raise e


async def close_mongo_connection():
    """Close MongoDB connection on shutdown."""
    if mongo_db.client:
        mongo_db.client.close()
        print("🔌 MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Dependency injection: returns active DB instance."""
    if mongo_db.db is None:
        # This prevents the 'NoneType has no attribute users' error
        raise RuntimeError(
            "MongoDB is not initialized. connect_to_mongo() did NOT run. "
            "Ensure app.add_event_handler('startup', connect_to_mongo) is set."
        )
    return mongo_db.db
