"""
Task service
"""
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.app.models.task import TaskInDB
from datetime import datetime

class TaskService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.tasks

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
            elif isinstance(value, dict):
                result[key] = self._convert_to_dict(value)
            else:
                result[key] = value
        return result

    async def create_task(self, task_data: dict) -> TaskInDB:
        """Create a new task"""
        task_data["created_at"] = datetime.utcnow()
        task_data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(task_data)
        task_data["_id"] = str(result.inserted_id)
        return TaskInDB(**task_data)

    async def get_task_by_id(self, task_id: str) -> Optional[TaskInDB]:
        """Get task by ID"""
        try:
            task_data = await self.collection.find_one({"_id": ObjectId(task_id)})
            if task_data:
                task_data = self._convert_to_dict(task_data)
                return TaskInDB(**task_data)
        except Exception:
            pass
        return None

    async def get_tasks_by_org(self, org_id: str, skip: int = 0, limit: int = 50) -> List[TaskInDB]:
        """Get all tasks in an organization"""
        tasks = []
        cursor = self.collection.find({"org_id": org_id}).skip(skip).limit(limit).sort("created_at", -1)
        async for task_data in cursor:
            task_data = self._convert_to_dict(task_data)
            tasks.append(TaskInDB(**task_data))
        return tasks

    async def get_tasks_by_user(self, user_id: str, org_id: str) -> List[TaskInDB]:
        """Get tasks assigned to a user"""
        tasks = []
        cursor = self.collection.find({
            "assigned_to": user_id,
            "org_id": org_id
        }).sort("created_at", -1)
        async for task_data in cursor:
            task_data = self._convert_to_dict(task_data)
            tasks.append(TaskInDB(**task_data))
        return tasks

    async def update_task(self, task_id: str, update_data: dict) -> Optional[TaskInDB]:
        """Update task"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                result = self._convert_to_dict(result)
                return TaskInDB(**result)
        except Exception:
            pass
        return None

    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(task_id)})
            return result.deleted_count > 0
        except Exception:
            return False

