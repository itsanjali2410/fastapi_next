"""
Messages service - Business logic for messaging with unified inbox (ConversationParticipants)
"""
import asyncio
from typing import Optional, List, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.message import MessageInDB
from src.app.models.user import UserInDB
from src.app.models.conversation_participant import ConversationParticipant
from datetime import datetime
from bson.errors import InvalidId


class MessagesService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.messages
        self.users_collection = db.users
        self.conversations_collection = db.conversation_participants

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
            elif isinstance(value, list):
                result[key] = [
                    self._convert_to_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @staticmethod
    def get_dm_conversation_id(user1_id: str, user2_id: str) -> str:
        """Generate a deterministic conversation ID for a 1-on-1 chat."""
        sorted_ids = sorted([user1_id, user2_id])
        return f"dm_{sorted_ids[0]}_{sorted_ids[1]}"

    async def upsert_conversation_participants(
        self,
        conversation_id: Union[ObjectId, str],
        convo_type: str,
        participants: List[dict],
        last_message_content: Optional[str],
        last_message_at: Optional[datetime],
        sender_id: Optional[str] = None,
        conversation_image: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        """Fan-out write: Update ConversationParticipants for all participants."""
        if isinstance(conversation_id, str) and conversation_id.startswith("dm_"):
            conv_id_value = conversation_id
        else:
            if not isinstance(conversation_id, ObjectId):
                conv_id_value = ObjectId(conversation_id)
            else:
                conv_id_value = conversation_id

        tasks = []
        for participant in participants:
            user_id = participant["user_id"]
            display_name = participant.get("display_name")
            image = participant.get("image") or conversation_image
            other_user_id = participant.get("other_user_id")
            is_sender = (sender_id and user_id == sender_id)

            set_doc = {
                "user_id": user_id,
                "conversation_id": str(conv_id_value),
                "type": convo_type,
                "name": display_name,
                "last_message_content": last_message_content,
                "last_message_at": last_message_at,
            }

            if image:
                set_doc["image"] = image
            if other_user_id:
                set_doc["other_user_id"] = other_user_id
            if group_id:
                set_doc["group_id"] = group_id

            filter_query = {
                "user_id": user_id,
                "conversation_id": str(conv_id_value)
            }

            if not is_sender and last_message_content:
                update_operation = {
                    "$set": set_doc,
                    "$inc": {"unread_count": 1}
                }
            else:
                set_doc["unread_count"] = 0
                update_operation = {"$set": set_doc}

            tasks.append(
                self.conversations_collection.update_one(
                    filter_query,
                    update_operation,
                    upsert=True
                )
            )

        if tasks:
            await asyncio.gather(*tasks)

    async def get_conversations_for_user(self, user_id: str) -> List[ConversationParticipant]:
        """Get unified inbox: All conversations (DMs + Groups) for a user."""
        cursor = (
            self.conversations_collection
            .find({"user_id": user_id})
            .sort("last_message_at", -1)
        )

        conversations = []
        async for doc in cursor:
            doc = self._convert_to_dict(doc)
            conversations.append(ConversationParticipant(**doc))

        return conversations

    async def mark_conversation_read(self, user_id: str, conversation_id: str) -> bool:
        """Mark all messages in a conversation as read (reset unread_count to 0)."""
        result = await self.conversations_collection.update_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {"$set": {"unread_count": 0}}
        )
        return result.modified_count > 0 or result.matched_count > 0

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
        """Get message history between two users."""
        query = {
            "$or": [
                {"sender_id": user1_id, "receiver_id": user2_id},
                {"sender_id": user2_id, "receiver_id": user1_id}
            ]
        }
        
        if before_timestamp:
            query["created_at"] = {"$lt": before_timestamp}
        
        messages = []
        cursor = (
            self.collection
            .find(query)
            .sort("created_at", 1)
            .limit(limit + 1)
        )
        
        async for msg_data in cursor:
            msg_data = self._convert_to_dict(msg_data)
            messages.append(MessageInDB(**msg_data))
        
        return messages

    async def get_chat_list(self, user_id: str, organization_id: str) -> List[dict]:
        """Legacy method: Get chat list using aggregation pipeline."""
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
                continue
        
        return chats

    async def get_organization_users(
        self,
        organization_id: str,
        current_user_id: str
    ) -> List[UserInDB]:
        """Get all organization members except the current user."""
        try:
            org = await self.db.organizations.find_one({"_id": ObjectId(organization_id)})
            if not org:
                return []
            
            member_ids = org.get("members", [])
            filtered_member_ids = []
            for mid in member_ids:
                mid_str = str(mid) if isinstance(mid, ObjectId) else mid
                if mid_str != current_user_id:
                    filtered_member_ids.append(mid)
            
            users = []
            for member_id in filtered_member_ids:
                try:
                    member_obj_id = member_id if isinstance(member_id, ObjectId) else ObjectId(member_id)
                    user_data = await self.users_collection.find_one({"_id": member_obj_id})
                    if user_data:
                        user_data = self._convert_to_dict(user_data)
                        users.append(UserInDB(**user_data))
                except (InvalidId, Exception):
                    continue
            
            return users
        except (InvalidId, Exception):
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
