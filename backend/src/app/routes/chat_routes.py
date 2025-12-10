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
    Get chat list (list of conversations).
    Returns all conversations grouped by other user with last message and timestamp.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    chats = await messages_service.get_chat_list(
        user_id=current_user.id,
        organization_id=current_user.org_id
    )
    
    # Transform to match frontend expected format
    chat_list = []
    for chat in chats:
        chat_list.append({
            "id": chat["other_user_id"],  # Use other_user_id as chat id
            "receiver_id": chat["other_user_id"],
            "receiver_name": chat["other_user_name"],
            "last_message": chat.get("last_message"),
            "last_message_time": chat.get("last_message_timestamp").isoformat() if chat.get("last_message_timestamp") else None,
            "unread_count": chat.get("unread_count",0)
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

