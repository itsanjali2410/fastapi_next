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
from src.app.schemas.enhanced_message_schema import EnhancedMessageCreate
from src.app.dependencies import get_current_user, get_user_service
from src.app.services.messages_service import MessagesService
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB
from src.app.db.mongo import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from bson import ObjectId

router = APIRouter()

def get_messages_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessagesService:
    """Get MessagesService instance"""
    return MessagesService(db)

@router.post("/send", response_model=MessageResponse)
async def send_message(
    message_data: dict,  # Accept both MessageCreate and EnhancedMessageCreate
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Send a message (1-to-1 or group).
    Supports reply_to, group_chat_id, and enhanced features.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    receiver_id = message_data.get("receiver_id")
    group_chat_id = message_data.get("group_chat_id")
    content = message_data.get("content")
    reply_to = message_data.get("reply_to")
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required"
        )
    
    if not receiver_id and not group_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either receiver_id or group_chat_id is required"
        )
    
    # For 1-to-1 messages, verify receiver
    receiver_name = None
    if receiver_id:
        receiver = await user_service.get_user_by_id(receiver_id)
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
        receiver_name = receiver.name
    
    # Store message in database with enhanced features
    message_doc = {
        "organization_id": current_user.org_id,
        "sender_id": current_user.id,
        "receiver_id": receiver_id,
        "group_chat_id": group_chat_id,
        "content": content,
        "reply_to": reply_to,
        "edited": False,
        "deleted": False,
        "reactions": [],
        "delivery_status": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_read": False
    }
    
    result = await messages_service.collection.insert_one(message_doc)
    message_doc["_id"] = str(result.inserted_id)
    
    # Emit Socket.io event
    from src.app.socketio_manager import socketio_manager
    message_payload = {
        "id": message_doc["_id"],
        "organization_id": message_doc["organization_id"],
        "sender_id": message_doc["sender_id"],
        "receiver_id": message_doc.get("receiver_id"),
        "group_chat_id": message_doc.get("group_chat_id"),
        "content": message_doc["content"],
        "reply_to": message_doc.get("reply_to"),
        "created_at": message_doc["created_at"].isoformat(),
        "is_read": message_doc["is_read"],
        "sender_name": current_user.name
    }
    
    if receiver_id:
        await socketio_manager.emit_new_message(receiver_id, message_payload)
        await socketio_manager.emit_new_message(current_user.id, message_payload)
        # Emit chat list update to both users
        await socketio_manager.emit_chat_list_update(receiver_id)
        await socketio_manager.emit_chat_list_update(current_user.id)
    elif group_chat_id:
        # Emit to all group members
        from src.app.services.group_chat_service import GroupChatService
        db = get_database()
        group_service = GroupChatService(db)
        group = await group_service.get_group_chat(group_chat_id)
        if group:
            for member_id in group.members:
                await socketio_manager.emit_new_message(member_id, message_payload)
                await socketio_manager.emit_chat_list_update(member_id)
    
    return MessageResponse(
        id=message_doc["_id"],
        organization_id=message_doc["organization_id"],
        sender_id=message_doc["sender_id"],
        receiver_id=message_doc.get("receiver_id", ""),
        content=message_doc["content"],
        created_at=message_doc["created_at"],
        is_read=message_doc["is_read"],
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
    
    # Get messages with replyTo lookup using aggregation
    from bson import ObjectId
    messages_collection = messages_service.collection
    
    # Build query
    query = {
        "organization_id": current_user.org_id,
        "$or": [
            {"sender_id": current_user.id, "receiver_id": other_user_id},
            {"sender_id": other_user_id, "receiver_id": current_user.id}
        ]
    }
    
    if before_timestamp:
        query["created_at"] = {"$lt": before_timestamp}
    
    # Use aggregation pipeline to include replyTo lookup
    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": 1}},
        {"$limit": limit + 1},  # Fetch one extra to check if more exist
        {
            "$lookup": {
                "from": "messages",
                "localField": "reply_to",
                "foreignField": "_id",
                "as": "quoted_message"
            }
        },
        {
            "$addFields": {
                "quoted_message": {
                    "$arrayElemAt": ["$quoted_message", 0]
                }
            }
        }
    ]
    
    messages_data = []
    async for msg_data in messages_collection.aggregate(pipeline):
        # Convert ObjectId to string
        if isinstance(msg_data.get("_id"), ObjectId):
            msg_data["_id"] = str(msg_data["_id"])
        
        # Convert quoted message _id if exists
        if msg_data.get("quoted_message") and isinstance(msg_data["quoted_message"].get("_id"), ObjectId):
            msg_data["quoted_message"]["_id"] = str(msg_data["quoted_message"]["_id"])
        
        messages_data.append(msg_data)
    
    # Determine if more messages exist
    has_more = len(messages_data) > limit
    messages_to_return = messages_data[:limit]
    
    # Build message responses
    user_cache = {
        current_user.id: current_user.name,
        other_user_id: other_user.name
    }
    
    message_responses = []
    for msg_data in messages_to_return:
        sender_id = msg_data.get("sender_id")
        sender_name = user_cache.get(sender_id, "Unknown")
        receiver_name = user_cache.get(msg_data.get("receiver_id"), "Unknown")
        
        message_responses.append(MessageResponse(
            id=msg_data["_id"],
            organization_id=msg_data.get("organization_id"),
            sender_id=sender_id,
            receiver_id=msg_data.get("receiver_id"),
            content=msg_data.get("content", ""),
            created_at=msg_data.get("created_at"),
            is_read=msg_data.get("is_read", False),
            sender_name=sender_name,
            receiver_name=receiver_name
        ))
    
    return MessageHistoryResponse(
        messages=message_responses,
        total=len(message_responses),
        has_more=has_more
    )

