from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.auth_schema import UserCreate, UserLogin, Token, UserResponse
from src.app.core.security import get_password_hash, verify_password, create_access_token
from src.app.db.mongo import get_database
from src.app.dependencies import get_current_user
from src.app.models.user import UserInDB
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    # 1. Check if email already exists
    existing_user = await db.users.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    # 2. Prepare User Document
    # NOTE: Logic - New signups are Admins who need to setup an Org
    user_doc = {
        "email": user_in.email,
        "hashed_password": user_in.password,
        "name": user_in.name,
        "role": "admin",      # Default role for new signups
        "org_id": None,       # Glue: Will be filled in 'Onboarding' step
        "is_active": True,
        "created_at": ObjectId().generation_time
    }

    # 3. Insert into DB
    new_user = await db.users.insert_one(user_doc)
    user_id = str(new_user.inserted_id)

    # 4. Generate Token immediately so they are logged in
    access_token = create_access_token(data={"sub": user_id})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncIOMotorDatabase = Depends(get_database)):
    # 1. Find User
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 2. Verify Password
    if not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 3. Generate Token
    access_token = create_access_token(data={"sub": str(user["_id"])})

    return {"access_token": access_token, "token_type": "bearer"}

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