from fastapi import APIRouter, HTTPException, status, Depends, Request
from src.app.schemas.auth_schema import UserCreate, UserLogin, Token, UserResponse
from src.app.core.security import get_password_hash, verify_password, create_access_token
from src.app.db.mongo import get_database
from src.app.dependencies import get_current_user
from src.app.models.user import UserInDB
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from src.app.services.auth_service import create_refresh_token, rotate_refresh_token
from src.app.services.auth_service import hash_password
from fastapi.responses import JSONResponse
router = APIRouter()

@router.post("/register")
async def register(user_in: UserCreate, db: AsyncIOMotorDatabase = Depends(get_database)):

    # 1. Check if user exists
    existing_user = await db.users.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # 2. Hash password (IMPORTANT!)
    hashed_pw = hash_password(user_in.password)

    # 3. Create user doc
    user_doc = {
        "email": user_in.email,
        "hashed_password": hashed_pw,
        "name": user_in.name,
        "role": "admin",
        "org_id": None,
        "is_active": True,
        "created_at": ObjectId().generation_time,
        "refresh_token": None
    }

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # 4. Generate tokens
    access = create_access_token({"sub": user_id})
    refresh = create_refresh_token({"sub": user_id})

    # 5. Save refresh token in DB
    await db.users.update_one(
        {"_id": result.inserted_id},
        {"$set": {"refresh_token": refresh}}
    )

    # 6. Return tokens as HttpOnly cookies (like login)
    response = JSONResponse({"message": "Registration successful"})

    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 60 * 60
    )

    return response

@router.post("/login")
async def login(login_data: UserLogin, db=Depends(get_database)):
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(400, "Incorrect email or password")

    if not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(400, "Incorrect email or password")

    access = create_access_token({"sub": str(user["_id"])})
    refresh = create_refresh_token({"sub": str(user["_id"])})

    # Save refresh token in DB (important)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"refresh_token": refresh}}
    )

    response = JSONResponse({"message": "Login successful"})

    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 60 * 60
    )

    return response

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Fetch current user details. 
    Frontend uses this to check if 'org_id' is null. 
    If null -> Redirect to Onboarding Page.
    """
    # UserInDB is a Pydantic model, so use attribute access (not dictionary access)
    return {
        "id": current_user.id or current_user.name,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "org_id": current_user.org_id,
        "is_active": current_user.is_active
    }

@router.post("/refresh")
async def refresh_token(request: Request, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Refresh access token using refresh token from HttpOnly cookie.
    Implements token rotation for security.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    
    try:
        # Rotate refresh token (generates new access and refresh tokens)
        new_access, new_refresh = await rotate_refresh_token(db, refresh_token)
        
        # Set new tokens as HttpOnly cookies
        response = JSONResponse({"message": "Token refreshed successfully"})
        
        response.set_cookie(
            key="access_token",
            value=new_access,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=15 * 60  # 15 minutes
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=30 * 24 * 60 * 60  # 30 days
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/logout")
async def logout(request: Request, current_user: UserInDB = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Logout user by clearing refresh token from database and cookies.
    """
    # Clear refresh token from database
    await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"refresh_token": None}}
    )
    
    # Clear cookies
    response = JSONResponse({"message": "Logged out successfully"})
    response.delete_cookie("access_token", httponly=True, secure=True, samesite="strict")
    response.delete_cookie("refresh_token", httponly=True, secure=True, samesite="strict")
    
    return response