"""
User service - Business logic for user operations
"""
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.user import UserInDB
from src.app.core.security import get_password_hash, verify_password
from src.app.schemas.auth_schema import UserCreate

class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string in dictionary"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = self._convert_to_dict(value)
            else:
                result[key] = value
        return result

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Fetch user by email"""
        user_data = await self.collection.find_one({"email": email})
        if user_data:
            user_data = self._convert_to_dict(user_data)
            return UserInDB(**user_data)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Fetch user by ID"""
        try:
            user_data = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user_data:
                user_data = self._convert_to_dict(user_data)
                return UserInDB(**user_data)
        except Exception:
            pass
        return None

    async def create_user(self, user_create: UserCreate) -> UserInDB:
        """Create a new user"""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_create.email)
        if existing_user:
            raise ValueError(f"User with email {user_create.email} already exists")

        user_dict = {
            "email": user_create.email,
            "name": user_create.name,
            "hashed_password": get_password_hash(user_create.password),
            "role": "user",
            "is_active": True,
            "org_id": None
        }
        
        result = await self.collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return UserInDB(**user_dict)

    async def verify_user_password(self, email: str, password: str) -> Optional[UserInDB]:
        """Verify user credentials"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user

    async def update_user(self, user_id: str, update_data: dict) -> Optional[UserInDB]:
        """Update user information"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                result = self._convert_to_dict(result)
                return UserInDB(**result)
        except Exception:
            pass
        return None

    async def get_all_users(self, skip: int = 0, limit: int = 10) -> list:
        """Get all users with pagination"""
        users = []
        cursor = self.collection.find().skip(skip).limit(limit)
        async for user_data in cursor:
            user_data = self._convert_to_dict(user_data)
            users.append(UserInDB(**user_data))
        return users

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception:
            return False