@router.get("/group/{group_id}/history", response_model=MessageHistoryResponse)
async def get_group_message_history(
    group_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[str] = Query(default=None),
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get message history for a group chat"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Verify user is member of group
    from src.app.services.group_chat_service import GroupChatService
    db = get_database()
    group_service = GroupChatService(db)
    group = await group_service.get_group_chat(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group chat not found"
        )
    
    if current_user.id not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )
    
    # Get messages
    before_timestamp = None
    if before:
        try:
            before_timestamp = datetime.fromisoformat(before.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format"
            )
    
    query = {"group_chat_id": group_id}
    if before_timestamp:
        query["created_at"] = {"$lt": before_timestamp}
    
    messages = []
    cursor = (
        messages_service.collection
        .find(query)
        .sort("created_at", 1)
        .limit(limit + 1)
    )
    
    async for msg_data in cursor:
        msg_data = messages_service._convert_to_dict(msg_data)
        from src.app.models.message import MessageInDB
        messages.append(MessageInDB(**msg_data))
    
    has_more = len(messages) > limit
    messages_to_return = messages[:limit]
    
    # Get user names
    user_ids = list(set([msg.sender_id for msg in messages_to_return]))
    user_names = {}
    for user_id in user_ids:
        user = await user_service.get_user_by_id(user_id)
        if user:
            user_names[user_id] = user.name
    
    message_responses = []
    for msg in messages_to_return:
        message_responses.append(MessageResponse(
            id=msg.id,
            organization_id=msg.organization_id,
            sender_id=msg.sender_id,
            receiver_id="",  # Group messages don't have receiver_id
            content=msg.content,
            created_at=msg.created_at,
            is_read=msg.is_read,
            sender_name=user_names.get(msg.sender_id, "Unknown"),
            receiver_name=None
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

@router.put("/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: str,
    update_data: dict,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service),
    user_service: UserService = Depends(get_user_service)
):
    """Edit a message"""
    # Verify message exists and belongs to user
    message = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message["sender_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages"
        )
    
    # Update message
    await messages_service.collection.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$set": {
                "content": update_data.get("content", message["content"]),
                "edited": True,
                "edited_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Return updated message
    updated = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
    updated = messages_service._convert_to_dict(updated)
    sender = await user_service.get_user_by_id(updated["sender_id"])
    receiver = await user_service.get_user_by_id(updated["receiver_id"]) if updated.get("receiver_id") else None
    
    # Emit update via Socket.io
    from src.app.socketio_manager import socketio_manager
    user_ids = []
    if updated.get("receiver_id"):
        user_ids = [updated["sender_id"], updated["receiver_id"]]
    elif updated.get("group_chat_id"):
        from src.app.services.group_chat_service import GroupChatService
        db = get_database()
        group_service = GroupChatService(db)
        group = await group_service.get_group_chat(updated["group_chat_id"])
        if group:
            user_ids = group.members
    
    await socketio_manager.emit_message_updated(user_ids, updated)
    
    return MessageResponse(
        id=str(updated["_id"]),
        organization_id=updated["organization_id"],
        sender_id=updated["sender_id"],
        receiver_id=updated.get("receiver_id", ""),
        content=updated["content"],
        created_at=updated["created_at"],
        is_read=updated.get("is_read", False),
        sender_name=sender.name if sender else None,
        receiver_name=receiver.name if receiver else None
    )

@router.delete("/{message_id}", response_model=dict)
async def delete_message(
    message_id: str,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """Delete a message (soft delete)"""
    message = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message["sender_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages"
        )
    
    await messages_service.collection.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$set": {
                "deleted": True,
                "deleted_at": datetime.utcnow(),
                "content": "[Message deleted]",
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Emit delete via Socket.io
    from src.app.socketio_manager import socketio_manager
    user_ids = []
    if message.get("receiver_id"):
        user_ids = [message["sender_id"], message["receiver_id"]]
    elif message.get("group_chat_id"):
        from src.app.services.group_chat_service import GroupChatService
        db = get_database()
        if db:
            group_service = GroupChatService(db)
            group = await group_service.get_group_chat(message["group_chat_id"])
            if group:
                user_ids = group.members
    
    await socketio_manager.emit_message_deleted(user_ids, message_id)
    
    return {"message": "Message deleted successfully"}

@router.post("/{message_id}/reaction", response_model=dict)
async def add_reaction(
    message_id: str,
    reaction_data: dict,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """Add or remove a reaction to a message"""
    emoji = reaction_data.get("emoji")
    if not emoji:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Emoji is required"
        )
    
    message = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    reactions = message.get("reactions", [])
    # Remove existing reaction from this user
    reactions = [r for r in reactions if r.get("user_id") != current_user.id]
    # Add new reaction
    reactions.append({
        "user_id": current_user.id,
        "emoji": emoji,
        "created_at": datetime.utcnow()
    })
    
    await messages_service.collection.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"reactions": reactions, "updated_at": datetime.utcnow()}}
    )
    
    # Emit update via Socket.io
    from src.app.socketio_manager import socketio_manager
    updated_message = messages_service._convert_to_dict(message)
    updated_message["reactions"] = reactions
    
    user_ids = []
    if message.get("receiver_id"):
        user_ids = [message["sender_id"], message["receiver_id"]]
    elif message.get("group_chat_id"):
        from src.app.services.group_chat_service import GroupChatService
        db = get_database()
        if db:
            group_service = GroupChatService(db)
            group = await group_service.get_group_chat(message["group_chat_id"])
            if group:
                user_ids = group.members
    
    await socketio_manager.emit_message_updated(user_ids, updated_message)
    
    return {"message": "Reaction added successfully"}

