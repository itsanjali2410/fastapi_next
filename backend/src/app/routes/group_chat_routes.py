"""
Group Chat routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
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
from src.app.models.user import UserInDB
from typing import List

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

    # Check for duplicate group name in the same organization
    existing_groups = await group_service.get_user_groups(
        user_id=current_user.id,
        organization_id=current_user.org_id
    )
    for existing_group in existing_groups:
        if existing_group.name.lower() == group_data.name.lower().strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A group with this name already exists"
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

    # Get last message and unread count for each group
    from src.app.db.mongo import get_database
    from src.app.services.messages_service import MessagesService
    db = get_database()
    messages_service = MessagesService(db)
    
    group_items = []
    for group in groups:
        # Get last message for this group
        last_message_query = {
            "group_chat_id": group.id,
            "deleted": {"$ne": True}
        }
        last_message_cursor = (
            messages_service.collection
            .find(last_message_query)
            .sort("created_at", -1)
            .limit(1)
        )
        
        last_message = None
        last_message_timestamp = None
        async for msg in last_message_cursor:
            last_message = msg.get("content", "")
            last_message_timestamp = msg.get("created_at")
            break
        
        # Get unread count (messages not read by current user)
        unread_query = {
            "group_chat_id": group.id,
            "is_read": False,
            "sender_id": {"$ne": current_user.id},  # Don't count own messages
            "deleted": {"$ne": True}
        }
        unread_count = await messages_service.collection.count_documents(unread_query)
        
        group_items.append({
            "id": group.id,
            "name": group.name,
            "avatar_url": group.avatar_url,
            "last_message": last_message,
            "last_message_timestamp": last_message_timestamp.isoformat() if last_message_timestamp else None,
            "unread_count": unread_count,
            "member_count": len(group.members)
        })
    
    # Sort by last_message_timestamp (most recent first)
    group_items.sort(key=lambda x: (
        x["last_message_timestamp"] if x["last_message_timestamp"] else "",
        x["name"]
    ), reverse=True)

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

    return {"message": "Member removed successfully"}

