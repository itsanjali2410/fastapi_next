"""
Invite link routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.invite_schema import InviteLinkCreate, InviteLinkResponse, InviteLinkUse
from src.app.dependencies import get_current_admin_user, get_invite_service, get_user_service, get_org_service
from src.app.services.invite_service import InviteService
from src.app.services.user_service import UserService
from src.app.services.org_service import OrgService
from src.app.models.user import UserInDB
from src.app.core.security import get_password_hash
from typing import List

router = APIRouter()

@router.post("/create", response_model=InviteLinkResponse)
async def create_invite_link(
    invite_data: InviteLinkCreate,
    current_user: UserInDB = Depends(get_current_admin_user),
    invite_service: InviteService = Depends(get_invite_service)
):
    """Create invite link - admin only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must have an organization"
        )
    
    invite = await invite_service.create_invite(
        org_id=current_user.org_id,
        created_by=current_user.id,
        expires_at=invite_data.expires_at
    )
    
    # Generate invite URL
    invite_url = f"/join?token={invite.token}"
    
    return {
        "id": invite.id,
        "org_id": invite.org_id,
        "token": invite.token,
        "invite_url": invite_url,
        "created_by": invite.created_by,
        "is_used": invite.is_used,
        "used_by": invite.used_by,
        "expires_at": invite.expires_at,
        "created_at": invite.created_at
    }

@router.post("/use", response_model=dict)
async def use_invite_link(
    invite_data: InviteLinkUse,
    invite_service: InviteService = Depends(get_invite_service),
    user_service: UserService = Depends(get_user_service),
    org_service: OrgService = Depends(get_org_service)
):
    """Use invite link to join organization"""
    # Get invite
    invite = await invite_service.get_invite_by_token(invite_data.token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite link"
        )
    
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite link has already been used"
        )
    
    # Check if user exists
    existing = await user_service.get_user_by_email(invite_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create user
    from src.app.schemas.auth_schema import UserCreate
    user_create = UserCreate(
        email=invite_data.email,
        password=invite_data.password,
        name=invite_data.name
    )
    new_user = await user_service.create_user(user_create)
    
    # Add to organization
    await org_service.add_member_to_org(invite.org_id, new_user.id)
    await user_service.update_user(new_user.id, {"org_id": invite.org_id})
    
    # Mark invite as used
    await invite_service.use_invite(invite_data.token, new_user.id)
    
    return {
        "message": "Successfully joined organization",
        "user_id": new_user.id
    }

