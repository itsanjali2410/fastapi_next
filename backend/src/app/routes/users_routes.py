"""
User management routes (admin only)
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.auth_schema import UserCreate, UserResponse
from src.app.dependencies import get_current_user, get_current_admin_user, get_user_service
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB
from typing import List

router = APIRouter()

@router.post("/create", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: UserInDB = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Create new user in organization - admin only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must have an organization"
        )
    
    # Check if user exists
    existing = await user_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create user
    new_user = await user_service.create_user(user_data)
    
    # Add user to organization
    from src.app.services.org_service import OrgService
    from src.app.db.mongo import get_database
    org_service = OrgService(get_database())
    await org_service.add_member_to_org(current_user.org_id, new_user.id)
    
    # Update user's org_id
    await user_service.update_user(new_user.id, {"org_id": current_user.org_id})
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "role": new_user.role,
        "org_id": new_user.org_id,
        "is_active": new_user.is_active
    }

@router.get("/", response_model=List[UserResponse])
async def get_org_users(
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Get all users in organization"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    users = await user_service.get_all_users()
    org_users = [u for u in users if u.org_id == current_user.org_id]
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "org_id": u.org_id,
            "is_active": u.is_active
        }
        for u in org_users
    ]

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: dict,
    current_user: UserInDB = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update user - admin only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must have an organization"
        )
    
    user = await user_service.get_user_by_id(user_id)
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated = await user_service.update_user(user_id, update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": updated.id,
        "email": updated.email,
        "name": updated.name,
        "role": updated.role,
        "org_id": updated.org_id,
        "is_active": updated.is_active
    }

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Delete user - admin only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must have an organization"
        )
    
    user = await user_service.get_user_by_id(user_id)
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove from organization
    from src.app.services.org_service import OrgService
    from src.app.db.mongo import get_database
    org_service = OrgService(get_database())
    await org_service.remove_member_from_org(current_user.org_id, user_id)
    
    return {"message": "User deleted successfully"}