@router.post("/{message_id}/mark-read", response_model=dict)
async def mark_message_read(
    message_id: str,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """Mark a message as read and update delivery status"""
    message = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Update read status
    delivery_status = message.get("delivery_status", {})
    if current_user.id not in delivery_status:
        delivery_status[current_user.id] = {}
    
    delivery_status[current_user.id]["delivered"] = True
    delivery_status[current_user.id]["read"] = True
    delivery_status[current_user.id]["read_at"] = datetime.utcnow()
    delivery_status[current_user.id]["read_by"] = current_user.id
    
    await messages_service.collection.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$set": {
                "is_read": True,
                "delivery_status": delivery_status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Message marked as read"}

@router.post("/mark-all-read", response_model=dict)
async def mark_all_messages_read(
    data: dict,
    current_user: UserInDB = Depends(get_current_user),
    messages_service: MessagesService = Depends(get_messages_service)
):
    """Mark all unread messages in a conversation as read"""
    receiver_id = data.get("receiver_id")
    group_chat_id = data.get("group_chat_id")
    
    if not receiver_id and not group_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either receiver_id or group_chat_id is required"
        )
    
    # Build query for unread messages
    query = {
        "is_read": False,
        "organization_id": current_user.org_id
    }
    
    if receiver_id:
        # For 1-to-1: messages where sender is the other user and receiver is current user
        # Only mark messages sent TO current user as read
        query["sender_id"] = receiver_id
        query["receiver_id"] = current_user.id
    elif group_chat_id:
        # For group: all messages in the group (not filtered by receiver_id)
        query["group_chat_id"] = group_chat_id
    
    # Update all unread messages
    now = datetime.utcnow()
    result = await messages_service.collection.update_many(
        query,
        {
            "$set": {
                "is_read": True,
                "updated_at": now
            },
            "$setOnInsert": {
                "delivery_status": {}
            }
        }
    )
    
    # Update delivery_status for all updated messages
    if result.modified_count > 0:
        # Get all updated messages to update their delivery_status
        updated_messages = []
        async for msg in messages_service.collection.find(query):
            delivery_status = msg.get("delivery_status", {})
            if current_user.id not in delivery_status:
                delivery_status[current_user.id] = {}
            delivery_status[current_user.id]["delivered"] = True
            delivery_status[current_user.id]["read"] = True
            delivery_status[current_user.id]["read_at"] = now
            delivery_status[current_user.id]["read_by"] = current_user.id
            
            await messages_service.collection.update_one(
                {"_id": msg["_id"]},
                {"$set": {"delivery_status": delivery_status}}
            )
    
    # Emit chat list update to both users (for 1-to-1) or all group members
    from src.app.socketio_manager import socketio_manager
    if receiver_id:
        await socketio_manager.emit_chat_list_update(current_user.id)
        await socketio_manager.emit_chat_list_update(receiver_id)
        await socketio_manager.emit_messages_read(receiver_id, current_user.id)
    elif group_chat_id:
        from src.app.services.group_chat_service import GroupChatService
        db = get_database()
        group_service = GroupChatService(db)
        group = await group_service.get_group_chat(group_chat_id)
        if group:
            for member_id in group.members:
                await socketio_manager.emit_chat_list_update(member_id)
    
    return {"message": f"Marked {result.modified_count} messages as read"}
