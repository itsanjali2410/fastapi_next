"""
Invite link service
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.invite import InviteLinkInDB
from datetime import datetime, timedelta
import secrets

class InviteService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.invite_links

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value
            else:
                result[key] = value
        return result

    def _generate_token(self) -> str:
        """Generate unique token"""
        return secrets.token_urlsafe(32)

    async def create_invite(self, org_id: str, created_by: str, expires_at: Optional[datetime] = None) -> InviteLinkInDB:
        """Create invite link"""
        token = self._generate_token()
        invite_data = {
            "org_id": org_id,
            "token": token,
            "created_by": created_by,
            "is_used": False,
            "created_at": datetime.utcnow()
        }
        if expires_at:
            invite_data["expires_at"] = expires_at
        else:
            # Default: expires in 7 days
            invite_data["expires_at"] = datetime.utcnow() + timedelta(days=7)
        
        result = await self.collection.insert_one(invite_data)
        invite_data["_id"] = str(result.inserted_id)
        return InviteLinkInDB(**invite_data)

    async def get_invite_by_token(self, token: str) -> Optional[InviteLinkInDB]:
        """Get invite by token"""
        try:
            invite_data = await self.collection.find_one({"token": token})
            if invite_data:
                invite_data = self._convert_to_dict(invite_data)
                # Check if expired
                if invite_data.get("expires_at") and invite_data["expires_at"] < datetime.utcnow():
                    return None
                return InviteLinkInDB(**invite_data)
        except Exception:
            pass
        return None

    async def use_invite(self, token: str, user_id: str) -> bool:
        """Mark invite as used"""
        try:
            result = await self.collection.update_one(
                {"token": token},
                {"$set": {"is_used": True, "used_by": user_id}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def get_org_invites(self, org_id: str) -> List[InviteLinkInDB]:
        """Get all invites for an organization"""
        invites = []
        cursor = self.collection.find({"org_id": org_id}).sort("created_at", -1)
        async for invite_data in cursor:
            invite_data = self._convert_to_dict(invite_data)
            invites.append(InviteLinkInDB(**invite_data))
        return invites

    async def delete_invite(self, invite_id: str, org_id: str) -> bool:
        """Delete an invite link"""
        try:
            result = await self.collection.delete_one({
                "_id": ObjectId(invite_id),
                "org_id": org_id
            })
            return result.deleted_count > 0
        except Exception:
            return False

