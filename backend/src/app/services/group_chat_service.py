"""
Group Chat Service
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.group_chat import GroupChatInDB
from datetime import datetime
from bson.errors import InvalidId

class GroupChatService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.group_chats
        self.users_collection = db.users

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string in dictionary"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, list):
                result[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
            elif isinstance(value, dict):
                result[key] = self._convert_to_dict(value)
            else:
                result[key] = value
        return result

    async def create_group_chat(
        self,
        organization_id: str,
        name: str,
        created_by: str,
        member_ids: List[str],
        description: Optional[str] = None
    ) -> GroupChatInDB:
        """Create a new group chat"""
        group_data = {
            "organization_id": organization_id,
            "name": name,
            "description": description,
            "created_by": created_by,
            "members": member_ids + [created_by],  # Include creator
            "admins": [created_by],  # Creator is admin
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }

        result = await self.collection.insert_one(group_data)
        group_data["_id"] = str(result.inserted_id)
        return GroupChatInDB(**group_data)

    async def get_group_chat(self, group_id: str) -> Optional[GroupChatInDB]:
        """Get a group chat by ID"""
        try:
            group_data = await self.collection.find_one({"_id": ObjectId(group_id)})
            if group_data:
                group_data = self._convert_to_dict(group_data)
                return GroupChatInDB(**group_data)
        except (InvalidId, Exception):
            return None
        return None

    async def get_user_groups(self, user_id: str, organization_id: str) -> List[GroupChatInDB]:
        """Get all groups a user is a member of"""
        groups = []
        cursor = self.collection.find({
            "organization_id": organization_id,
            "members": user_id,
            "is_active": True
        }).sort("updated_at", -1)

        async for group_data in cursor:
            group_data = self._convert_to_dict(group_data)
            groups.append(GroupChatInDB(**group_data))

        return groups

    async def add_members(self, group_id: str, user_ids: List[str]) -> bool:
        """Add members to a group"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(group_id)},
                {
                    "$addToSet": {"members": {"$each": user_ids}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except (InvalidId, Exception):
            return False

    async def remove_member(self, group_id: str, user_id: str) -> bool:
        """Remove a member from a group"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(group_id)},
                {
                    "$pull": {"members": user_id, "admins": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except (InvalidId, Exception):
            return False

    async def update_group(self, group_id: str, update_data: dict) -> bool:
        """Update group chat details"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"_id": ObjectId(group_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except (InvalidId, Exception):
            return False

    async def add_admin(self, group_id: str, user_id: str) -> bool:
        """Add an admin to a group"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(group_id)},
                {
                    "$addToSet": {"admins": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except (InvalidId, Exception):
            return False

    async def remove_admin(self, group_id: str, user_id: str) -> bool:
        """Remove an admin from a group"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(group_id)},
                {
                    "$pull": {"admins": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except (InvalidId, Exception):
            return False


