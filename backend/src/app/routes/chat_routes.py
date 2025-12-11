"""
Chat routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.chat_schema import MessageCreate, MessageResponse, ChatHistoryResponse
from src.app.schemas.message_schema import ChatListResponse, ChatListItem
from src.app.dependencies import get_current_user, get_chat_service, get_user_service
from src.app.services.chat_service import ChatService
from src.app.services.user_service import UserService
from src.app.services.messages_service import MessagesService
from src.app.models.user import UserInDB
from src.app.db.mongo import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

router = APIRouter()

def get_messages_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessagesService:
    """Get MessagesService instance"""
    return MessagesService(db)

@router.get("/list", response_model=List[dict])
async def get_chat_list(
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """
    Get unified chat list (personal chats + groups).
    Returns all conversations with lastMessage.createdAt for proper sorting.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Get personal chats
    personal_chats = await messages_service.get_chat_list(
        user_id=current_user.id,
        organization_id=current_user.org_id
    )
    
    # Get groups
    from src.app.services.group_chat_service import GroupChatService
    from src.app.db.mongo import get_database
    db = get_database()
    group_service = GroupChatService(db)
    groups = await group_service.get_user_groups(
        user_id=current_user.id,
        organization_id=current_user.org_id
    )
    
    # Transform personal chats to unified format
    chat_list = []
    for chat in personal_chats:
        last_message_timestamp = chat.get("last_message_timestamp")
        # Handle datetime conversion
        created_at_str = None
        if last_message_timestamp:
            if hasattr(last_message_timestamp, 'isoformat'):
                created_at_str = last_message_timestamp.isoformat()
            else:
                created_at_str = str(last_message_timestamp)
        
        chat_list.append({
            "type": "personal",
            "chatId": chat["other_user_id"],
            "receiver_id": chat["other_user_id"],
            "receiver_name": chat["other_user_name"],
            "name": chat["other_user_name"],
            "lastMessage": {
                "content": chat.get("last_message") or "",
                "createdAt": created_at_str
            },
            "last_message": chat.get("last_message"),
            "last_message_time": created_at_str,
            "unread_count": chat.get("unread_count", 0),
            "is_group": False
        })
    
    # Transform groups to unified format
    messages_collection = db.messages
    for group in groups:
        # Get last message for this group
        last_message = None
        last_message_timestamp = None
        async for msg in messages_collection.find(
            {"group_chat_id": group.id}
        ).sort("created_at", -1).limit(1):
            last_message = msg.get("content", "")
            last_message_timestamp = msg.get("created_at")
            break
        
        # Calculate unread count for this user
        unread_count = await messages_collection.count_documents({
            "group_chat_id": group.id,
            "readBy": {"$ne": current_user.id}
        })
        
        # Handle datetime conversion
        created_at_str = None
        if last_message_timestamp:
            if hasattr(last_message_timestamp, 'isoformat'):
                created_at_str = last_message_timestamp.isoformat()
            else:
                created_at_str = str(last_message_timestamp)
        
        chat_list.append({
            "type": "group",
            "chatId": group.id,
            "group_chat_id": group.id,
            "name": group.name,
            "lastMessage": {
                "content": last_message or "",
                "createdAt": created_at_str
            },
            "last_message": last_message,
            "last_message_time": created_at_str,
            "unread_count": unread_count,
            "is_group": True
        })
    
    return chat_list

@router.post("/read/{message_id}")
async def mark_message_read(
    message_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Mark message as read"""
    success = await chat_service.mark_as_read(message_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return {"message": "Message marked as read"}

