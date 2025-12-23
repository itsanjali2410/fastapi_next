from motor.motor_asyncio import AsyncIOMotorClient
from src.app.core.config import settings

client = None
db = None

async def connect_to_mongo():
    global client, db
    try:
        client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        await client.admin.command("ping")
        db = client[settings.MONGO_DB]
        print("✅ MongoDB connected")
    except Exception as e:
        print("❌ MongoDB connection failed:", e)

async def close_mongo_connection():
    if client:
        client.close()
        print("🔌 MongoDB connection closed")
