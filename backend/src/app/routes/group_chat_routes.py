"""
Group Chat routes
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.app.schemas.group_chat_schema import (
    GroupChatCreate,
    GroupChatUpdate,
    GroupChatResponse,
    GroupChatListResponse,
    GroupChatMemberAdd,
    GroupChatMemberRemove
)
from src.app.dependencies import get_current_user, get_group_chat_service, get_user_service
from src.app.services.group_chat_service import GroupChatService
from src.app.services.user_service import UserService
from src.app.services.messages_service import MessagesService
from src.app.models.user import UserInDB
from src.app.db.mongo import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter()

@router.post("", response_model=GroupChatResponse)
async def create_group_chat(
    group_data: GroupChatCreate,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    user_service: UserService = Depends(get_user_service)
):
    """Create a new group chat"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )

    # Verify all members exist and are in the same org
    for member_id in group_data.member_ids:
        member = await user_service.get_user_by_id(member_id)
        if not member or member.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member: {member_id}"
            )

    group = await group_service.create_group_chat(
        organization_id=current_user.org_id,
        name=group_data.name,
        created_by=current_user.id,
        member_ids=group_data.member_ids,
        description=group_data.description
    )

    # Get user names
    creator = await user_service.get_user_by_id(group.created_by)
    member_names = []
    for member_id in group.members:
        member = await user_service.get_user_by_id(member_id)
        if member:
            member_names.append(member.name)

    admin_names = []
    for admin_id in group.admins:
        admin = await user_service.get_user_by_id(admin_id)
        if admin:
            admin_names.append(admin.name)

    return GroupChatResponse(
        id=group.id,
        organization_id=group.organization_id,
        name=group.name,
        description=group.description,
        created_by=group.created_by,
        created_by_name=creator.name if creator else None,
        members=group.members,
        member_names=member_names,
        admins=group.admins,
        admin_names=admin_names,
        avatar_url=group.avatar_url,
        created_at=group.created_at,
        updated_at=group.updated_at,
        is_active=group.is_active
    )

@router.get("", response_model=GroupChatListResponse)
async def get_my_groups(
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service)
):
    """Get all groups the current user is a member of"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )

    groups = await group_service.get_user_groups(
        user_id=current_user.id,
        organization_id=current_user.org_id
    )

    # TODO: Get last message and unread count for each group
    group_items = []
    for group in groups:
        group_items.append({
            "id": group.id,
            "name": group.name,
            "avatar_url": group.avatar_url,
            "last_message": None,
            "last_message_timestamp": None,
            "unread_count": 0,
            "member_count": len(group.members)
        })

    return GroupChatListResponse(groups=group_items)

@router.get("/{group_id}", response_model=GroupChatResponse)
async def get_group_chat(
    group_id: str,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get group chat details"""
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

    # Get user names
    creator = await user_service.get_user_by_id(group.created_by)
    member_names = []
    for member_id in group.members:
        member = await user_service.get_user_by_id(member_id)
        if member:
            member_names.append(member.name)

    admin_names = []
    for admin_id in group.admins:
        admin = await user_service.get_user_by_id(admin_id)
        if admin:
            admin_names.append(admin.name)

    return GroupChatResponse(
        id=group.id,
        organization_id=group.organization_id,
        name=group.name,
        description=group.description,
        created_by=group.created_by,
        created_by_name=creator.name if creator else None,
        members=group.members,
        member_names=member_names,
        admins=group.admins,
        admin_names=admin_names,
        avatar_url=group.avatar_url,
        created_at=group.created_at,
        updated_at=group.updated_at,
        is_active=group.is_active
    )

@router.put("/{group_id}", response_model=GroupChatResponse)
async def update_group_chat(
    group_id: str,
    update_data: GroupChatUpdate,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    user_service: UserService = Depends(get_user_service)
):
    """Update group chat details (admin only)"""
    group = await group_service.get_group_chat(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group chat not found"
        )

    if current_user.id not in group.admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update group details"
        )

    update_dict = update_data.dict(exclude_unset=True)
    await group_service.update_group(group_id, update_dict)

    # Return updated group - build response inline
    updated_group = await group_service.get_group_chat(group_id)
    if not updated_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group chat not found"
        )

    # Get user names
    creator = await user_service.get_user_by_id(updated_group.created_by)
    member_names = []
    for member_id in updated_group.members:
        member = await user_service.get_user_by_id(member_id)
        if member:
            member_names.append(member.name)

    admin_names = []
    for admin_id in updated_group.admins:
        admin = await user_service.get_user_by_id(admin_id)
        if admin:
            admin_names.append(admin.name)

    return GroupChatResponse(
        id=updated_group.id,
        organization_id=updated_group.organization_id,
        name=updated_group.name,
        description=updated_group.description,
        created_by=updated_group.created_by,
        created_by_name=creator.name if creator else None,
        members=updated_group.members,
        member_names=member_names,
        admins=updated_group.admins,
        admin_names=admin_names,
        avatar_url=updated_group.avatar_url,
        created_at=updated_group.created_at,
        updated_at=updated_group.updated_at,
        is_active=updated_group.is_active
    )

