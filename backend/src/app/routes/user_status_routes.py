"""
User Status routes - Online/offline and last seen
"""
from fastapi import APIRouter, HTTPException, status, Depends
from collections.abc import AsyncIterator
from src.app.schemas.user_status_schema import (
    UserStatusResponse,
    UserStatusUpdate,
    UsersStatusResponse
)
from src.app.dependencies import get_current_user, get_user_status_service, get_user_service
from src.app.services.user_status_service import UserStatusService
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB

router = APIRouter()

@router.put("/me", response_model=UserStatusResponse)
async def update_my_status(
    status_data: UserStatusUpdate,
    current_user: UserInDB = Depends(get_current_user),
    status_service: UserStatusService = Depends(get_user_status_service),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's online status"""
    status_obj = await status_service.update_status(
        user_id=current_user.id,
        is_online=status_data.is_online
    )

    return UserStatusResponse(
        user_id=status_obj.user_id,
        is_online=status_obj.is_online,
        last_seen=status_obj.last_seen,
        user_name=current_user.name
    )

@router.get("/me", response_model=UserStatusResponse)
async def get_my_status(
    current_user: UserInDB = Depends(get_current_user),
    status_service: UserStatusService = Depends(get_user_status_service)
):
    """Get current user's status"""
    status_obj = await status_service.get_status(current_user.id)
    if not status_obj:
        # Create default status
        status_obj = await status_service.update_status(current_user.id, False)

    return UserStatusResponse(
        user_id=status_obj.user_id,
        is_online=status_obj.is_online,
        last_seen=status_obj.last_seen,
        user_name=current_user.name
    )

@router.get("/{user_id}", response_model=UserStatusResponse)
async def get_user_status(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    status_service: UserStatusService = Depends(get_user_status_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get status for a specific user (must be in same organization)"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Verify the requested user is in the same organization
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if target_user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access user status outside your organization"
        )
    
    status_obj = await status_service.get_status(user_id)
    if not status_obj:
        # Create default status if doesn't exist
        status_obj = await status_service.update_status(user_id, False)
    
    return UserStatusResponse(
        user_id=status_obj.user_id,
        is_online=status_obj.is_online,
        last_seen=status_obj.last_seen,
        user_name=target_user.name
    )

@router.get("", response_model=UsersStatusResponse)
async def get_org_users_status(
    current_user: UserInDB = Depends(get_current_user),
    status_service: UserStatusService = Depends(get_user_status_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get status for all users in the organization"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )

    # Get org members
    from src.app.db.mongo import get_database
    from bson import ObjectId
    
    db = get_database()
    org = await db.organizations.find_one({"_id": ObjectId(current_user.org_id)})
    
    user_ids = []
    if org:
        user_ids = [str(mid) if isinstance(mid, ObjectId) else mid for mid in org.get("members", [])]

    statuses_dict = await status_service.get_org_users_status(
        organization_id=current_user.org_id,
        user_ids=user_ids
    )

    statuses = []
    for user_id, status_obj in statuses_dict.items():
        user = await user_service.get_user_by_id(user_id)
        statuses.append(UserStatusResponse(
            user_id=status_obj.user_id,
            is_online=status_obj.is_online,
            last_seen=status_obj.last_seen,
            user_name=user.name if user else None
        ))

    return UsersStatusResponse(statuses=statuses)

