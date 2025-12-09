"""
Organization service - Business logic for organization operations
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.org import OrgInDB
from datetime import datetime

class OrgService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.organizations

    def _convert_to_dict(self, data: dict) -> dict:
        """Convert ObjectId to string in dictionary"""
        if data is None:
            return None
        result = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, list):
                result[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
            elif isinstance(value, dict):
                result[key] = self._convert_to_dict(value)
            else:
                result[key] = value
        return result

    async def create_org(self, name: str, address: str, no_of_users: int, owner_name: str, contact_number: str, owner_id: str) -> OrgInDB:
        """Create a new organization"""
        org_dict = {
            "name": name,
            "address": address,
            "no_of_users": no_of_users,
            "owner_name": owner_name,
            "contact_number": contact_number,
            "owner_id": ObjectId(owner_id),
            "members": [ObjectId(owner_id)],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }
        
        result = await self.collection.insert_one(org_dict)
        org_dict["_id"] = str(result.inserted_id)
        org_dict["owner_id"] = str(org_dict["owner_id"])
        org_dict["members"] = [str(m) for m in org_dict["members"]]
        return OrgInDB(**org_dict)

    async def get_org_by_id(self, org_id: str) -> Optional[OrgInDB]:
        """Fetch organization by ID"""
        try:
            org_data = await self.collection.find_one({"_id": ObjectId(org_id)})
            if org_data:
                org_data = self._convert_to_dict(org_data)
                return OrgInDB(**org_data)
        except Exception:
            pass
        return None

    async def get_orgs_by_owner(self, owner_id: str) -> List[OrgInDB]:
        """Get all organizations owned by a user"""
        orgs = []
        try:
            cursor = self.collection.find({"owner_id": ObjectId(owner_id)})
            async for org_data in cursor:
                org_data = self._convert_to_dict(org_data)
                orgs.append(OrgInDB(**org_data))
        except Exception:
            pass
        return orgs

    async def add_member_to_org(self, org_id: str, user_id: str) -> Optional[OrgInDB]:
        """Add a user to an organization"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(org_id)},
                {
                    "$addToSet": {"members": ObjectId(user_id)},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                return_document=True
            )
            if result:
                result = self._convert_to_dict(result)
                return OrgInDB(**result)
        except Exception:
            pass
        return None

    async def remove_member_from_org(self, org_id: str, user_id: str) -> Optional[OrgInDB]:
        """Remove a user from an organization"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(org_id)},
                {
                    "$pull": {"members": ObjectId(user_id)},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                return_document=True
            )
            if result:
                result = self._convert_to_dict(result)
                return OrgInDB(**result)
        except Exception:
            pass
        return None

    async def update_org(self, org_id: str, update_data: dict) -> Optional[OrgInDB]:
        """Update organization information"""
        try:
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            if not update_data:
                return None
            update_data["updated_at"] = datetime.utcnow()
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(org_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                result = self._convert_to_dict(result)
                return OrgInDB(**result)
        except Exception:
            pass
        return None

    async def get_all_orgs(self, skip: int = 0, limit: int = 10) -> List[OrgInDB]:
        """Get all organizations with pagination"""
        orgs = []
        cursor = self.collection.find().skip(skip).limit(limit)
        async for org_data in cursor:
            org_data = self._convert_to_dict(org_data)
            orgs.append(OrgInDB(**org_data))
        return orgs

    async def delete_org(self, org_id: str) -> bool:
        """Delete an organization"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(org_id)})
            return result.deleted_count > 0
        except Exception:
            return False