@router.post("/{group_id}/members", response_model=dict)
async def add_members(
    group_id: str,
    member_data: GroupChatMemberAdd,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service)
):
    """Add members to a group (admin only)"""
    group = await group_service.get_group_chat(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group chat not found"
        )

    if current_user.id not in group.admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can add members"
        )

    success = await group_service.add_members(group_id, member_data.user_ids)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add members"
        )

    # Fetch updated group and broadcast changes
    updated_group = await group_service.get_group_chat(group_id)
    # Update conversation participants for all members
    from src.app.services.messages_service import MessagesService
    db = get_database()
    messages_service = MessagesService(db)
    participants = [{"user_id": m, "display_name": updated_group.name} for m in updated_group.members]
    await messages_service.upsert_conversation_participants(
        conversation_id=group_id,
        convo_type="group",
        participants=participants,
        last_message_content=None,
        last_message_at=None,
        group_id=group_id
    )

    # Emit group member added event
    from src.app.socketio_manager import socketio_manager
    added_names = []
    for uid in member_data.user_ids:
        user_obj = await db.users.find_one({"_id": ObjectId(uid)})
        if user_obj:
            added_names.append(user_obj.get("name", "Unknown"))

    if socketio_manager.sio:
        for member_id in updated_group.members:
            member_socket = socketio_manager.user_sockets.get(member_id)
            if member_socket:
                await socketio_manager.sio.emit('group_member_added', {
                    "groupId": group_id,
                    "addedUserIds": member_data.user_ids,
                    "addedUserNames": added_names
                }, room=member_socket)

    return {"message": "Members added successfully"}

@router.delete("/{group_id}/members/{user_id}", response_model=dict)
async def remove_member(
    group_id: str,
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service)
):
    """Remove a member from a group (admin only, or self)"""
    group = await group_service.get_group_chat(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group chat not found"
        )

    # User can remove themselves, or admin can remove anyone
    if user_id != current_user.id and current_user.id not in group.admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove other members"
        )

    success = await group_service.remove_member(group_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove member"
        )

    # Update conversation participants (remove the conversation entry for the removed user)
    from src.app.services.messages_service import MessagesService
    db = get_database()
    messages_service = MessagesService(db)
    await messages_service.conversations_collection.delete_one({"user_id": user_id, "conversation_id": group_id})

    # Emit group member removed event
    from src.app.socketio_manager import socketio_manager
    removed_name = None
    user_obj = await db.users.find_one({"_id": ObjectId(user_id)})
    if user_obj:
        removed_name = user_obj.get("name")

    updated_group = await group_service.get_group_chat(group_id)
    if socketio_manager.sio and updated_group:
        for member_id in updated_group.members:
            member_socket = socketio_manager.user_sockets.get(member_id)
            if member_socket:
                await socketio_manager.sio.emit('group_member_removed', {
                    "groupId": group_id,
                    "removedUserId": user_id,
                    "removedUserName": removed_name
                }, room=member_socket)

    return {"message": "Member removed successfully"}

