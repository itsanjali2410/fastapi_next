"""
Organization routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.org_schema import OrgCreate, OrgUpdate, OrgResponse
from src.app.dependencies import get_current_user, get_current_admin_user, get_org_service
from src.app.services.org_service import OrgService
from src.app.models.user import UserInDB

router = APIRouter()

@router.post("/setup", response_model=OrgResponse)
async def setup_organization(
    org_data: OrgCreate,
    current_user: UserInDB = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Setup organization - only for users without org_id"""
    if current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an organization"
        )
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create organizations"
        )
    
    org = await org_service.create_org(
        name=org_data.name,
        address=org_data.address,
        no_of_users=org_data.no_of_users,
        owner_name=org_data.owner_name,
        contact_number=org_data.contact_number,
        owner_id=current_user.id
    )
    
    # Update user's org_id
    from src.app.services.user_service import UserService
    from src.app.db.mongo import get_database
    user_service = UserService(get_database())
    await user_service.update_user(current_user.id, {"org_id": org.id})
    
    return org

@router.get("/me", response_model=OrgResponse)
async def get_my_organization(
    current_user: UserInDB = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Get current user's organization"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no organization"
        )
    
    org = await org_service.get_org_by_id(current_user.org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return org

@router.put("/me", response_model=OrgResponse)
async def update_my_organization(
    org_data: OrgUpdate,
    current_user: UserInDB = Depends(get_current_admin_user),
    org_service: OrgService = Depends(get_org_service)
):
    """Update organization - admin only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no organization"
        )
    
    update_dict = org_data.model_dump(exclude_unset=True)
    org = await org_service.update_org(current_user.org_id, update_dict)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return org

