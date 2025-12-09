"""
Messages service - Business logic for one-to-one messaging
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.message import MessageInDB
from src.app.models.user import UserInDB
from datetime import datetime
from bson.errors import InvalidId

class MessagesService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.messages
        self.users_collection = db.users

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string in dictionary"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = self._convert_to_dict(value)
            else:
                result[key] = value
        return result

    async def send_message(
        self, 
        organization_id: str,
        sender_id: str,
        receiver_id: str,
        content: str
    ) -> MessageInDB:
        """Store a new message in the database"""
        message_data = {
            "organization_id": organization_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "created_at": datetime.utcnow(),
            "is_read": False
        }
        
        result = await self.collection.insert_one(message_data)
        message_data["_id"] = str(result.inserted_id)
        return MessageInDB(**message_data)

    async def get_message_history(
        self,
        user1_id: str,
        user2_id: str,
        limit: int = 50,
        before_timestamp: Optional[datetime] = None
    ) -> List[MessageInDB]:
        """
        Get message history between two users.
        Returns messages where:
        - sender_id = user1 AND receiver_id = user2
        OR
        - sender_id = user2 AND receiver_id = user1
        Sorted by created_at ascending.
        
        Note: Fetches limit + 1 to determine if more messages exist.
        """
        query = {
            "$or": [
                {"sender_id": user1_id, "receiver_id": user2_id},
                {"sender_id": user2_id, "receiver_id": user1_id}
            ]
        }
        
        # Add timestamp filter if provided
        if before_timestamp:
            query["created_at"] = {"$lt": before_timestamp}
        
        messages = []
        # Fetch limit + 1 to determine if more messages exist
        cursor = (
            self.collection
            .find(query)
            .sort("created_at", 1)  # Ascending order
            .limit(limit + 1)
        )
        
        async for msg_data in cursor:
            msg_data = self._convert_to_dict(msg_data)
            messages.append(MessageInDB(**msg_data))
        
        return messages

    async def get_chat_list(self, user_id: str, organization_id: str) -> List[dict]:
        """
        Get chat list (WhatsApp-like) using MongoDB aggregation.
        Groups messages by the other user, gets last message and timestamp,
        sorts by recent activity (descending).
        """
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "$or": [
                        {"sender_id": user_id},
                        {"receiver_id": user_id}
                    ]
                }
            },
            {
                "$addFields": {
                    "other_user_id": {
                        "$cond": {
                            "if": {"$eq": ["$sender_id", user_id]},
                            "then": "$receiver_id",
                            "else": "$sender_id"
                        }
                    }
                }
            },
            {
                "$sort": {"created_at": -1}
            },
            {
                "$group": {
                    "_id": "$other_user_id",
                    "last_message": {"$first": "$content"},
                    "last_message_timestamp": {"$first": "$created_at"},
                    "unread_count": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$eq": ["$receiver_id", user_id]},
                                        {"$eq": ["$is_read", False]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$sort": {"last_message_timestamp": -1}
            }
        ]
        
        chats = []
        async for chat_data in self.collection.aggregate(pipeline):
            other_user_id = chat_data["_id"]
            
            # Get user details
            try:
                user_data = await self.users_collection.find_one({"_id": ObjectId(other_user_id)})
                if user_data:
                    user_data = self._convert_to_dict(user_data)
                    chats.append({
                        "other_user_id": other_user_id,
                        "other_user_name": user_data.get("name", "Unknown"),
                        "last_message": chat_data.get("last_message"),
                        "last_message_timestamp": chat_data.get("last_message_timestamp"),
                        "unread_count": chat_data.get("unread_count", 0)
                    })
            except (InvalidId, Exception):
                # Skip invalid user IDs
                continue
        
        return chats

    async def get_organization_users(
        self,
        organization_id: str,
        current_user_id: str
    ) -> List[UserInDB]:
        """
        Get all organization members except the current user.
        Used for starting new chats.
        """
        # First, get the organization to find its members
        try:
            org = await self.db.organizations.find_one({"_id": ObjectId(organization_id)})
            if not org:
                return []
            
            member_ids = org.get("members", [])
            # Convert ObjectId to string for comparison
            current_user_obj_id = ObjectId(current_user_id)
            # Filter out current user (handle both ObjectId and string formats)
            filtered_member_ids = []
            for mid in member_ids:
                # Convert to string for comparison
                mid_str = str(mid) if isinstance(mid, ObjectId) else mid
                if mid_str != current_user_id:
                    filtered_member_ids.append(mid)
            
            users = []
            for member_id in filtered_member_ids:
                try:
                    # Handle both ObjectId and string formats
                    member_obj_id = member_id if isinstance(member_id, ObjectId) else ObjectId(member_id)
                    user_data = await self.users_collection.find_one({"_id": member_obj_id})
                    if user_data:
                        user_data = self._convert_to_dict(user_data)
                        users.append(UserInDB(**user_data))
                except (InvalidId, Exception):
                    continue
            
            return users
        except (InvalidId, Exception) as e:
            return []

    async def mark_messages_as_read(
        self,
        sender_id: str,
        receiver_id: str
    ) -> int:
        """Mark all messages from sender to receiver as read"""
        result = await self.collection.update_many(
            {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "is_read": False
            },
            {
                "$set": {"is_read": True}
            }
        )
        return result.modified_count

    async def get_unread_count(
        self,
        user_id: str,
        organization_id: str
    ) -> int:
        """Get total unread message count for a user in an organization"""
        count = await self.collection.count_documents({
            "organization_id": organization_id,
            "receiver_id": user_id,
            "is_read": False
        })
        return count