@router.get("/{group_id}/messages")
async def get_group_messages(
    group_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get paginated messages for a group"""
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
    
    # Calculate skip
    skip = (page - 1) * limit
    
    # Get messages with replyTo lookup using aggregation
    messages_collection = db.messages
    pipeline = [
        {"$match": {"group_chat_id": group_id}},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
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
    
    messages = []
    user_service = UserService(db)
    async for msg_data in messages_collection.aggregate(pipeline):
        # Convert ObjectId to string
        if isinstance(msg_data.get("_id"), ObjectId):
            msg_data["_id"] = str(msg_data["_id"])
        
        # Convert quoted message _id if exists
        if msg_data.get("quoted_message") and isinstance(msg_data["quoted_message"].get("_id"), ObjectId):
            msg_data["quoted_message"]["_id"] = str(msg_data["quoted_message"]["_id"])
        
        # Get sender name
        sender_id = msg_data.get("sender_id")
        sender = await user_service.get_user_by_id(sender_id) if sender_id else None
        msg_data["sender_name"] = sender.name if sender else "Unknown"
        
        messages.append(msg_data)
    
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    
    # Get total count for pagination
    total_count = await messages_collection.count_documents({"group_chat_id": group_id})
    has_more = skip + len(messages) < total_count
    
    return {
        "messages": messages,
        "page": page,
        "limit": limit,
        "total": total_count,
        "has_more": has_more
    }

@router.post("/{group_id}/mark-read")
async def mark_group_messages_read(
    group_id: str,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Mark all unread messages in a group as read for the current user"""
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
    
    # Mark all unread messages as read by adding user to read_by array and record timestamps
    messages_collection = db.messages
    # First find the messages to update
    unread_query = {"group_chat_id": group_id, "read_by": {"$ne": current_user.id}}
    messages_to_update = []
    async for msg in messages_collection.find(unread_query):
        messages_to_update.append(msg["_id"])

    now = datetime.utcnow()
    for msg_id in messages_to_update:
        await messages_collection.update_one(
            {"_id": msg_id},
            {
                "$addToSet": {"read_by": current_user.id},
                "$set": {f"read_by_details.{current_user.id}": now}
            }
        )

    # Get updated unread count (should be 0 now)
    unread_count = await messages_collection.count_documents({
        "group_chat_id": group_id,
        "read_by": {"$ne": current_user.id}
    })
    
    # Emit unread update to user
    from src.app.socketio_manager import socketio_manager
    user_socket = socketio_manager.user_sockets.get(current_user.id)
    if user_socket and socketio_manager.sio:
        await socketio_manager.sio.emit('group_unread_update', {
            "groupId": group_id,
            "unreadCount": unread_count
        }, room=user_socket)

    # Emit group read update to all members so UI can show who saw messages
    if socketio_manager.sio and group:
        for member_id in group.members:
            member_socket = socketio_manager.user_sockets.get(member_id)
            if member_socket:
                await socketio_manager.sio.emit('group_read_update', {
                    "groupId": group_id,
                    "userId": current_user.id,
                    "userName": current_user.name,
                    "seenAt": now.isoformat()
                }, room=member_socket)

    return {
        "message": "Messages marked as read",
        "unreadCount": unread_count,
        "modifiedCount": len(messages_to_update)
    }


@router.get("/{group_id}/last-seen")
async def get_group_last_seen(
    group_id: str,
    current_user: UserInDB = Depends(get_current_user),
    group_service: GroupChatService = Depends(get_group_chat_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get last message and per-user last-seen timestamps (formatted for IST)."""
    group = await group_service.get_group_chat(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    messages_collection = db.messages
    latest_msg = None
    async for msg in messages_collection.find({"group_chat_id": group_id}).sort("created_at", -1).limit(1):
        latest_msg = msg
        break

    if not latest_msg:
        return {"last_message": None, "read_by": [], "header_time": None}

    # Build read_by list with names and formatted times
    from src.app.utils.time_utils import format_relative_time, to_ist

    read_by_details = latest_msg.get("read_by_details", {})
    read_by_list = []
    for user_id, ts in read_by_details.items():
        try:
            user_data = await db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user_data.get("name") if user_data else "Unknown"
        except Exception:
            user_name = "Unknown"
        # ts may be datetime or ISO string; normalize
        if isinstance(ts, str):
            try:
                seen_dt = datetime.fromisoformat(ts)
            except Exception:
                seen_dt = datetime.utcnow()
        else:
            seen_dt = ts

        read_by_list.append({
            "userId": user_id,
            "userName": user_name,
            "seenAt": format_relative_time(seen_dt),
            "seenAtISO": to_ist(seen_dt).isoformat()
        })

    header_time = format_relative_time(latest_msg.get("created_at"))

    return {
        "last_message": {
            "id": str(latest_msg.get("_id")),
            "content": latest_msg.get("content"),
            "createdAt": latest_msg.get("created_at")
        },
        "read_by": read_by_list,
        "header_time": header_time
    }

