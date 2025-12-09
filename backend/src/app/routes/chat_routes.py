"""
Chat routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.chat_schema import MessageCreate, MessageResponse, ChatHistoryResponse
from src.app.dependencies import get_current_user, get_chat_service, get_user_service
from src.app.services.chat_service import ChatService
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB
from typing import List

router = APIRouter()

# Note: /send route removed - use /api/v1/messages/send instead for one-to-one messaging
# Note: /messages route removed - use /api/v1/messages/history/{other_user_id} instead

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

