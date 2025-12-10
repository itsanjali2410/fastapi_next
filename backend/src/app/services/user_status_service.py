"""
User Status Service - Track online/offline and last seen
"""
from typing import Optional, List, Dict
from datetime import timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.user_status import UserStatusInDB
from datetime import datetime
from bson.errors import InvalidId

class UserStatusService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.user_statuses

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            else:
                result[key] = value
        return result

    async def update_status(self, user_id: str, is_online: bool) -> UserStatusInDB:
        """Update user online status"""
        status_data = {
            "user_id": user_id,
            "is_online": is_online,
            "last_seen": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Upsert status
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": status_data},
            upsert=True
        )

        return UserStatusInDB(**status_data)

    async def get_status(self, user_id: str) -> Optional[UserStatusInDB]:
        """Get user status"""
        status_data = await self.collection.find_one({"user_id": user_id})
        if status_data:
            status_data = self._convert_to_dict(status_data)
            return UserStatusInDB(**status_data)
        return None

    async def get_org_users_status(self, organization_id: str, user_ids: List[str]) -> Dict[str, UserStatusInDB]:
        """Get status for multiple users in an organization"""
        statuses = {}
        cursor = self.collection.find({"user_id": {"$in": user_ids}})
        
        async for status_data in cursor:
            status_data = self._convert_to_dict(status_data)
            status = UserStatusInDB(**status_data)
            statuses[status.user_id] = status

        # Create default offline status for users not found
        for user_id in user_ids:
            if user_id not in statuses:
                statuses[user_id] = UserStatusInDB(
                    user_id=user_id,
                    is_online=False,
                    last_seen=datetime.utcnow()
                )

        return statuses

    async def mark_offline_after_timeout(self, timeout_minutes: int = 5):
        """Mark users as offline if they haven't updated status in timeout period"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        await self.collection.update_many(
            {
                "is_online": True,
                "updated_at": {"$lt": cutoff_time}
            },
            {
                "$set": {
                    "is_online": False,
                    "last_seen": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

