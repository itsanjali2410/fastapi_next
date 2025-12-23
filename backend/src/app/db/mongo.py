from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from src.app.core.config import settings

client: Optional[AsyncIOMotorClient] = None
db = None


async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    print("✅ Connected to MongoDB")


async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("❌ MongoDB connection closed")


def get_database():
    if db is None:
        raise RuntimeError("Database not initialized")
    return db
