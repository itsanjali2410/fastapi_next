"""
Chat service
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.chat import MessageInDB
from datetime import datetime

class ChatService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.messages

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value
            else:
                result[key] = value
        return result

    async def send_message(self, message_data: dict) -> MessageInDB:
        """Send a message"""
        message_data["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(message_data)
        message_data["_id"] = str(result.inserted_id)
        return MessageInDB(**message_data)

    async def get_messages(self, org_id: str, skip: int = 0, limit: int = 100) -> List[MessageInDB]:
        """Get messages for an organization"""
        messages = []
        cursor = self.collection.find({"org_id": org_id}).skip(skip).limit(limit).sort("created_at", 1)
        async for msg_data in cursor:
            msg_data = self._convert_to_dict(msg_data)
            messages.append(MessageInDB(**msg_data))
        return messages

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"is_read": True}}
            )
            return result.modified_count > 0
        except Exception:
            return False

