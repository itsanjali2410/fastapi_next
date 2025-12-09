"""
Dependency injection for FastAPI routes
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.app.core.config import settings
from src.app.db.mongo import get_database
from src.app.services.user_service import UserService
from src.app.services.org_service import OrgService
from src.app.services.task_service import TaskService
from src.app.services.chat_service import ChatService
from src.app.services.invite_service import InviteService
from src.app.models.user import UserInDB

# Import services for dependency injection
from src.app.db.mongo import get_database

security = HTTPBearer()

async def get_user_service(db=Depends(get_database)) -> UserService:
    """Get UserService instance"""
    return UserService(db)

async def get_org_service(db=Depends(get_database)) -> OrgService:
    """Get OrgService instance"""
    return OrgService(db)

async def get_task_service(db=Depends(get_database)) -> TaskService:
    """Get TaskService instance"""
    return TaskService(db)

async def get_chat_service(db=Depends(get_database)) -> ChatService:
    """Get ChatService instance"""
    return ChatService(db)

async def get_invite_service(db=Depends(get_database)) -> InviteService:
    """Get InviteService instance"""
    return InviteService(db)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service)
) -> UserInDB:
    """
    Verify JWT token and return current user
    Extract user from the token and fetch from database
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await user_service.get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return user

async def get_current_admin_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """
    Verify that current user has admin role
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource"
        )
    return current_user

async def get_current_user_for_org(
    org_id: str,
    current_user: UserInDB = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service)
) -> UserInDB:
    """
    Verify that current user is a member of the organization
    """
    org = await org_service.get_org_by_id(org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if current_user.id not in org.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    return current_user
