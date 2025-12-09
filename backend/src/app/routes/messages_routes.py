"""
Messages routes - One-to-one messaging endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.app.schemas.message_schema import (
    MessageCreate,
    MessageResponse,
    MessageHistoryResponse,
    ChatListResponse,
    UserListResponse,
    ChatListItem,
    UserListItem
)
from src.app.dependencies import get_current_user, get_user_service
from src.app.services.messages_service import MessagesService
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB
from src.app.db.mongo import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional

router = APIRouter()

def get_messages_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessagesService:
    """Get MessagesService instance"""
    return MessagesService(db)

@router.post("/send", response_model=MessageResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Send a one-to-one message.
    Stores the message and emits real-time update via Socket.io.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Verify receiver exists and is in the same organization
    receiver = await user_service.get_user_by_id(message_data.receiver_id)
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    if receiver.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send message to user outside your organization"
        )
    
    # Store message in database
    message = await messages_service.send_message(
        organization_id=current_user.org_id,
        sender_id=current_user.id,
        receiver_id=message_data.receiver_id,
        content=message_data.content
    )
    
    # Get receiver name for response
    receiver_name = receiver.name if receiver else "Unknown"
    
    # Emit Socket.io event to receiver
    from src.app.socketio_manager import socketio_manager
    await socketio_manager.emit_new_message(
        receiver_id=message_data.receiver_id,
        message={
            "id": message.id,
            "organization_id": message.organization_id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
            "sender_name": current_user.name
        }
    )
    
    # Also emit to sender for confirmation
    await socketio_manager.emit_new_message(
        receiver_id=current_user.id,
        message={
            "id": message.id,
            "organization_id": message.organization_id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
            "sender_name": current_user.name,
            "receiver_name": receiver_name
        }
    )
    
    return MessageResponse(
        id=message.id,
        organization_id=message.organization_id,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content,
        created_at=message.created_at,
        is_read=message.is_read,
        sender_name=current_user.name,
        receiver_name=receiver_name
    )

@router.get("/history/{other_user_id}", response_model=MessageHistoryResponse)
async def get_message_history(
    other_user_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[str] = Query(default=None, description="ISO format timestamp for pagination"),
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get message history between current user and another user.
    Supports pagination using 'before' timestamp and 'limit'.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Verify other user exists and is in the same organization
    other_user = await user_service.get_user_by_id(other_user_id)
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if other_user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view messages with user outside your organization"
        )
    
    # Parse before timestamp if provided
    before_timestamp = None
    if before:
        try:
            before_timestamp = datetime.fromisoformat(before.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format. Use ISO format."
            )
    
    # Get messages (service fetches limit + 1 to determine if more exist)
    messages = await messages_service.get_message_history(
        user1_id=current_user.id,
        user2_id=other_user_id,
        limit=limit,
        before_timestamp=before_timestamp
    )
    
    # Determine if more messages exist by checking if we got more than limit
    has_more = len(messages) > limit
    
    # Return only the requested limit (remove the extra message if present)
    messages_to_return = messages[:limit]
    
    # Batch fetch user data - only 2 users in a conversation, fetch once
    # Create a cache to avoid duplicate queries
    user_cache = {
        current_user.id: current_user.name,
        other_user_id: other_user.name
    }
    
    # Build message responses using cached user data
    message_responses = []
    for msg in messages_to_return:
        # Use cached user names (only 2 users in conversation)
        sender_name = user_cache.get(msg.sender_id, "Unknown")
        receiver_name = user_cache.get(msg.receiver_id, "Unknown")
        
        message_responses.append(MessageResponse(
            id=msg.id,
            organization_id=msg.organization_id,
            sender_id=msg.sender_id,
            receiver_id=msg.receiver_id,
            content=msg.content,
            created_at=msg.created_at,
            is_read=msg.is_read,
            sender_name=sender_name,
            receiver_name=receiver_name
        ))
    
    return MessageHistoryResponse(
        messages=message_responses,
        total=len(message_responses),
        has_more=has_more
    )

@router.get("/chats", response_model=ChatListResponse)
async def get_chat_list(
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """
    Get chat list (WhatsApp-like).
    Returns all conversations grouped by other user with last message and timestamp.
    Sorted by recent activity (descending).
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
    
    chat_items = [
        ChatListItem(
            other_user_id=chat["other_user_id"],
            other_user_name=chat["other_user_name"],
            last_message=chat.get("last_message"),
            last_message_timestamp=chat.get("last_message_timestamp"),
            unread_count=chat.get("unread_count", 0)
        )
        for chat in chats
    ]
    
    return ChatListResponse(chats=chat_items)

@router.get("/users", response_model=UserListResponse)
async def get_organization_users(
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """
    Get all organization members except the current user.
    Used for starting new chats.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    users = await messages_service.get_organization_users(
        organization_id=current_user.org_id,
        current_user_id=current_user.id
    )
    
    user_items = [
        UserListItem(
            id=user.id,
            name=user.name,
            email=user.email
        )
        for user in users
    ]
    
    return UserListResponse(users=user_items)


